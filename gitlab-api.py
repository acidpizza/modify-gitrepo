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


def migrate_group(source, dest):
  pass

def migrate_project(source, dest):
  # Export
  (detected_source_project_path, project_data) = export_project(source)
  print()

  # Determine import location
  if dest != None:
    print(f'Importing project to specified location at: {dest}')
  else:
    dest = detected_source_project_path
    print(f'Importing project to detected location at: {dest}')
  print()

  # Debugging -> save exported file to disk
  # open('file.tar.gz', 'wb').write(project_data)

  # modify repo
  modified_project_data = modify_repo(project_data)
  print()

  # Debugging -> save modified exported file to disk
  # open('file.tar.gz', 'wb').write(modified_project_data)

  # Import
  import_project(dest, modified_project_data)


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
  returns: (detected_source_project_path, project_data)
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
  print(f'- Detected path is: {detected_source_project_path}')

  # Initiate export
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

  return (detected_source_project_path, project_data)


def import_project(dest, project_data):
  '''
  dest: dest project in format namespace/project.
  project_data: the contents of the exported project
  '''
  print(f'Importing project to {dest}.')
  # Split import location into namespace and path
  if len(dest.rsplit("/", 1)) != 2:
    print(f'- Unable to split {dest} into namespace and path with delimiter = /.')
    sys.exit(1)

  dest_namespace = dest.rsplit("/", 1)[0]
  dest_path = dest.rsplit("/", 1)[1]
  print(f'- Importing to namespace={dest_namespace}, path={dest_path}.')

  headers = {
    'PRIVATE-TOKEN': f'{DST_TOKEN}'
  }
  files = {
    'file': ('file.tar.gz', BytesIO(project_data))
  }
  data = {
    # 'path': f'{dest}',
    "namespace": dest_namespace,
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
  "python3 gitlab-api.py <-g|-p> <-s source> [-d dest]\n"
  "\n"
  "Options\n"
  "-------------\n"
  "-g: migrate group\n"
  "  -s: source group in form of either group_id or group/subgroup\n"
  "  -d: dest group in form of either group_id or group/subgroup. Takes source path if not provided.\n"
  "-p: migrate project\n"
  "  -s: source project in form of either project_id or namespace/project\n"
  "  -d: dest project in form of namespace/project. Takes source path if not provided.\n"  
  "\n"
  )


def main():
  try:
    opts, args = getopt.getopt(sys.argv[1:], "s:d:gp")
  except getopt.GetoptError as err:
    print(err)
    print_help()
    sys.exit(1)

  # Print help if no arguments provided
  if len(sys.argv) == 1:
    print_help()
    sys.exit(1)

  # Set config from arguments
  source = None
  dest = None
  migrate_action = None
  for key, value in opts:
    if key == "-s":
      source = value
    elif key == "-d":
      dest = value
    elif key == "-g":
      migrate_action = Action.MIGRATE_GROUP
    elif key == "-p":
      migrate_action = Action.MIGRATE_PROJECT
    else:
      print(f"Error: Unhandled option {key}")
      sys.exit(1)
    
  # Check that necessary config are set
  if not source or not migrate_action:
    print("Error: Some values were not set.")
    print_help()
    sys.exit(1)

  # Perform repo action
  if migrate_action == Action.MIGRATE_GROUP:
    migrate_group(source, dest)
  elif migrate_action == Action.MIGRATE_PROJECT:
    migrate_project(source, dest)


if __name__ == "__main__":
  main()
