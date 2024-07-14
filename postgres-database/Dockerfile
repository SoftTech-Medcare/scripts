# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY init-database-and-user.py ./

# Set environment variables (replace with actual values or use secrets management)
ENV DB_HOST=localhost:5431
ENV DB_NAME=your_database_name
ENV DB_USER=your_superuser
ENV DB_PASSWORD=your_superuser_password
ENV USER=new_user
ENV USER_PASSWORD=new_user_password
ENV SCHEMA=new_schema
ENV DATABASE=new_database

# Run the Python script
CMD ["python", "./init-database-and-user.py"]
