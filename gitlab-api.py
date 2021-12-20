import getopt, sys
from enum import Enum, auto
import requests
import urllib.parse
import time
from io import BytesIO
import tempfile
import subprocess
import importlib
modify_gitrepo = importlib.import_module("modify-gitrepo")
import os
import shutil

# ---------------------------------------------------------------------------
TLS_VERIFY=False
if TLS_VERIFY==False:
  import urllib3
  urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SRC_GITLAB_URL = os.environ['SRC_GITLAB_URL']
SRC_TOKEN = os.environ['SRC_TOKEN']
DST_GITLAB_URL = os.environ['DST_GITLAB_URL']
DST_TOKEN = os.environ['DST_TOKEN']
GIT_BINARY = os.environ['GIT_BINARY']

# ---------------------------------------------------------------------------
class Action(Enum):
  MIGRATE_GROUP = auto()
  MIGRATE_PROJECT = auto()


def migrate_group(source, dest_path = None, dest_name = None):
  '''
  Migrates a Gitlab group from source to dest.

  source: source group in format group_id or namespace.
  dest_path: [optional] dest path. Autodetected if not provided.
  dest_name: [optional] dest name. Autodetected if not provided.
  '''
  # Export
  (detected_source_group_path, detected_source_group_name, group_data) = export_group(source)
  print()
  
  # Determine import location
  if dest_path != None:
    print(f'Importing group to specified path at: {dest_path}')
  else:
    dest_path = detected_source_group_path
    print(f'Importing group to detected path at: {dest_path}')

  if dest_name != None:
    print(f'Importing group with specified name: {dest_name}')
  else:
    dest_name = detected_source_group_name
    print(f'Importing group with detected name: {dest_name}')
  
  print()

  # Debugging -> save exported file to disk
  # open('file.tar.gz', 'wb').write(group_data)

  # Import
  import_group(dest_path, dest_name, group_data)


def migrate_project(source, dest_path = None, dest_name = None):
  '''
  Migrates a Gitlab project from source to dest.
  If dest is not provided, it will be derived from source.

  source: source project in format project_id or namespace/project.
  dest_path: [optional] dest path. Autodetected if not provided.
  dest_name: [optional] dest name. Autodetected if not provided.
  '''

  # Export
  (detected_source_project_path, detected_source_project_name, project_data) = export_project(source)
  print()

  # Determine import location
  if dest_path != None:
    print(f'Importing project to specified path at: {dest_path}')
  else:
    dest_path = detected_source_project_path
    print(f'Importing project to detected path at: {dest_path}')

  if dest_name != None:
    print(f'Importing project with specified name: {dest_name}')
  else:
    dest_name = detected_source_project_name
    print(f'Importing project with detected name: {dest_name}')

  print()

  # Debugging -> save exported file to disk
  # open('file.tar.gz', 'wb').write(project_data)

  # modify repo
  modified_project_data = modify_repo(project_data)
  print()

  # Debugging -> save modified exported file to disk
  # open('file.tar.gz', 'wb').write(modified_project_data)

  # Import
  import_project(dest_path, dest_name, modified_project_data)


# ---------------------------------------------------------------------------

def export_group(source):
  '''
  Detects the source group namespace and exports the group data.

  source: source group in format project_id or namespace.
  returns: (detected_source_group_path, detected_source_group_name, group_data)
  '''
  print(f'Exporting group from: {source}.')
  source_url_safe = urllib.parse.quote_plus(source)

  # Detect the source group namespace
  headers = {
    'PRIVATE-TOKEN': f'{SRC_TOKEN}'
  }
  response = requests.get(
    url = f'{SRC_GITLAB_URL}/api/v4/groups/{source_url_safe}',
    headers = headers,
    verify = TLS_VERIFY,
    timeout = 600,    
  )
  response.raise_for_status()
  detected_source_group_path = response.json()['full_path']
  detected_source_group_name = response.json()['name']
  print(f'- Detected path is: {detected_source_group_path}, detected name is: {detected_source_group_name}.')

  # Initiate export
  print(f'- Initiating export for group {source}...')
  response = requests.post(
    url = f'{SRC_GITLAB_URL}/api/v4/groups/{source_url_safe}/export',
    headers = headers,
    verify = TLS_VERIFY,
    timeout = 600,
  )
  response.raise_for_status()

  # Wait until group has been exported
  print(f'- Waiting for group {source} to be exported...')
  exported = False
  while not exported:
    try:
      response = requests.get(
        url = f'{SRC_GITLAB_URL}/api/v4/groups/{source_url_safe}/export/download',
        headers = headers,
        verify = TLS_VERIFY,
        timeout = 600,
      )
      response.raise_for_status()
      
      print(f'  - Group {source} export status is ready and downloaded.')
      group_data = response.content
      exported = True

    except Exception as e:
      print(f'  - Group {source} export status is not ready (404 not found is expected): {e}')
      time.sleep(1)

  print('- Successfully exported group.')

  return (detected_source_group_path, detected_source_group_name, group_data)


