#!/usr/bin/python3
import json
import os
import requests
import time
import yaml
from libs.log.logger import log_check
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retries = Retry(total=3, backoff_factor=0.1)
session = requests.Session()
session.mount('https://', HTTPAdapter(max_retries=retries))
timeout = 5


class ECSServers(object):
    """
    wrapped HUAWEI CLOUD ECS Servers APIs
    """

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
            self.region = info.get('region')
            self.project_id = info.get('projectId')
            self.headers = self.get_auth_header(self.region)
            self.name_prefix = info.get('name_prefix')
            self.vpcId = info.get('vpcId')
            self.subnetId = info.get('subnetId')
            self.security_group_id = info.get('security_group_id')
            self.volumetype = info.get('volumetype')
            self.waiting_time = info.get('waiting_time')
            self.query_times = info.get('query_times')
            self.server_boot_time = info.get('server_boot_time')
            self.max_servers_number = info.get('max_servers_number')
            self.max_list_number = info.get('max_list_number')
            self.flavorMapping = info.get('flavorMapping')
            self.archMapping = info.get('archMapping')

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
        response = session.post(url, data=json.dumps(data), timeout=timeout)
        try:
            token = response.headers["X-Subject-Token"]
            header = {'X-Auth-Token': token}
            log_check.info('Get authorized header: Successful')
            return header
        except KeyError:
            log_check.error('Get authorized token: Fail to get auth token.')

    def validate_create_fields(self, arch, flavor_level, admin_pass, count):
        """
        Validation of the created fields
        :param arch: architecture of servers
        :param flavor_level: specifies the flavor level of servers
        :param admin_pass: password for root
        :param count: numbers of servers
        :return:
        """
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
        if max_number_can_create == 0:
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
        """
        Data for creating servers
        :param admin_pass: password for root
        :param count: numbers of servers
        :param flavorRef: name of flavor
        :param imageRef: UUID of image
        :param name: server name
        :param vpcid: UUID of VPC
        :param subnet_id: UUID of subnet
        :param security_group_id: UUID of security group
        :param volumetype:
        :return:
        """
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
        response = session.post(url, headers=self.headers, data=json.dumps(data), timeout=timeout)
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

    def get_format_server(self, server, status='ACTIVE'):
        """
        Get formatted data of a server
        :param server: a dict of server data
        :param status: running status of the server
        :return: a dict contained id, name, ip, status, flavor and arch
        """
        format_server = {
            'id': server.get('id'),
            'name': server.get('name'),
            'ip': server.get('addresses').get(list(server.get('addresses').keys())[0])[0].get('addr') if server.get(
                'addresses') else '',
            'status': status,
            'flavor': {
                'vcpus': server.get('flavor').get('vcpus'),
                'ram': server.get('flavor').get('ram')
            },
            'arch': self.get_arch(server.get('flavor').get('name'))
        }
        return format_server

    def list_servers(self):
        """
        List all active servers about obs
        :return: a list of all server details
        """
        url = 'https://ecs.{}.myhuaweicloud.com/v1/{}/cloudservers/detail?limit={}&status=ACTIVE&name=obs'.format(
            self.region, self.project_id, self.max_list_number)
        response = session.get(url, headers=self.headers, timeout=timeout)
        if response.status_code == 200:
            servers = []
            for server in response.json().get('servers'):
                if server.get('addresses'):
                    format_server = self.get_format_server(server)
                    servers.append(format_server)
            result = {'code': 200, 'servers': servers}
        else:
            result = {'code': 400, 'error': response.json()}
        return result

    def get_server(self, server_ip):
        """
        Get a server detail by server_ip
        :param server_ip: IP address
        :return: server detail
        """
        server_id = self.get_server_id(server_ip)
        if not server_id:
            log_check.error('Get server: IP {} does not exists.'.format(server_ip))
            return {'code': 400, 'error': 'Not exist'}
        url = ' https://ecs.{}.myhuaweicloud.com/v1/{}/cloudservers/{}'.format(self.region, self.project_id, server_id)
        response = session.get(url, headers=self.headers, timeout=timeout)
        if response.status_code == 200:
            server = response.json().get('server')
            status = server.get('status')
            if status == 'BUILD':
                status = 'BUILDING'
            elif status not in ['BUILDING', 'ACTIVE', 'DELETED']:
                status = 'OTHER'
            format_server = self.get_format_server(server, status)
            result = {'code': 200, 'server': format_server}
            log_check.info('Get server: {}'.format(result))
        else:
            result = {'code': 400, 'error': response.json()}
            log_check.error('Get server: {}'.format(result))
        return result

    def delete_servers(self, serverIps):
        """
        Delete servers
        :param serverIps: a list of IP address
        :return:
        """
        serverIds = self.get_server_ids(serverIps)
        url = 'https://ecs.{}.myhuaweicloud.com/v1/{}/cloudservers/delete'.format(self.region, self.project_id)
        servers = [{'id': server_id} for server_id in serverIds]
        data = {
            'delete_publicip': True,
            'delete_volume': True,
            'servers': servers
        }
        response = session.post(url, headers=self.headers, data=json.dumps(data), timeout=timeout)
        if response.status_code == 200:
            result = {'code': 200, 'message': 'Delete successfully'}
            log_check.info('Delete servers: {}'.format(serverIps))
        else:
            result = {'code': 400, 'error': response.json()}
            log_check.error('Delete servers: {}'.format(result))
        return result

    def get_arch(self, flavor_name):
        """
        Get architecture by flavor_name
        :param flavor_name: name of flavor
        :return: architecture of the server
        """
        for arch in self.archMapping:
            if flavor_name in self.archMapping.get(arch):
                return arch

    def get_server_maps(self):
        """
        Get mapping between IP addresses and server_ids
        :return: A list of nested dictionaries {ip: server_id}
        """
        url = 'https://ecs.{}.myhuaweicloud.com/v1/{}/cloudservers/detail?limit={}&status=ACTIVE&name=obs'.format(
            self.region, self.project_id, self.max_list_number)
        response = session.get(url, headers=self.headers, timeout=timeout)
        if response.status_code == 200:
            server_maps = [
                {server.get('addresses').get(list(server.get('addresses').keys())[0])[0].get('addr'): server.get('id')}
                if server.get('addresses') else {None: server.get('id')}
                for server in response.json()['servers']]
            return server_maps
        else:
            return {}

    def get_hostname_maps(self):
        """
        Get mapping between IP addresses and hostnames
        :return: A list of nested dictionaries {IP: hostname}
        """
        url = 'https://ecs.{}.myhuaweicloud.com/v1/{}/cloudservers/detail?limit={}&status=ACTIVE&name=obs'.format(
            self.region, self.project_id, self.max_list_number)
        response = session.get(url, headers=self.headers, timeout=timeout)
        if response.status_code == 200:
            hostname_maps = [{server.get('addresses').get(list(server.get('addresses').keys())[0])[0].get(
                'addr'): server.get('name')}
                             if server.get('addresses') else {None: server.get('id')}
                             for server in response.json()['servers']]
            return hostname_maps
        else:
            return {}

    def get_hostname(self, server_ip):
        """
        Get hostname of the server through IP address
        :param server_ip: IP address
        :return: hostname of the server
        """
        servers = self.get_hostname_maps()
        for server in servers:
            if server.get(server_ip):
                hostname = server.get(server_ip)
                return hostname

    def get_server_id(self, server_ip):
        """
        Get the server_id through IP address
        :param server_ip: IP address
        :return: server_id
        """
        servers = self.get_server_maps()
        for server in servers:
            if server.get(server_ip):
                server_id = server.get(server_ip)
                return server_id

    def get_server_ids(self, server_ips):
        """
        Get a list of server_id through IP addresses
        :param server_ips: list of IP address
        :return: list of server_id
        """
        servers = self.get_server_maps()
        server_ids = []
        for ip in server_ips:
            for server in servers:
                if server.get(ip):
                    server_id = server.get(ip)
                    server_ids.append(server_id)
                    break
        return server_ids

    def get_server_ip(self, server_id: str):
        """
        Get IP address through server_id
        :param server_id: server_id
        :return: IP address
        """
        servers = self.get_server_maps()
        for server in servers:
            if server.get(list(server.keys())[0]) == server_id:
                return list(server.keys())[0]

    def get_server_ips(self, server_ids: list):
        """
        Get a list of IP addresses through server_ids
        :param server_ids: list of server_id
        :return: list of IP address
        """
        servers = self.get_server_maps()
        server_ips = []
        for server_id in server_ids:
            for server in servers:
                server_ip = list(server.keys())[0]
                if server.get(server_ip) == server_id:
                    server_ips.append(server_ip)
                    break
        return server_ips

    def get_max_number_can_create(self):
        """
        Get maximum number of servers can be created
        :return: count of remaining servers can be created or None when error occurs
        """
        url = 'https://ecs.{}.myhuaweicloud.com/v1/{}/cloudservers/detail'.format(self.region, self.project_id)
        response = session.get(url, headers=self.headers, timeout=timeout)
        if response.status_code != 200:
            result = {'code': 400, 'error': response.json()}
            log_check.error('Get max number can create: {}'.format(result))
            return 0
        count = response.json().get('count')
        max_servers_number = self.max_servers_number
        return max_servers_number - count


ecs_server = ECSServers('/usr/li-wen/libs/conf/ecs_servers.yaml')

