#!/bin/env python3
# -*- encoding=utf-8 -*-
"""
# **********************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2021-2021. All rights reserved.
# [openeuler-jenkins] is licensed under the Mulan PSL v1.
# You can use this software according to the terms and conditions of the Mulan PSL v1.
# You may obtain a copy of Mulan PSL v1 at:
#     http://license.coscl.org.cn/MulanPSL
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v1 for more details.
# Author: wangge
# Create: 2021-10-29
# **********************************************************************************
"""
import re
import paramiko
import requests
import os
import argparse
import time
import subprocess
import base64
import json
import socket
from libs.cloud.HWCloud.ecs_servers import ecs_server
from libs.log.logger import log_check
from main.common.executecmd import ExecuteCmd
from main.common.aes_decode import AESEncryAndDecry


class QueryOBSWorker(object):
    """
    query osb worker status such as:
    1.query obs worker instance status
    2.get idle instance distribution
    3.get obs worker list in idle status
    """
    
    @staticmethod
    def get_worker_value_name_password():
        """
        @description : get worker name and password decrypt file
        -----------
        @param : NA
        -----------
        @returns : 
            AESEncryAndDecry().decrypt_file
        ----------
        """
        decryptor = AESEncryAndDecry(DECRYPTION_KEY,DECRYPT_FILE_PATH)
        return decryptor.decrypt_file
        
    def get_monitor_resource(resource,ip,times):
        """
        @description : from url get json value
        -----------
        @param : 
            resource : mem,cpu,network,IOPS
            ip : ip address
            times : average time
        -----------
        @returns :
            str(round(float(requests.post(xxx).json()[x][x][x][x][x][x])))
        ----------
        """
        instance_ip = ip + ":9100"
        url_add = "https://openeuler-beijing4-prometheus.osinfra.cn/api/v1/query?query="
        #cpu
        url_cpu = f"{url_add}100%20-%20avg(irate(node_cpu_seconds_total{{instance=\"{instance_ip}\",mode=\"idle\"}}[{times}]))by(instance)*100"
    
        #mem
        url_mem = f"{url_add}100%20-%20(node_memory_MemAvailable_bytes{{instance=\"{instance_ip}\"}})%2F(node_memory_MemTotal_bytes{{instance=\"{instance_ip}\"}})*100"
        #IOPS-read
        url_read = f"{url_add}max(irate(node_disk_read_bytes_total{{instance=\"{instance_ip}\"}}[{times}]))%20by%20(instance)"
    
        #IOPS-write
        url_write = f"{url_add}max(irate(node_disk_written_bytes_total{{instance=\"{instance_ip}\"}}[{times}]))%20by%20(instance)"

        #network-recive
        url_recive = f"{url_add}sum(irate(node_network_receive_bytes_total{{instance=\"{instance_ip}\",device!~\"bond.*?|lo\"}}[{times}])/128)by(instance)"

        #network-transmit
        url_transmit = f"{url_add}sum(irate(node_network_transmit_bytes_total{{instance=\"{instance_ip}\",device!~\"bond.*?|lo\"}}[{times}])/128)by(instance)"


        headers = {'Content-type':'application/json'}
        data = {"order":2,"index_patterns":["stdout-*"],"settings":{"index":{"max_result_window":"200000"}}}
        result = self.get_worker_value_name_password()
        result_cut = result.split('\n')
        username = result_cut[0]
        password = result_cut[1]
        if resource == 'mem':
            r_url = url_mem
        elif resource == 'CPU':
            r_url = url_cpu
        elif resource == 'IOPS-read':
            r_url = url_read
        elif resource == 'IOPS-write':
            r_url = url_write
        elif resource == 'NET-recive':
            r_url = url_recive
        elif resource == 'NET-transmit':
            r_url = url_transmit
        else:
            return None
        r=requests.post(url = r_url,headers = headers,data = json.dumps(data),auth = (username,password))
        try:
            resource_value = str(round(float(r.json()['data']['result'][0]['value'][1]),2))
            if resource == 'mem' or resource == 'CPU':
                value = resource_value + '%'
            else:
                value = resource_value + 'kb/s'
        except BaseException as e:
            log_check.error(f'please check your value,due to {e}')
            value = '0'
        return value

    def get_monitor_value(self,ip,times,resource):
        """
        @description : get ip cpu,mem,IOPS and network
        ------------
        @param : 
            ip : ip addrass
            times : how many minutes
            resource : cpu,mem,IOPS,network
        -----------
        @returns :
            resource_info : cpu,mem,IOPS,network in dictionary  
        """
        resource_info = {}
        resource_info['IP'] = ip
        resource_info['times'] = times
        times_check = re.findall(r'\d+m$',times)
        if times_check:
            if times_check[0] == times:
                resource_info['times'] = times
            else:
                return resource_info
        else:
            log_check.error(f'times error')
            return resource_info
        
        if resource == 'all':
            resource_info['mem'] = self.get_monitor_resource('mem',ip,times)
            resource_info['CPU'] = self.get_monitor_resource('CPU',ip,times)
            resource_info['IOPS-read'] = self.get_monitor_resource('IOPS-read',ip,times)
            resource_info['IOPS-write'] = self.get_monitor_resource('IOPS-write',ip,times)
            resource_info['NET-recive'] = self.get_monitor_resource('NET-recive',ip,times)
            resource_info['NET-transmit'] = self.get_monitor_resource('NET-transmit',ip,times)       
        else:
            resource_info[resource] = self.get_monitor_resource(resource,ip,times)
        return resource_info


    def get_all_worker_list(self):
        """
        @description : get a list shows all workers and is divided arch and x86
        ------------
        @param : NA
        -----------
        @returns : 
            obs_worker_list : a list shows all workers and is divided arch and x86
        """
        obs_worker_list = {"aarch64":[],"x86":[]}
        server_list = ecs_server.list_servers()
        if server_list['code'] != 200:
            log_check.error(f'not exist this obs_worker_list')
            return server_list['error']
        else:
            pass
        for i in range(len(server_list['servers'])):
            if server_list['servers'][i]['arch'] == 'aarch64':
                obs_worker_list["aarch64"].append(server_list['servers'][i]['ip'])
            else:
                obs_worker_list["x86"].append(server_list['servers'][i]['ip'])
        return obs_worker_list


    def check_worker_status(self,ip):
        """
        @description : get worker machine status 
        -------------
        @param :
            ip : ip address
        -------------
        @returns : 
            machine_status : a dictionary about ip and status   
        """
        try:
            server_ip = ecs_server.get_server(ip)
            if server_ip['code'] != 200:
                log_check.error(f'this ip is not exist')
                return server_ip['error']
            else:
                pass
            
            machine_status = {'ip':server_ip['server']['ip'],'status':server_ip['server']['status']}
            return machine_status
        except BaseException as e:
            log_check.error(f'this IP is not exist,due to {e}')
            return None

    def check_service(self,ip,passwd):
        """
        @description : check ip obsworker service status
        -------------
        @param : 
            ip : ip addrass
            passwd : ip password
        -------------
        @returns : 
            service_state:a dictionary about ip and status
        """
        service_state = dict()
        service_state["ip"] = ip
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname = ip,
                username = 'root',
                password = passwd,
                timeout = 5
                )
            stdin,stdout,stderr = client.exec_command('systemctl status obsworker')
        except socket.timeout as e:
            log_check.error(f"Not connect this ip,please check password or ip,due to {e}")
            client.close()
            return None
        str_obs = stdout.read().decode('utf-8')
        str_obs = str_obs.split("Active: ")
        str_obs = str_obs[1].split(" ")
        str_obs = str_obs[0]
        if str_obs == "active":
            service_state["service_OK"] = "0"
        else:
            service_state["service_OK"] = "1"
        client.close()
        return service_state

    def get_worker_config_value(self,str_worker_value,config_value_cut):
        try:
            str_value = str_worker_value.split(config_value_cut)
            str_value = str_value[1].split("\"")
            str_value = str_value[0]
        except IndexError as e:
            log_check.error(f'get error due to {e}')
            return None
        return str_value

    def check_worker_config(self,ip,passwd,config):
        """
        @description : check worker config is it consistent
        -------------
        @param : 
            ip : ip address
            passwd : ip address password
            config : a dectionary about jobs,instances,vcpus,ram
        @returns : 
            consistency_result : is it consistent true or false
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=ip,
                username='root',
                password=passwd,
                timeout=5
                )
            """
            get the values of jobs and instances from obs-server
            """
            stdin,stdout,stderr = client.exec_command("cat /etc/sysconfig/obs-server")
        except socket.timeout as e:
            log_check.error(f'Not connect this IP.due to {e}')
            client.close()
            consistency_result = False
            return consistency_result
        str_value = stdout.read().decode('utf-8')
        str_ins = self.get_worker_config_value(str_value,"\nOBS_WORKER_INSTANCES=\"")
        str_jobs = self.get_worker_config_value(str_value,"\nOBS_WORKER_JOBS=\"")
        str_repo_servers = self.get_worker_config_value(str_value,"\nOBS_REPO_SERVERS=\"")
        server_get = ecs_server.get_server(ip)
        if server_get["code"] != 200:
            log_check.error(f'get server information from {ip} failed')
            consistency_result = False
            client.close()
            return consistency_result
        if str_ins == config['instances'] and str_jobs == config['jobs'] and str_repo_servers == config['repo_server']:
            try:
                if config['vcpus'] == server_get['server']['flavor']['vcpus'] and config['ram'] == server_get['server']['flavor']['ram']:
                    consistency_result = True
                else:
                    consistency_result = False
            except KeyError as e:
                log_check.error(f'error due to {e}')
                consistency_result = False
                client.close()
                return consistency_result
            except AttributeError as e:
                log_check.error(f'error due to {e}')
                consistency_result = False
                client.close()
                return consistency_result
        else:
            try:
                origin_instance_content = 'OBS_WORKER_INSTANCES="' + str_ins + '"'
                origin_jobs_content = 'OBS_WORKER_JOBS="' + str_jobs + '"'
                origin_repo_servers_content = 'OBS_REPO_SERVERS="' + str_repo_servers + '"'
                client_modify_instance_cmd = "sed -i 's/" + origin_instance_content + "/OBS_WORKER_INSTANCES=\"" + config['instances'] + "\"/g' /etc/sysconfig/obs-server"
                client.exec_command(client_modify_instance_cmd)
                client_modify_jobs_cmd = "sed -i 's/" + origin_jobs_content + "/OBS_WORKER_JOBS=\"" + config['jobs'] + "\"/g' /etc/sysconfig/obs-server"
                client.exec_command(client_modify_jobs_cmd)
                client_modify_repo_servers_cmd = "sed -i 's/" + origin_repo_servers_content + "/OBS_REPO_SERVERS=\"" + config['instances'] + "\"/g' /etc/sysconfig/obs-server"
                client.exec_command('systemctl restart obsworker')
                worker_name = server_get["server"]["name"]
                dest_instance = config['instances']
                dest_jobs = config['jobs']
                dest_repo_servers = config['repo_server']
                log_check.info(f'worker:{worker_name}, ip:{ip}, change instance / jobs / repo_server form {str_ins} / {str_jobs} / {str_repo_servers} to {dest_instance} / {dest_jobs} / {dest_repo_servers}')
                consistency_result = True
            except BaseException as e:
                log_check.error(f'error due to {e}')
                consistency_result = False
        client.close()
        return consistency_result           
