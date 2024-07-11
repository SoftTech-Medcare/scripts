import os
try:
  import requests
except ImportError:
  raise ImportError("The 'requests' library is required for making HTTP requests. Please install it using 'pip install requests")

from argparse import ArgumentParser

def get_image_tags(registry_url, repository, auth):
  response = requests.get(f"{registry_url}/v2/{repository}/tags/list", auth=auth)
  response.raise_for_status()
  tags = response.json().get('tags', [])
  return tags

def delete_tag(registry_url, repository, auth, tag):
  response = requests.head(f"{registry_url}/v2/{repository}/manifests/{tag}", auth=auth, headers={'Accept': 'application/vnd.docker.distribution.manifest.v2+json'})
  response.raise_for_status()
  digest = response.headers['Docker-Content-Digest']
  response = requests.delete(f"{registry_url}/v2/{repository}/manifests/{digest}", auth=auth)
  if response.status_code == 202:
    print(f"Deleted tag: {tag}")
  else:
    print(f"Failed to delete tag: {tag}, status code: {response.status_code}")

def manage_image_tags(registry_url: str, repository: str, username: str, password: str, keep=4):
  """
  Manages image tags in a container registry, keeping only the specified
  number of most recent version tags and deleting older ones.

  Args:
      registry_url (str): URL of the container registry.
      repository (str): Name of the image repository.
      username (str): Username for authentication.
      password (str): Password for authentication.
      keep (int, optional): The number of version
          tags to retain. Defaults to 4.

  Raises:
      ValueError: If the provided number of tags to keep is non-positive.
      ImportError: If the `semver` library is not installed.
  """

  try:
    import semver
    semver.require('=3.0.2')
  except ImportError:
    raise ImportError("The 'semver' library is required for version tag management. Please install it using 'pip install semver'.")

  if keep <= 0:
    raise ValueError("number_of_version_tags_to_keep must be a positive integer.")

  auth = (username, password)
  tags = get_image_tags(registry_url, repository, auth)
  
  # Filter out non-version tags if needed (e.g., "latest")
  version_tags = [tag for tag in tags if semver.Version.is_valid(tag)]
  
  if len(version_tags) > keep:
    version_tags_sorted = sorted(version_tags, key=semver.Version.parse)
    tags_to_delete = version_tags_sorted[:-4]
    for tag in tags_to_delete:
      delete_tag(registry_url, repository, auth, tag)
  else:
      print(f"No need to delete tags, {keep} or fewer version tags found.")

if __name__ == "__main__":
  parser = ArgumentParser(description='Manage Docker image tags in a private registry.')
  parser.add_argument('--registry', required=False, help='The URL of the private Docker registry.')
  parser.add_argument('--repository', required=False, help='The name of the repository (image) to manage.')
  parser.add_argument('--username', required=False, help='The username for the Docker registry.')
  parser.add_argument('--password', required=False, help='The password for the Docker registry.')
  parser.add_argument('--keep', type=int, default=4, help='The number of version tags to keep (default: 4).')
  
  args = parser.parse_args()

  registry = args.registry or os.getenv('DOCKER_REGISTRY')
  repository = args.repository or os.getenv('DOCKER_REPOSITORY') # the image repository name
  username = args.username or os.getenv('DOCKER_USERNAME')
  password = args.password or os.getenv('DOCKER_PASSWORD')
  keep = args.keep or os.getenv("KEEP_TAGS", 4)

  # Check for missing required arguments (after trying environment variables)
  missing_args = []
  if not registry:
    missing_args.append('registry')
  if not repository:
    missing_args.append('repository')
  if not username:
    missing_args.append('username')
  if not password:
    missing_args.append('password')

  if missing_args:
    print(f"Error: Missing required arguments: {', '.join(missing_args)}")
    exit(1)
  
  manage_image_tags(registry, repository, username, password, keep)
