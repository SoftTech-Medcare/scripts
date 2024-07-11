from argparse import ArgumentParser
import requests
import os
from truncate_image import manage_image_tags

def get_arguments():
  """Parses command-line arguments for registry URL, username, password, and keep value.

  Returns:
    argparse.Namespace: An object containing parsed arguments.
  """

  parser = ArgumentParser(description="Truncates image tags in a container registry.")
  parser.add_argument('--registry', type=str, required=True,
                      help="The URL of the container registry.")
  parser.add_argument('--username', type=str, required=True,
                      help="The username for authentication with the registry.")
  parser.add_argument('--password', type=str, required=True,
                      help="The password for authentication with the registry.")
  parser.add_argument('--keep', type=int, default=4,
                      help="The number of tags to keep for each image (default: 4).")

  return parser.parse_args()

def get_repositories(registry_url, username, password):
  """Fetches the list of repositories from the container registry.

  Args:
    registry_url: The URL of the container registry.
    username: The username for authentication with the registry.
    password: The password for authentication with the registry.

  Returns:
    list: A list of repository names.
  """

  response = requests.get(f'{registry_url}/v2/_catalog', auth=(username, password))
  response.raise_for_status()
  repositories = response.json().get('repositories', [])
  return repositories

def truncate_all_images(registry_url, username, password, keep):
  """Truncates image tags in all repositories, keeping the specified number.

  Args:
    registry_url: The URL of the container registry.
    username: The username for authentication with the registry.
    password: The password for authentication with the registry.
    keep: The number of tags to keep for each image.
  """

  repositories = get_repositories(registry_url, username, password)
  for repository in repositories:
    manage_image_tags(registry_url, repository, username, password, keep=keep)

if __name__ == "__main__":
  args = get_arguments()

  registry = args.registry or os.getenv('DOCKER_REGISTRY')
  username = args.username or os.getenv('DOCKER_USERNAME')
  password = args.password or os.getenv('DOCKER_PASSWORD')
  keep = args.keep or os.getenv("KEEP_TAGS", 4)

  # Check for missing required arguments (after trying environment variables)
  missing_args = []
  if not registry:
    missing_args.append('registry')
  if not username:
    missing_args.append('username')
  if not password:
    missing_args.append('password')

  if missing_args:
    print(f"Error: Missing required arguments: {', '.join(missing_args)}")
    exit(1)

  truncate_all_images(registry, username, password, args.keep)
