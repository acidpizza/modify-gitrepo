#!/usr/bin/env python3

import getopt, sys
from enum import Enum, auto
import os
import git_filter_repo

'''
Example usage at: https://github.com/newren/git-filter-repo/tree/main/contrib/filter-repo-demos
'''

# ---------------------------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------------------------

AUTHORS = set()
def callback_get_author_names(commit, metadata):
  AUTHORS.add(commit.author_name)


def callback_modify_repo(commit, metadata):
  # Map of user to userinfo
  users = {
    b"olduser_1" : {
      "new_name" : b"modified - olduser1",
      "new_email" : b"modified-olduser1@nowhere.com",
    },
    b"olduser_2" : {
      "new_name" : b"modified - olduser2",
      "new_email" : b"modified-olduser2@nowhere.com",
    },
  }

  # --- Debugging ---
  # if commit.author_name in users:
  #   print(f'{users[commit.author_name]["new_name"]}')

  # Replace parameters for users matching author_name in each commit
  if commit.author_name in users:
    userinfo = users[commit.author_name]
    commit.author_name = userinfo["new_name"]
    commit.author_email = userinfo["new_email"]
    commit.committer_name = userinfo["new_name"]
    commit.committer_email = userinfo["new_email"]


# ---------------------------------------------------------------------------
class Action(Enum):
  GET_USERS = auto()
  MODIFY_REPO = auto()
  ANALYZE_REPO = auto()

'''
git_filter_repo.FilteringOptions.default_options():
analyze=False,
blob_callback=None,
commit_callback=None,
debug=False,
dry_run=False,
email_callback=None,
filename_callback=None,
force=False,
help=False,
inclusive=False,
mailmap=None,
max_blob_size=0,
message_callback=None,
name_callback=None,
no_ff=False,
partial=False,
path_changes=[],
preserve_commit_encoding=False,
preserve_commit_hashes=False,
prune_degenerate='auto',
prune_empty='auto',
quiet=False,
refname_callback=None,
refs=['--all'],
repack=True,
replace_message=None,
replace_refs=None,
replace_text=None,
report_dir=None,
reset_callback=None,
source=None,
state_branch=None,
stdin=False,
strip_blobs_with_ids=set(),
subdirectory_filter=None,
tag_callback=None,
tag_rename=None,
target=None,
to_subdirectory_filter=None,
use_base_name=False,
version=False
'''

def get_users(repo_path):
  args = git_filter_repo.FilteringOptions.default_options()
  args.source = repo_path
  args.dry_run = True
  args.force = True if FORCE else False
  filter = git_filter_repo.RepoFilter(args, commit_callback = callback_get_author_names)
  filter.run()

  print('List of authors:')
  for author in AUTHORS:
    print(author)


def modify_repo(repo_path):
  args = git_filter_repo.FilteringOptions.default_options()
  args.source = repo_path
  args.target = repo_path.encode('utf-8')
  args.replace_refs = '--update-no-add'
  args.force = True if FORCE else False
  filter = git_filter_repo.RepoFilter(args, commit_callback = callback_modify_repo)
  filter.run()


def analyze_repo(repo_path, report_folder):
  # Get absolute path of report folder as we will be changing directory
  report_folder_abs = os.path.abspath(report_folder)
  
  # analyze repo only works on current directory
  os.chdir(repo_path)

  args = git_filter_repo.FilteringOptions.default_options()
  args.report_dir = report_folder_abs.encode('utf-8')
  args.force = True if FORCE else False
  git_filter_repo.RepoAnalyze.run(args)


def print_help():
  print("This script assists in modifying commit history.\n"
  "\n"
  "Usage\n"
  "-----\n"
  "Get all unique users in repo: modify-gitrepo.py -u -r <repo_path>\n"
  "Modify commit history       : modify-gitrepo.py -m -r <repo_path>\n"
  "Analyze Repo                : modify-gitrepo.py -a <report_folder> -r <repo_path>\n"
  "-----\n"
  "Global Options\n"
  "-f : force\n"
  )


def main():
  try:
    opts, args = getopt.getopt(sys.argv[1:], "r:umaf:")
  except getopt.GetoptError as err:
    print(err)
    print_help()
    sys.exit(1)

  # Print help if no arguments provided
  if len(sys.argv) == 1:
    print_help()
    sys.exit(1)

  # Set config from arguments
  repo_path = None
  report_folder = None
  repo_action = None
  FORCE = False
  for key, value in opts:
    if key == "-r":
      repo_path = value
    elif key == "-u":
      repo_action = Action.GET_USERS
    elif key == "-m":
      repo_action = Action.MODIFY_REPO
    elif key == "-a":
      repo_action = Action.ANALYZE_REPO
      report_folder = value
    elif key == "-f":
      FORCE = True
    else:
      print(f"Error: Unhandled option {key}")
      sys.exit(1)
    
  # Check that necessary config are set
  if not repo_path or not repo_action:
    print("Error: Some values were not set.")
    print_help()
    sys.exit(1)

  # Perform repo action
  if repo_action == Action.GET_USERS:
    get_users(repo_path)
  elif repo_action == Action.MODIFY_REPO:
    modify_repo(repo_path)
  elif repo_action == Action.ANALYZE_REPO:
    analyze_repo(repo_path, report_folder)

if __name__ == "__main__":
  main()
