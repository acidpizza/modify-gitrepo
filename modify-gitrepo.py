#!/usr/bin/env python3

import getopt, sys
from enum import Enum, auto
import git_filter_repo

'''
Example usage at: https://github.com/newren/git-filter-repo/tree/main/contrib/filter-repo-demos
'''

class Action(Enum):
  GET_USERS = auto()
  MODIFY_REPO = auto()

def print_help():
  print("This script assists in modifying commit history.\n" 
  "\n" 
  "Usage\n"
  "-----\n"
  "Get all unique users in repo: modify-gitrepo.py -u -r <repo_path>\n"
  "Modify commit history       : modify-gitrepo.py -m -r <repo_path>\n" 
  )


def callback_print_author_names(commit, metadata):
  print(commit.author_name)


def get_users(repo_path):
  args = [
    '--replace-refs',
    '--update-no-add',
  ]
  filter = git_filter_repo.RepoFilter(args, commit_callback = callback_print_author_names)
  filter.run()


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
  # elif repo_action == Action.MODIFY_REPO:
  #   modify_repo(repo_path)

if __name__ == "__main__":
  main()