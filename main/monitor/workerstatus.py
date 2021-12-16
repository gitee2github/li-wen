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
from libs.cloud.HWCloud.ecs_servers import ECSServers
from libs.log.logger import log_check
from main.common.executecmd import ExecuteCmd
from main.common.aes_decode import AESEncryAndDecry

WORKER_INFO_PATH = '/var/tmp/OBS-WSDM/all_obs_worker_info.log'
INSTANCE_STATISTICS_PATH = '/var/tmp/OBS-WSDM/instance_statistics_tmp.log'
EMPTY_CMD_LIST = -1
ENCRYPTED_DATA_PATH = '/usr/obs-wsdm/libs/conf/worker_management_platform_login_info'
DECRYPT_FILE_PATH = '/usr/obs-wsdm/libs/conf/get_worker_value_login_info'
DECRYPTION_KEY = 'abcd1234'
EXECMD = ExecuteCmd()

class QueryOBSWorker(object):
    """
    query osb worker status such as:
    1.query obs worker instance status
    2.get idle instance distribution
    3.get obs worker list in idle status
    """
    def __init__(self):
        """
        init function 
        """
        self.server_dict = {}
        server = ECSServers()
        servers_dict = server.list()
        if servers_dict["code"] == 200:
            server_list = servers_dict["servers"]
        for single_machine in server_list:
            ip_key = single_machine["ip"]
            self.server_dict[ip_key] = single_machine
    
    def get_worker_value_name_password(self):
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
        
    def get_worker_value(self,r_url):
        """
        @description : from url get json value
        -----------
        @param : 
            r_url : get cpu,mem,IOPS and network from url
        -----------
        @returns :
            str(round(float(requests.post(xxx).json()[x][x][x][x][x][x]
        ----------
        """
        headers = {'Content-type':'application/json'}
        data = {"order":2,"index_patterns":["stdout-*"],"settings":{"index":{"max_result_window":"200000"}}}
        result = self.get_worker_value_name_password()
        username = result.split('\n')[0]
        password = result.split('\n')[1]
        r=requests.post(url=r_url,headers=headers,data=json.dumps(data),auth=(username,password))
        try:
            value=str(round(float(r.json()['data']['result'][0]['value'][1]),2))
        except BaseException as e:
            log_check.error(f'please check your value,due to {e} ')
            value='0'
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
        resource_info={}
        Instance = ip + ":9100"
        url_add = "https://openeuler-beijing4-prometheus.osinfra.cn/api/v1/query?query="
        #cpu
        url_cpu = f"{url_add}100%20-%20avg(irate(node_cpu_seconds_total{{instance=\"{Instance}\",mode=\"idle\"}}[{times}]))by(instance)*100"
    
        #mem
        url_mem = f"{url_add}100%20-%20(node_memory_MemAvailable_bytes{{instance=\"{Instance}\"}})%2F(node_memory_MemTotal_bytes{{instance=\"{Instance}\"}})*100"
        #IOPS-read
        url_read = f"{url_add}max(irate(node_disk_read_bytes_total{{instance=\"{Instance}\"}}[{times}]))%20by%20(instance)"
    
        #IOPS-write
        url_write = f"{url_add}max(irate(node_disk_written_bytes_total{{instance=\"{Instance}\"}}[{times}]))%20by%20(instance)"

        #network-recive
        url_recive = f"{url_add}sum(irate(node_network_receive_bytes_total{{instance=\"{Instance}\",device!~\"bond.*?|lo\"}}[{times}])/128)by(instance)"

        #network-transmit
        url_transmit = f"{url_add}sum(irate(node_network_transmit_bytes_total{{instance=\"{Instance}\",device!~\"bond.*?|lo\"}}[{times}])/128)by(instance)"

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
             
        if resource == 'all' or resource == 'mem':
            resource_info['mem']=self.get_worker_value(r_url=url_mem)+'%'
        if resource == 'all' or resource == 'CPU':   
            resource_info['CPU']=self.get_worker_value(r_url=url_cpu)+'%'
        if resource == 'all' or resource == 'IOPS':
            resource_info['IOPS-read']=self.get_worker_value(r_url=url_read)+'kb/s'
            resource_info['IOPS-write']=self.get_worker_value(r_url=url_write)+'kb/s'
        if resource == 'all' or resource == 'net':
            resource_info['NET-recive']=self.get_worker_value(r_url=url_recive)+'kb/s'
            resource_info['NET-transmit']=self.get_worker_value(r_url=url_transmit)+'kb/s'        
        return resource_info


    def get_all_worker_ip(self):
        """
        @description : get a list shows all workers and is divided arch and x86
        ------------
        @param : NA
        -----------
        @returns : 
            obs_worker_list : a list shows all workers and is divided arch and x86
        """
        obs_worker_list = [{"aarch64":[]},{"x86":[]}]
        server = ECSServers()
        server_list = server.list()
        for i in range(0, len(server_list['servers'])):
            if server_list['servers'][i]['arch'] == 'aarch64':
                obs_worker_list[0]["aarch64"].append(server_list['servers'][i]['ip'])
            else:
                obs_worker_list[1]["x86"].append(server_list['servers'][i]['ip'])
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
            server = ECSServers()
            server_ip = server.get(ip)
    
            """
            find ip and status from the server_ip
            """
            machine_status={'ip':server_ip['server']['ip'],'status':server_ip['server']['status']}
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
        service_state["ip"]=ip
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=ip,
                username='root',
                password=passwd,
                timeout=5
                )
            stdin,stdout,stderr = client.exec_command('systemctl status obsworker')
        except BaseException as e:
            log_check.error(f"Not connect this ip,please check password or ip,due to {e}")
            return None
        str_obs = stdout.read().decode('utf-8')

        try:
            str_obs = str_obs.split("Active: ")
            str_obs = str_obs[1].split(" ")
            str_obs = str_obs[0]
        except BaseException as e:
            log_check.error(f"Not find obsservice,due to {e}")
            return None
        if str_obs == "active":
            service_state["service_OK"] = "0"
        else:
            service_state["service_OK"] = "1"
        client.close()
        return service_state

