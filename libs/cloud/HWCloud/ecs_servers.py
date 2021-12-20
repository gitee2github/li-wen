#!/usr/bin/python3
import json
import os
import requests
import time
import yaml
from libs.log.logger import log_check


class ECSServers(object):
    def __init__(self, conf_path):
        super(ECSServers, self).__init__()
        self.conf_path = conf_path
        info = {}
        try:
            with open(self.conf_path, 'r', encoding='utf-8') as fp:
                info = yaml.safe_load(fp)
        except yaml.MarkedYAMLError as e1:
            log_check.error(e1)
        except FileNotFoundError as e2:
            log_check(e2)
        if info:
            region = info.get('region')
            project_id = info.get('projectId')
            headers = self.get_auth_header(region)
            name_prefix = info.get('name_prefix')
            vpcId = info.get('vpcId')
            subnetId = info.get('subnetId')
            security_group_id = info.get('security_group_id')
            volumetype = info.get('volumetype')
            waiting_time = info.get('waiting_time')
            query_times = info.get('query_times')
            server_boot_time = info.get('server_boot_time')
            max_servers_number = info.get('max_servers_number')
            max_list_number = info.get('max_list_number')
            flavorMapping = info.get('flavorMapping')
            archMapping = info.get('archMapping')
            ECSServers.info = info
            ECSServers.region = region
            ECSServers.project_id = project_id
            ECSServers.headers = headers
            ECSServers.name_prefix = name_prefix
            ECSServers.vpcId = vpcId
            ECSServers.subnetId = subnetId
            ECSServers.security_group_id = security_group_id
            ECSServers.volumetype = volumetype
            ECSServers.waiting_time = waiting_time
            ECSServers.query_times = query_times
            ECSServers.server_boot_time = server_boot_time
            ECSServers.max_servers_number = max_servers_number
            ECSServers.max_list_number = max_list_number
            ECSServers.flavorMapping = flavorMapping
            ECSServers.archMapping = archMapping

    @staticmethod
    def get_auth_header(project_region):
        """
        Get authorization header
        :param project_region: region of project
        :return: authorized header
        """
        url = os.getenv("AUTH_URL", "https://iam.myhuaweicloud.com/v3/auth/tokens")
        data = {
            "auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "domain": {
                                "name": os.getenv("IAM_DOMAIN", "")
                            },
                            "name": os.getenv("IAM_USER", ""),
                            "password": os.getenv("IAM_PASSWORD", "")
                        }
                    }
                },
                "scope": {
                    "project": {
                        "name": project_region
                    }
                }
            }
        }
        response = requests.post(url, data=json.dumps(data))
        try:
            token = response.headers["X-Subject-Token"]
            header = {'X-Auth-Token': token}
            log_check.info('Get authorized header: Successful')
            return header
        except KeyError:
            log_check.error('Get authorized token: Fail to get auth token.')

    def validate_create_fields(self, arch, flavor_level, admin_pass, count):
        if arch not in self.flavorMapping.keys():
            result = {'code': 400, 'error': 'Unmatched architecture name.'}
            log_check.error('Create servers: {}'.format(result))
            return result
        if flavor_level not in ['l1', 'l2', 'l3']:
            result = {'code': 400, 'error': 'The flavor_level must be one of ["l1", "l2", "l3"].'}
            log_check.error('Create servers: {}'.format(result))
            return result
        if len(admin_pass) < 8 or len(admin_pass) > 26:
            result = {'code': 400, 'error': 'The length of admin_pass must be 8-26.'}
            log_check.error('Create servers: {}'.format(result))
            return result
        if not (isinstance(count, int) and count > 0):
            result = {'code': 400, 'error': 'The count must be a positive integer.'}
            log_check.error('Create servers: {}'.format(result))
            return result
        max_number_can_create = self.get_max_number_can_create()
        if not max_number_can_create:
            result = {'code': 400, 'error': 'Cannot get maximum number of servers that can be created.'}
            log_check.error('Create servers: {}'.format(result))
            return result
        if count > max_number_can_create:
            result = {'code': 400, 'error': 'Exceeds maximum number of servers that can be created.'}
            log_check.error('Create servers: {}'.format(result))
            return result

    @staticmethod
    def get_create_data(admin_pass, count, flavorRef, imageRef, name, vpcid, subnet_id, security_group_id,
                        volumetype):
        data = {
            'server': {
                'adminPass': admin_pass,
                'count': count,
                'flavorRef': flavorRef,
                'imageRef': imageRef,
                'name': name,
                'nics': [
                    {
                        'subnet_id': subnet_id
                    }
                ],
                'root_volume': {
                    'volumetype': volumetype
                },
                'security_groups': [
                    {
                        'id': security_group_id
                    }
                ],
                'vpcid': vpcid
            }
        }
        return data

    def create_servers(self, arch, flavor_level, admin_pass, count=1):
        """
        Create servers
        :param admin_pass: password for root
        :param arch: architecture of servers
        :param flavor_level: specifies the flavor level of servers
        :param count: numbers of servers
        :return: a list of IP address of the available servers
        """
        result = self.validate_create_fields(arch, flavor_level, admin_pass, count)
        if result:
            return result

        url = 'https://ecs.{}.myhuaweicloud.com/v1/{}/cloudservers'.format(self.region, self.project_id)
        try:
            flavorRef = self.flavorMapping.get(arch).get(flavor_level)
            imageRef = self.flavorMapping.get(arch).get('imageRef')
            print(flavorRef, imageRef)
        except AttributeError as e:
            log_check.error(e)
            result = {'code': 400, 'error': e}
            return result
        name = self.name_prefix + str(int(time.time())) + '-' + arch
        vpcid = self.vpcId
        subnet_id = self.subnetId
        security_group_id = self.security_group_id
        volumetype = self.volumetype
        waiting_time = self.waiting_time
        query_times = self.query_times
        server_boot_time = self.server_boot_time
        data = self.get_create_data(admin_pass, count, flavorRef, imageRef, name, vpcid, subnet_id, security_group_id,
                                    volumetype)
        response = requests.post(url, headers=self.headers, data=json.dumps(data))
        if response.status_code == 200:
            serverIds = response.json()['serverIds']
            while query_times > 0:
                server_ips = self.get_server_ips(serverIds)
                if len(server_ips) == len(serverIds):
                    result = {'code': 200, 'server_ips': server_ips}
                    log_check.info('Create servers: {}'.format(result))
                    # return after servers startup
                    time.sleep(server_boot_time)
                    return result
                else:
                    query_times -= 1
                    time.sleep(waiting_time)
        else:
            result = {'code': 400, 'error': response.json()}
            log_check.error('Create servers: {}'.format(result))
            return result


ecs_server = ECSServers('/usr/li-wen/libs/conf/ecs_servers.yaml')
