#!/usr/bin/env python3

import getopt, sys
from enum import Enum, auto
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


def get_users(repo_path):
  args = git_filter_repo.FilteringOptions.default_options()
  args.source = repo_path
  args.dry_run = True
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
  filter = git_filter_repo.RepoFilter(args, commit_callback = callback_modify_repo)
  filter.run()


def print_help():
  print("This script assists in modifying commit history.\n"
  "\n"
  "Usage\n"
  "-----\n"
  "Get all unique users in repo: modify-gitrepo.py -u -r <repo_path>\n"
  "Modify commit history       : modify-gitrepo.py -m -r <repo_path>\n"
  )


def main():
  try:
    opts, args = getopt.getopt(sys.argv[1:], "umr:")
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
  repo_action = None
  for key, value in opts:
    if key == "-r":
      repo_path = value
    elif key == "-u":
      repo_action = Action.GET_USERS
    elif key == "-m":
      repo_action = Action.MODIFY_REPO
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

if __name__ == "__main__":
  main()