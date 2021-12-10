# Test Migration of Gitlab

## Get initial password
```
sudo docker exec -it gitlab grep 'Password:' /etc/gitlab/initial_root_password
```

# Pure Python Implementatoin for Modfy Gitrepo

```bash
# Get dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python3 modify-gitrepo.py

# Exit venv
deactivate
```