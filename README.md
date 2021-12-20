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

# Run
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
