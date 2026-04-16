import base64
import os
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extensions import cursor
from kubernetes import client, config

# Load Kubernetes config (assumes running inside the Kubernetes cluster)
config.load_incluster_config()

# Kubernetes client for accessing secrets
v1 = client.CoreV1Api()

POSTGRES_SECRET_NAMESPACE = os.getenv('POSTGRES_SECRET_NAMESPACE', 'default')
POSTGRES_SECRET_NAME = os.getenv('POSTGRES_SECRET_NAME', 'db-superuser')
POSTGRES_SECRET_KEY = os.getenv("POSTGRES_SECRET_KEY", "password")

# Database connection parameters
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'postgres')

# New user and database parameters
USER = os.getenv('USER')
USER_PASSWORD = os.getenv('USER_PASSWORD')
SCHEMA = (os.getenv('SCHEMA') or '').strip()
DATABASE = os.getenv('DATABASE')

def check_user_exists(cursor: cursor, user):
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (user,))
    return cursor.fetchone() is not None

def check_database_exists(cursor: cursor, dbname):
    cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
    return cursor.fetchone() is not None

def check_schema_exists(cursor: cursor, schema):
    cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s", (schema,))
    return cursor.fetchone() is not None

def get_postgres_superuser_password():
    try:
        # Retrieve PostgreSQL superuser password from Kubernetes Secret
        secret = v1.read_namespaced_secret(name=POSTGRES_SECRET_NAME, namespace=POSTGRES_SECRET_NAMESPACE)
        data = secret.data.get(POSTGRES_SECRET_KEY)
        if data:
            decoded = base64.b64decode(data).decode('utf-8')
            return decoded
        else:
            return None
    except client.exceptions.ApiException as e:
        print(f"Error fetching Kubernetes Secret: {e}")
        return None

def create_postgres_user_schema_and_database():
    try:
        # Get PostgreSQL superuser password from Kubernetes Secret
        superuser_password = get_postgres_superuser_password()
        if not superuser_password:
            print("Error: Cannot retrieve PostgreSQL superuser password from Kubernetes Secret.")
            return
        
        # Connect to the PostgreSQL server
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=superuser_password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if user exists, create if not
        if not check_user_exists(cursor, USER):
            cursor.execute(sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(USER)), (USER_PASSWORD,))
            print(f"User '{USER}' created successfully.")
        else:
            print(f"User '{USER}' already exists. update password if needed.")
            cursor.execute(sql.SQL("ALTER USER {} WITH PASSWORD %s").format(sql.Identifier(USER)), (USER_PASSWORD,))

        # Check if database exists, create if not
        if not check_database_exists(cursor, DATABASE):
            cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(DATABASE), sql.Identifier(USER)))
            print(f"Database '{DATABASE}' created successfully.")
        else:
            print(f"Database '{DATABASE}' already exists.")
        
        # Reconnect to the new database to create schema and grant privileges
        cursor.close()
        conn.close()
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DATABASE,
            user=DB_USER,
            password=superuser_password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Always grant database privileges.
        cursor.execute(
            sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                sql.Identifier(DATABASE),
                sql.Identifier(USER),
            )
        )

        # Use default schema behavior when SCHEMA is not specified (or explicitly set to public).
        use_public_schema = (not SCHEMA) or SCHEMA.lower() == 'public'
        target_schema = 'public' if use_public_schema else SCHEMA

        if use_public_schema:
            # Keep schema-less mode: use PostgreSQL default public schema.
            cursor.execute(
                sql.SQL("ALTER USER {} IN DATABASE {} SET search_path TO public").format(
                    sql.Identifier(USER),
                    sql.Identifier(DATABASE),
                )
            )
            cursor.execute(
                sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(
                    sql.Identifier(USER)
                )
            )
            cursor.execute(
                sql.SQL("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {}").format(
                    sql.Identifier(USER)
                )
            )
            cursor.execute(
                sql.SQL("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {}").format(
                    sql.Identifier(USER)
                )
            )
            print(f"Using default schema 'public' for user '{USER}'.")
        else:
            # Backward-compatible path for custom schema deployments.
            if not check_schema_exists(cursor, target_schema):
                cursor.execute(
                    sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                        sql.Identifier(target_schema),
                        sql.Identifier(USER),
                    )
                )
                print(f"Schema '{target_schema}' created for user '{USER}'.")
            else:
                print(f"Schema '{target_schema}' already exists.")

            cursor.execute(
                sql.SQL("ALTER USER {} IN DATABASE {} SET search_path TO {}").format(
                    sql.Identifier(USER),
                    sql.Identifier(DATABASE),
                    sql.Identifier(target_schema),
                )
            )
            cursor.execute(
                sql.SQL("GRANT ALL PRIVILEGES ON SCHEMA {} TO {}").format(
                    sql.Identifier(target_schema),
                    sql.Identifier(USER),
                )
            )
            cursor.execute(
                sql.SQL("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {} TO {}").format(
                    sql.Identifier(target_schema),
                    sql.Identifier(USER),
                )
            )
            cursor.execute(
                sql.SQL("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {} TO {}").format(
                    sql.Identifier(target_schema),
                    sql.Identifier(USER),
                )
            )
            print(f"Granted all privileges on database '{DATABASE}' and schema '{target_schema}' to user '{USER}'.")
            
        # Commit changes
        conn.commit()

        print("User and database initialization completed successfully.")

    except psycopg2.Error as e:
        print(f"Error: {e}")
    finally:
        if conn is not None:
            cursor.close()
            conn.close()

# Call the function to create user, schema, and database
create_postgres_user_schema_and_database()