def import_group(dest_path, dest_name, group_data):
  '''
  dest_path: path of group
  dest_name: name of group
  group_data: the contents of the exported group.
  '''
  print(f'Importing group to path={dest_path}, name={dest_name}.')

  headers = {
    'PRIVATE-TOKEN': f'{DST_TOKEN}'
  }
  files = {
    'file': ('file.tar.gz', BytesIO(group_data))
  }
  data = {
    "path": dest_path,
    "name": dest_name,
  }

  # Check if dest group is a sub-group
  if len(dest_path.split("/")) > 1:
    detected_dest_parent_path = dest_path.rsplit("/", 1)[0]
    detected_dest_child_path = dest_path.rsplit("/", 1)[1]
    print(f'- Detected parent group path = {detected_dest_parent_path}, child group path = {detected_dest_child_path}.')

    # Detect the dest parent id
    detected_dest_parent_path_url_safe = urllib.parse.quote_plus(detected_dest_parent_path)
    response = requests.get(
      url = f'{DST_GITLAB_URL}/api/v4/groups/{detected_dest_parent_path_url_safe}',
      headers = headers,
      verify = TLS_VERIFY,
      timeout = 600,    
    )
    response.raise_for_status()
    detected_dest_parent_id = response.json()['id']
    
    # Amend path and parent_id
    data["path"] = detected_dest_child_path
    data["parent_id"] = detected_dest_parent_id
    print(f'- Detected parent_id: {detected_dest_parent_id}.')
    
  response = requests.post(
    url = f'{DST_GITLAB_URL}/api/v4/groups/import',
    headers = headers,
    data = data,
    files = files,
    verify = TLS_VERIFY,
    timeout = 600,
  )
  response.raise_for_status()

  print('- Successfully imported group.')


def modify_repo(project_data):
  print('Modifying repo')
  with tempfile.TemporaryDirectory() as tmpdirname:
    print('- Created temporary directory', tmpdirname)

    # Save to tempdir/file.tar.gz
    print('- Saving project tar file')
    tarfilename = "file.tar.gz"
    with open(f'{tmpdirname}/{tarfilename}', 'wb') as tarfile:
      tarfile.write(project_data)
      tarfile.flush()
      os.fsync(tarfile)

    # tar -zxvf file.tar.gz
    print('- Untar-ing file')
    subprocess.check_output([ "/usr/bin/tar", "-zx", "-C", tmpdirname, "-f", f"{tmpdirname}/{tarfilename}" ])

    print('------------------------------------------')
    # git clone project.bundle
    print('- git clone project.bundle')
    subprocess.check_output([ f"{GIT_BINARY}", "-C", tmpdirname, "clone", "project.bundle" ])

    print('------------------------------------------')
    # python3 modify-repo -m -r project/
    print('- modifying repo')
    modify_gitrepo.FORCE = False
    modify_gitrepo.modify_repo(f"{tmpdirname}/project")
    
    print('------------------------------------------')
    # git -C project/ bundle create project.bundle --all
    print('- git recreate project.bundle')
    subprocess.check_output([ f"{GIT_BINARY}", "-C", f"{tmpdirname}/project", "bundle", "create", f"{tmpdirname}/project.bundle", "--all" ])
    
    print('------------------------------------------')
    # rm file.tar.gz
    # rm -rf project
    print('- delete project folder')
    shutil.rmtree(f'{tmpdirname}/project')

    # tar -zcvf file.tar.gz .
    print('- Tar-ing file')
    subprocess.check_output([ "/usr/bin/tar", "-zc",  f"--exclude={tarfilename}", "-C", tmpdirname, "-f", f"{tmpdirname}/file.tar.gz", "." ])

    # Load modfied export
    print('- Load modified project data')
    with open(f'{tmpdirname}/file.tar.gz', 'rb') as tarfile:
      modified_project_data = tarfile.read()

    return modified_project_data



