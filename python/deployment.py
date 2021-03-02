import os.path
import re

import yaml
from jinja2 import Template

from vault import Vault


class SwarmDeployment:
    def __init__(self, project, service, new_version, team, environment,
                 replicas, image_name, url='', port=''):
        self.project = project
        self.service = service
        self.version = new_version
        self.old_version = ''
        self.team = team
        self.environment = environment
        self.url = url
        self.port = port
        self.replicas = replicas
        self.image_name = image_name
        self.compose_path = self.set_compose_path()
        self.compose_filename = self.set_compose_filename()
        self.lock_filename = self.set_lock_filename()
        self.lock_filename = self.set_lock_filename()
        self.env_filename = self.set_env_filename()
        self.swarm_stack = self.project + "-" + self.environment
        self.ext_network = self.swarm_stack + "-ext"
        # full name of service as it will exist in Swarm (e.g. for monitoring)
        self.swarm_service = self.swarm_stack + "_" + self.service
        if self.url:
            url_dict = self.set_host_and_prefix_from_url()
            self.host = url_dict['host']
            if 'postfix' in url_dict:
                self.postfix = url_dict['postfix']

    def set_compose_path(self):
        compose_path = "compose/" + self.project + "/" + self.environment + "/"
        return compose_path

    def set_compose_filename(self):
        filename = self.project + "-" + self.environment + "-" + self.team + ".yml"
        compose_filename = self.compose_path + filename
        return compose_filename

    def set_lock_filename(self):
        filename = self.project + "-" + self.environment + "-" + self.team + ".yml.lock"
        lock_filename = self.compose_path + "locks/" + filename
        return lock_filename

    def set_env_filename(self):
        env_filename = self.compose_path + self.service + ".env"
        return env_filename

    def set_host_and_prefix_from_url(self):
        try:
            host = self.url.split("//")[1].split("/")[0]
            postfix = self.url.split("//")[1].split("/", 1)[1]
            if postfix:
                return {'host': host, 'postfix': ('/' + postfix)}
            else:
                return {'host': host}
        except IndexError:
            host = self.url.split("//")[1].split("/")[0]
            return {'host': host}

    def url_string_from_compose(self):
        pattern = re.compile('^traefik.http.routers.*.rule=(.*)')
        with open(self.compose_path) as y:
            compose = yaml.safe_load(y)
        url_string = str([s for s in compose['services'][self.service]['deploy']['labels'] if pattern.match(s)])
        try:
            url_string = "http://" + (url_string.split("=")[1].split("`")[1]) + (url_string.split("=")[1].split("`")[3])
        except IndexError:
            url_string = "http://" + url_string.split("=")[1].split("`")[1]
        return url_string

    def env_file_from_vault(self):
        service_envs = Vault().get_service_envs(self.swarm_stack, self.service)
        if service_envs:
            out_file = open(self.env_filename, 'w')
            for key, value in service_envs.items():
                out_file.write(f'{key}={value}\n')
            out_file.close()
            print('[INFO] Creating env file')

    def delete_env_file(self):
        if os.path.isfile(self.env_filename):
            os.remove(self.env_filename)
            print('[INFO] Deleting env file')

    def file_from_template(self, template_file):
        service = open(template_file).read()
        template = Template(service)
        return template.render(deployment=self)

    def create_compose_file(self):
        if os.path.isfile(self.compose_filename):
            print('[INFO] Compose file exists, skipping creating new one')
            y = open(self.compose_filename, 'r')
            compose_data = yaml.safe_load(y)
            if self.service in compose_data['services']:
                print('[INFO] Service exists in compose file, changing only version')
                self.old_version = (compose_data['services'][self.service]['image']).split(':')[1]
                compose_data['services'][self.service]['image'] = self.image_name + ":" + self.version
                with open(self.compose_filename, 'w') as out_file:
                    out_file.write(yaml.dump(compose_data))
            else:
                print('[INFO] No such service in compose file, creating a new one from template')
                service_data = self.file_from_template('templates/service.tmpl')
                with open(self.compose_filename, 'r') as in_file:
                    buffer = in_file.readlines()
                with open(self.compose_filename, 'w') as out_file:
                    for line in buffer:
                        if line == "services:\n":
                            line = line + service_data + "\n"
                        out_file.write(line)
        else:
            print(f'[INFO] No compose file for {self.swarm_stack}, '
                  f'creating new one with service {self.service}')
            try:
                os.makedirs(self.compose_path)
                print('[INFO] Creating directory for new stack')
            except OSError as exc:
                print(f'[WARN] Failed creating dir - {exc}')
            compose_data = self.file_from_template('templates/compose.tmpl')
            with open(self.compose_filename, 'w') as out_file:
                out_file.write(compose_data)

