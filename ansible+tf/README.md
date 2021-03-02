# Ansible app deploy role

This playbook will install nginx as reverse proxy and copy virtual host config file to tagret hosts.

## Settings

-   `name:` virtual host's name
-   `address:` public address (url) (e.g. `app.example.com`)
-   `local_address:` local address and port where the application is running (e.g. `localhost:8080`)

## Running this playbook

### 1. Obtain the playbook
```
git@gitlab.rebrainme.com:devops_users_repos/1373/ansible.git
cd ansible
```
### 2. Customize options
Check 'Settings' part.
```
vim roles/app/var/main.yml
```
### 3. Create host file (if necessary)
```
vim hosts
```
```
# hosts
[my-hosts]
host1
host2
```
### 4. Run the playbook
```
ansible-playbook -l [target] -i [inventory file] -u [remote user] deploy.yml
```