def export_project(source):
  '''
  Detects the source project path and exports the project data.

  source: source project in format project_id or namespace/project.
  returns: (detected_source_project_path, detected_source_project_name, project_data)
  '''
  print(f'Exporting project from: {source}.')
  source_url_safe = urllib.parse.quote_plus(source)

  # Detect the source project path
  headers = {
    'PRIVATE-TOKEN': f'{SRC_TOKEN}'
  }
  response = requests.get(
    url = f'{SRC_GITLAB_URL}/api/v4/projects/{source_url_safe}',
    headers = headers,
    verify = TLS_VERIFY,
    timeout = 600,    
  )
  response.raise_for_status()
  detected_source_project_path = response.json()['path_with_namespace']
  detected_source_project_name = response.json()['name']
  print(f'- Detected path is: {detected_source_project_path}, detected name is: {detected_source_project_name}.')

  # Initiate export
  print(f'- Initiating export for project {source}...')
  response = requests.post(
    url = f'{SRC_GITLAB_URL}/api/v4/projects/{source_url_safe}/export',
    headers = headers,
    verify = TLS_VERIFY,
    timeout = 600,
  )
  response.raise_for_status()

  # Wait until project has been exported
  print(f'- Waiting for project {source} to be exported...')
  exported = False
  while not exported:
    response = requests.get(
      url = f'{SRC_GITLAB_URL}/api/v4/projects/{source_url_safe}/export',
      headers = headers,
      verify = TLS_VERIFY,
      timeout = 600,
    )
    response.raise_for_status()
    if response.json()['export_status'] != "finished":
      print(f'  - Project {source} export status is not ready...')
      time.sleep(1)
    else:
      print(f'  - Project {source} export status is ready.')
      exported = True

  # Download project data
  print(f'- Downloading project {source}.')
  response = requests.get(
    url = f'{SRC_GITLAB_URL}/api/v4/projects/{source_url_safe}/export/download',
    headers = headers,
    verify = TLS_VERIFY,
    timeout = 600,
  )
  response.raise_for_status()
  project_data = response.content

  print('- Successfully exported project.')

  return (detected_source_project_path, detected_source_project_name, project_data)


def import_project(dest_path, dest_name, project_data):
  '''
  dest_path: full path of project
  dest_name: name of project
  project_data: the contents of the exported project
  '''
  print(f'Importing project to path={dest_path}, name={dest_name}.')
  
  # Extract namespace
  if len(dest_path.rsplit("/", 1)) != 2:
    print(f'- Unable to split {dest_path} with delimiter = /.')
    sys.exit(1)

  dest_namespace = dest_path.rsplit("/", 1)[0]
  dest_path = dest_path.rsplit("/", 1)[1]
  print(f'- Extracted namespace={dest_namespace}, path={dest_path}.')

  headers = {
    'PRIVATE-TOKEN': f'{DST_TOKEN}'
  }
  files = {
    'file': ('file.tar.gz', BytesIO(project_data))
  }
  data = {
    "namespace": dest_namespace,
    "name": dest_name,
    "path": dest_path,
  }
  response = requests.post(
    url = f'{DST_GITLAB_URL}/api/v4/projects/import',
    headers = headers,
    data = data,
    files = files,
    verify = TLS_VERIFY,
    timeout = 600,
  )
  response.raise_for_status()

  print('- Successfully imported project.')


def print_help():
  print("This script assists in migrating a git repo between gitlab instances.\n"
  "\n"
  "Usage\n"
  "-------------\n"
  "python3 gitlab-api.py <-g|-p> <-s source> [--dest-path dest_path] [--dest-name dest_name]\n"
  "\n"
  "Options\n"
  "-------------\n"
  "-g: migrate group.\n"
  "-p: migrate project.\n"
  "-s: source - id or full path of group or project (eg. 113 or my-namespace/my-project).\n"
  "--dest-path: full path of destination group or project (eg. my-namespace/my-project). Autodetected if not provided.\n"
  "--dest-name: name of destination group or project (eg. 'My Project'). Autodetected if not provided."
  "\n"
  )


# ---------------------------------------------------------------------------


def main():
  try:
    opts, args = getopt.getopt(sys.argv[1:], "gps:", ["dest-path=","dest-name="])
  except getopt.GetoptError as err:
    print(err)
    print_help()
    sys.exit(1)

  # Print help if no arguments provided
  if len(sys.argv) == 1:
    print_help()
    sys.exit(1)

  # Set config from arguments
  migrate_action = None
  source = None
  dest_path = None
  dest_name = None
  for key, value in opts:
    if key == "-g":
      migrate_action = Action.MIGRATE_GROUP
    elif key == "-p":
      migrate_action = Action.MIGRATE_PROJECT
    elif key == "-s":
      source = value
    elif key == "--dest-path":
      dest_path = value
    elif key == "--dest-name":
      dest_name = value
    else:
      print(f"Error: Unhandled option {key}")
      sys.exit(1)
    
  # Check that necessary config are set
  if not migrate_action or not source:
    print("Error: Some values were not set.")
    print_help()
    sys.exit(1)

  # Perform repo action
  if migrate_action == Action.MIGRATE_GROUP:
    migrate_group(source, dest_path, dest_name)
  elif migrate_action == Action.MIGRATE_PROJECT:
    migrate_project(source, dest_path, dest_name)


if __name__ == "__main__":
  main()
