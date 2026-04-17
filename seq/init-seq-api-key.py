import os
import requests
import json

SEQ_URL = os.environ.get('SEQ_URL')
ADMIN_API_KEY = os.environ.get('ADMIN_API_KEY')
CUSTOMER_NAME = (os.environ.get('CUSTOMER_NAME') or '').strip()
POOL = (os.environ.get('POOL') or '').strip()

def get_services():
    with open('/app/services.txt', 'r') as f:
        services = {}
        for line in f:
            if line.strip():
                service, token = line.strip().split(',', 1)
                services[service] = token
    return services

def build_title(service):
    if CUSTOMER_NAME:
        return f"{CUSTOMER_NAME} - {service}"
    return service

def resolve_app_and_pool(service):
    # Keep behavior explicit: App always equals service from services.txt.
    # Optional POOL env adds a Pool property; no inferred parsing/fallback.
    if POOL:
        return service, POOL
    return service, None

def get_all_keys():
    response = requests.get(f"{SEQ_URL}/api/apikeys/", headers={"X-Seq-ApiKey": ADMIN_API_KEY})
    return response.json()

def create_or_update_key(service, token):
    all_keys = get_all_keys()
    title = build_title(service)
    existing_key = next((key for key in all_keys if key['Title'] == title), None)

    app, pool = resolve_app_and_pool(service)
    applied_properties = [{"Name": "App", "Value": app}]
    if pool:
        applied_properties.append({"Name": "Pool", "Value": pool})
    if CUSTOMER_NAME:
        applied_properties.append({"Name": "Customer", "Value": CUSTOMER_NAME})

    key_data = {
        "Title": title,
        "Token": token,
        "TokenPrefix": None,
        "InputSettings": {
            "AppliedProperties": applied_properties,
            "Filter": None,
            "MinimumLevel": None,
            "UseServerTimestamps": False
        },
        "IsDefault": False,
        "OwnerId": None,
        "AssignedPermissions": ["Ingest"]
    }

    if existing_key:
        key_id = existing_key['Id']
        key_data["Id"] = key_id
        response = requests.put(f"{SEQ_URL}/api/apikeys/{key_id}", 
                                headers={"X-Seq-ApiKey": ADMIN_API_KEY, "Content-Type": "application/json"},
                                data=json.dumps(key_data))
        print(f"Updated key for {service}: {response.status_code}")
    else:
        response = requests.post(f"{SEQ_URL}/api/apikeys/", 
                                 headers={"X-Seq-ApiKey": ADMIN_API_KEY, "Content-Type": "application/json"},
                                 data=json.dumps(key_data))
        print(f"Created key for {service}: {response.status_code}")

    return response.json()

def main():
    services = get_services()
    for service, token in services.items():
        result = create_or_update_key(service, token)
        print(f"API Key for {service}: {result['TokenPrefix']}")

if __name__ == "__main__":
    main()
