# Test Migration of Gitlab

## Get initial password
```
sudo docker exec -it gitlab grep 'Password:' /etc/gitlab/initial_root_password
```


# gitlab-api.py

This script automates a migration of git repo from src_gitlab to dst_gitlab, and performs desired repo modifications.

The modifications is performed by `modify-gitrepo.py`. The `callback_modify_repo` function in this script must be modified as desired.

This callback is run on every single commit in the repo. For example, commit history authors can be rewritten by updating the `users` dictionary.

```bash
# Get dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Need git >= 2.22.0 if using rhel7
yum install rh-git227
source /opt/rh/rh-git227/enable

# Modify values in set-env.sh
# Execute to set environment variables
source set-env.sh

# Run (MUST run from project root folder due to dependency with modify-gitrepo.py via relative path)
python3 gitlab-api.py

# Exit venv
deactivate
```


# modify-gitrepo.py

This is a pure Python implementation for `git-filter-repo` and can be used to manually modify a git repo.

```bash
# Get dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Need git >= 2.22.0 if using rhel7
yum install rh-git227
source /opt/rh/rh-git227/enable

# Run
python3 modify-gitrepo.py

# Exit venv
deactivate
```


# Exported Contents

## Group Exports

https://docs.gitlab.com/ee/api/group_import_export.html

```
Group exports include the following:

Group milestones
Group boards
Group labels
Group badges
Group members
Subgroups. Each subgroup includes all data above
Group wikis
```

## Project Exports 

https://docs.gitlab.com/ee/user/project/settings/import_export.html#exported-contents

```
The following items are exported:

Project and wiki repositories
Project uploads
Project configuration, excluding integrations
Issues with comments, merge requests with diffs and comments, labels, milestones, snippets, time tracking, and other project entities
Design Management files and data
LFS objects
Issue boards
Pipelines history
Push Rules
Awards

The following items are not exported:

Build traces and artifacts
Container registry images
CI/CD variables
Pipeline triggers
Webhooks
Any encrypted tokens
Merge Request Approvers
Repository size limits
```


# Notes

## Group / Project Visibility

Groups and projects are imported as private by default. If imported into a parent group, the group / project will inherit the parent group's visibility level.

https://docs.gitlab.com/ee/user/group/settings/import_export.html#important-notes