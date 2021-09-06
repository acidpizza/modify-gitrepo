#!/bin/bash

set -euo pipefail

# -------------------------- README ----------------------------------------------------
# Usage:
# 1. Git clone git-filter-repo git repo: https://github.com/newren/git-filter-repo
# 2. Add git-filter-repo to path. Easiest is to copy into /usr/local/bin.
# 3. Modify this script with your desired user map.
# 4. Run this script based on help instructions below.
# --------------------------------------------------------------------------------------

print_help() 
{ 
  echo "This script assists in modifying commit history." 
  echo "" 
  echo "Usage"
  echo "-----"
  echo "Get all unique users in repo: ${0} -u -r <repo_path>"
  echo "Modify commit history       : ${0} -m -r <repo_path>" 
} 

# Show all unique users in the repo
get_users()
{
  # Python3 code to perform logic on each commit
  # Add --force flag before --commit-callback flag to force the run if there are warnings
  git -C ${REPO_PATH} filter-repo --replace-refs update-no-add --commit-callback '
    print(commit.author_name)
    print("")
    ' 2>&1 | grep "b'" | sort | uniq
}

# Replaces author_name, author_email, committer_name, committer_email of multiple users.
modify_repo()
{
  # Python3 code to perform logic on each commit
  # Add --force flag before --commit-callback flag to force the run if there are warnings
  git -C ${REPO_PATH} filter-repo --replace-refs update-no-add --commit-callback '
    
    # Important: Commit values must be defined as byte strings
    # key - author_name to effect change on
    # value - new attributes (name, email) to be updated
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
    # Use triple-quotes for f-strings as single-quote and double-quote used already
    # if commit.author_name in users: 
    #   print(f"""{users[commit.author_name]["new_name"]}""")

    # Replace parameters for users matching author_name in each commit
    if commit.author_name in users:
      userinfo = users[commit.author_name]
      commit.author_name = userinfo["new_name"]
      commit.author_email = userinfo["new_email"]
      commit.committer_name = userinfo["new_name"]
      commit.committer_email = userinfo["new_email"]
    '
}

# --- MAIN --- 
if (( $# == 0 )); then 
  print_help 
  exit 1 
fi 
 
OPTIND=1 # Reset in case getopts has been used previously in the shell 

GET_USERS=0
MODIFY_REPO=0
REPO_PATH="" 
while getopts "umr:" opt; do 
  case $opt in 
    u)
      # get users option
      GET_USERS=1
      ;; 
    m)
      # modify repo option
      MODIFY_REPO=1
      ;; 
    r)
      # repo path
      REPO_PATH="${OPTARG}"
      ;; 
    \?)
      echo "Invalid option: -$OPTARG" 
      exit 1 
      ;; 
  esac 
done 
 
if [[ "${REPO_PATH}" == "" ]]; then 
  echo "No valid repo path was set."
  print_help 
  exit 1 
fi

if (( GET_USERS == 1 )); then
  get_users

elif (( MODIFY_REPO == 1 )); then
  modify_repo

else
  echo "No valid command was set."
  print_help
  exit 1
fi
