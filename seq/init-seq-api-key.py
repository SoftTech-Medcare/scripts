import os
import requests
import json

SEQ_URL = os.environ.get('SEQ_URL')
ADMIN_API_KEY = os.environ.get('ADMIN_API_KEY')
CUSTOMER_NAME = os.environ.get('CUSTOMER_NAME')
TOKEN = os.environ.get('TOKEN')

SERVICES = ['hemoserver', 'hemoreport', 'hemojob']

def get_all_keys():
    response = requests.get(f"{SEQ_URL}/api/apikeys/", headers={"X-Seq-ApiKey": ADMIN_API_KEY})
    return response.json()

def get_key(key_id):
    response = requests.get(f"{SEQ_URL}/api/apikeys/{key_id}", headers={"X-Seq-ApiKey": ADMIN_API_KEY})
    return response.json()

def create_or_update_key(service):
    all_keys = get_all_keys()
    existing_key = next((key for key in all_keys if key['Title'] == f"{CUSTOMER_NAME} - {service}"), None)

    key_data = {
        "Title": f"{CUSTOMER_NAME} - {service}",
        "Token": TOKEN,
        "TokenPrefix": None,
        "InputSettings": {
            "AppliedProperties": [
                {"Name": "App", "Value": service},
                {"Name": "Customer", "Value": CUSTOMER_NAME}
            ],
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
        key_data["Id"] = key_id  # Include the Id field for updates
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
    for service in SERVICES:
        result = create_or_update_key(service)
        print(f"API Key for {service}: {result['TokenPrefix']}")

if __name__ == "__main__":
    main()
