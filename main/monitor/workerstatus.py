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
import ast
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
from main.common.Constant import WORKER_INFO_PATH
from main.common.Constant import INSTANCE_STATISTICS_PATH
from main.common.Constant import EMPTY_CMD_LIST
from main.common.Constant import ENCRYPTED_DATA_PATH
from main.common.Constant import DECRYPTION_KEY
from main.common.Constant import OBS_USER_ID
from main.common.Constant import OBS_USER_PASS
from main.common.Constant import  OBS_FRONT

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
        servers_dict = ecs_server.list_servers()
        if servers_dict["code"] == 200:
            server_list = servers_dict["servers"]
            for single_machine in server_list:
                ip_key = single_machine["ip"]
                self.server_dict[ip_key] = single_machine

    def ipaddr_to_worker_feature(self, ipaddr, feature):
        """
        @description : translate an ip address to a worker's specified feature
        -------------
        @param : 
            ipaddr : ip address
            feature : specified feature
        -------------
        @returns : 
            ret_feature 

        """
        if ipaddr in self.server_dict.keys():
            info_dict = self.server_dict[ipaddr]
        else:
            info_dict = ecs_server.get_server(ipaddr)
        if "error" in info_dict.keys():
            log_check.error(f'invalid ip address')
            ret_feature = None
        else:
            if feature == 'name':
                ret_feature = info_dict["name"]
            elif feature == 'vcpus':
                ret_feature = info_dict["flavor"]["vcpus"]
            else:
                ret_feature = None
        return ret_feature

    def generate_all_worker_info_file(self):
        """
        @description : generate all worker information file
        --------------
        @param : NA
        --------------
        @returns : 
           BOOL : True or False 
        """
        #check temporary file directory's existion
        if not os.path.exists(os.path.dirname(WORKER_INFO_PATH)):
            os.makedirs(os.path.dirname(WORKER_INFO_PATH))
        #gengerate worker information file
        cmd = f'curl -s --user {OBS_USER_ID}:{OBS_USER_PASS} -X GET {OBS_FRONT} -o {WORKER_INFO_PATH}'
        result = ExecuteCmd.cmd_status(cmd.split())
        if result != 0:
            log_check.error(f'generate {WORKER_INFO_PATH} failed!')
            return False
        cmd = 'sed -i /arch="riscv64"/d ' + WORKER_INFO_PATH
        result = ExecuteCmd.cmd_status(cmd.split())
        cmd = 'sed -i /hostarch="riscv64"/d '+ WORKER_INFO_PATH
        result += ExecuteCmd.cmd_status(cmd.split())
        if result != 0:
            log_check.error(f'{WORKER_INFO_PATH} process failed!')
            return False
        return True
   
    def check_validation_of_workername(self, workername):
        """
        @description : check validation of worker name
        ---------------
        @param : 
            workername : obsworker name
        ---------------
        @returns : 
            BOOL : True or False
        """
        #existion of dependent file all_obs_worker_info should be ensured by invoker
        workername_str = 'workerid="' + workername + ':'
        exist = ExecuteCmd.cmd_output(['grep', '-c', workername_str, WORKER_INFO_PATH])
        if exist is None:
            return False
        return True

    def exec_cmd_list(self, cmd_list):
        """
        @description : is funcion is define to deal with series shell cmd, 
        due to ExecuteCmd class can not handle pipe command
        ---------------
        @param : 
            cmd_list : 
        ---------------
        @returns : 
            cmd_list.index(cmd) 
        """
        #check parameter's validation
        if len(cmd_list) == 0:
            return EMPTY_CMD_LIST
        cur_cmd = cmd_list[0] 
        for cmd in cmd_list:
            cur_cmd = cmd
            write_content = ExecuteCmd.cmd_output(cmd)
            if write_content:
                try:
                    with open(INSTANCE_STATISTICS_PATH, 'w') as tmp_file_handle:
                        tmp_file_handle.write(write_content)
                except FileNotFoundError as e:
                    log_check.error(f'open error due to {e}')
            else:
                cmd_str = str(cmd)
                break
        return cmd_list.index(cur_cmd)

    def worker_instance_statistics(self, workername):
        """
        @description : query a obs worker's instance situation
        --------------
        @param : 
            workername : obsworker name
        --------------
        @returns : 
           instance_situation 
        """
        instance_situation = {"ip":'0', "instance_all":0, "instance_run":0, "instance_idle":0}
        workername_validation = self.check_validation_of_workername(workername)
        if not workername_validation:
            log_check.info(f'workername:{workername} is invalid')
            return None
        #existion of dependent file all_obs_worker_info should be ensured by invoker
        total_cmd_list = [['grep', '-rn', workername + ':', WORKER_INFO_PATH], \
                    ['grep', '-E', '<building|<idle', INSTANCE_STATISTICS_PATH], \
                    ['awk', "{print $3}", INSTANCE_STATISTICS_PATH], \
                    ['awk', '-F=', '{print $2}', INSTANCE_STATISTICS_PATH], \
                    ['sed', 's/"//g', INSTANCE_STATISTICS_PATH], \
                    ['awk', '-F:', '{print $2}', INSTANCE_STATISTICS_PATH], \
                    ['sort', '-u', INSTANCE_STATISTICS_PATH]]
        total_accompany_tips_list = ['workername:' + workername + ' dose not exist in file ' + WORKER_INFO_PATH, \
                     'worker:' + workername + ' does not exist building or idle instance']
        total_accompany_tips_list.extend(total_cmd_list[2:])
        complete_num = self.exec_cmd_list(total_cmd_list)
        if complete_num == EMPTY_CMD_LIST:
            log_check.error(f'command line empty')
            return None
        if complete_num != len(total_cmd_list) - 1:
            log_check.error(total_accompany_tips_list[complete_num])
            return None
        cmd = 'tail -1 ' + INSTANCE_STATISTICS_PATH
        total_instance_str = ExecuteCmd.cmd_output(cmd.split())
        try:
            if total_instance_str.strip() == '':
                log_check.info(f'{workername} is down, has no instance')
                return None
        except AttributeError as e:
            log_check.error(f'strip error due to {e}')
        total_instance = int(total_instance_str)
        run_cmd_list = [['grep', '-rn', workername + ':', WORKER_INFO_PATH], \
                        ['grep', '-E', '<building', INSTANCE_STATISTICS_PATH], \
                        ['awk', "{print $3}", INSTANCE_STATISTICS_PATH], \
                        ['awk', '-F=', '{print $2}', INSTANCE_STATISTICS_PATH], \
                        ['sort', '-u', INSTANCE_STATISTICS_PATH]]
        run_accompany_tips_list = ['workername:' + workername + ' does not exist in file:' + WORKER_INFO_PATH, \
                         'worker:' + workername + ' does not exist running instance']
        run_accompany_tips_list.extend(run_cmd_list[2:])
        complete_num = self.exec_cmd_list(run_cmd_list)
        if complete_num == EMPTY_CMD_LIST:
            log_check.error(f'command line empty')
            return None
        if complete_num == 1:
            log_check.info(run_accompany_tips_list[complete_num])
            running_instance = 0
        elif complete_num == len(run_cmd_list) - 1:
            try:
                with open(INSTANCE_STATISTICS_PATH, 'r') as running_file_handle:
                    running_instance = len(running_file_handle.readlines())
            except FileNotFoundError as e:
                log_check.error(f'open error due to {e}')
        else:
            log_check.error(run_accompany_tips_list[complete_num])
            return None
        instance_situation["instance_all"] = total_instance
        instance_situation["instance_run"] = running_instance
        instance_situation["instance_idle"] = total_instance - running_instance
        return instance_situation

    def get_worker_instance(self, iplist):
        """
        @description : get instance's situation in specified worker
        --------------
        @param : 
            iplist :
        --------------
        @returns :
            worker_instance_state : 
        """
        worker_instance_state = []
        result = self.generate_all_worker_info_file()
        if not result:
            return worker_instance_state
        for ipaddr in iplist:
            workername = self.ipaddr_to_worker_feature(ipaddr, 'name')
            if workername is None:
                log_check.error(f'get worker name from ip:[ipaddr] failed,this ip does not correspond to a worker name')
                continue
            one_worker = self.worker_instance_statistics(workername)
            if one_worker is None:
                #log is recorded by worker_instance_statistics
                continue
            one_worker["ip"] = ipaddr
            worker_instance_state.append(one_worker)
        return worker_instance_state


    def ipaddr_to_level(self, ipaddr):
        """
        @description : get specified worker's level ,worker specifid by ip address
        --------------
        @param : 
            ipaddr : ip address
        --------------
        @returns : 
            level : different dict_cpu level 
        """
        cpus = self.ipaddr_to_worker_feature(ipaddr, 'vcpus')
        dict_cpu = {'16':'l1','32':'l2','64':'l3','128':'l3'}
        level = dict_cpu.get(cpus)
        if level == None:
            log_check.error(f'got invalid vcpus: {cpus} from ip: {ipaddr}')
        return level
    
    def _convert_instance_list(self, idle_list, arch, instance_list):
        """
        @description : get instance_list by idle_list and arch
        --------------
        @param : 
            idle_list : idle ip list
            arch : x86 or aarch64
            instance_list : {"aarch64":{},"x86":{}}
        --------------
        @returns :
            instance_list
        """
        if len(idle_list[arch]) != 0:
            for armip in idle_list[arch]:
                level = self.ipaddr_to_level(armip)
                instance_list[arch][level] += 1
        
    def query_idle_instance(self, iplist):
        """
        @description : statistic obs worker's level amount, worker specified by ip address list
        --------------
        @param :
            iplist : ip address list
        --------------
        @returns : 
           instance_list : aarch64 or x86 instance list 
        """
        instance_list = {"aarch64":{"l1":0, "l2":0, "l3":0}, "x86":{"l1":0, "l2":0, "l3":0}}
        result = self.generate_all_worker_info_file()
        if not result:
            return instance_list
        idle_list = self.query_idle_worker_ip(iplist)
        self._convert_instance_list(idle_list, "aarch64", instance_list)
        self._convert_instance_list(idle_list, "x86", instance_list)

        return instance_list


    def ipaddr_idle(self, ipaddr):
        """
        @description : judge whether a obs worker is in state idle, worker is specified by ip address
        --------------
        @param : 
            ipaddr : ip address
        --------------
        @returns : 
           BOOL : True or False 
        """
        workername = self.ipaddr_to_worker_feature(ipaddr, 'name')
        if workername is None:
            return False
        status_dict = self.worker_instance_statistics(workername)
        if status_dict is None:
            return False
        if (status_dict["instance_run"] == 0) and (status_dict["instance_all"] != 0):
            return True
        else:
            return False

    def query_idle_worker_ip(self, iplist):
        """
        @description : pick idle worker's ip form ip address list
        --------------
        @param : 
            iplist : x86 or aarch64 list
        --------------
        @returns : 
            idle_worker_list : idle obsworker list
        """
        idle_worker_list = {"aarch64":[], "x86":[]}
        arm_ip_list = iplist["aarch64"]
        x86_ip_list = iplist["x86"]
        for armip in arm_ip_list:
            idle = self.ipaddr_idle(armip)
            if idle:
                idle_worker_list["aarch64"].append(armip)
        for x86ip in x86_ip_list:
            idle = self.ipaddr_idle(x86ip)
            if idle:
                idle_worker_list["x86"].append(x86ip)
        return idle_worker_list
        
    def get_monitor_resource(self,resource,ip,times):
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
        decryption_str = self.get_decrypt_password()
        worker_login = ast.literal_eval(decryption_str)
        username = worker_login['monitor_server']['user']
        password = worker_login['monitor_server']['pass']
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

    def create_ssh_connector(self, hostip, hostpass):
        """
        @description : Create a ssh connector
        -----------
        @param :
            hostip: ip address
            hostpass: password for hostip
        -----------
        @returns :
        -----------
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname = hostip,
                username = 'root',
                password = hostpass,
                timeout = 5
                )
        except socket.timeout as e:
            log_check.error(f"Not connect this ip,please check password or ip,due to {e}")
            client.close()
            return None

        return client
        

    def check_service(self, ip, passwd):
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
        client = self.create_ssh_connector(ip, passwd)
        try:
            stdin,stdout,stderr = client.exec_command('systemctl status obsworker')
        except AttributeError as e:
            log_check.error(e)
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
        """
        @description : get obsworker config jobs instances and repo servers
        --------------
        @param : 
            str_worker_value : obsworker value from cmd
            config_value_cut : cut the str by this 
        --------------
        @returns :
            str_value 
        """
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
        client = self.create_ssh_connector(ip, passwd)
        try:
            #get the values of jobs and instances from obs-server
            stdin,stdout,stderr = client.exec_command("cat /etc/sysconfig/obs-server")
        except AttributeError as e:
            log_check.error(e)
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
            except (KeyError, AttributeError) as e:
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

    def get_decrypt_password(self):
        """
        @description : get decrypt password
        --------------
        @param : NA
        --------------
        @returns :
            decryptor.decrypt_file.split('\n')
        """
        decryptor = AESEncryAndDecry(DECRYPTION_KEY, ENCRYPTED_DATA_PATH, None)
        return decryptor.decrypt_file

    def valid_workername_filter(self, workernamelist, sshclient):
        """
        @description : select valid workername, compose a valid workname list
        ---------------
        @param :
            workernamelist     
            sshclient 
        ---------------
        @returns : 
           validnamelist :  
        """
        validnamelist = []
        for workername in workernamelist:
            try:
                stdin, stdout, stderr = sshclient.exec_command('ls /srv/obs/workers/building | grep -c "' + workername + ':"')
                building_instance = stdout.read().decode('utf-8')
                stdin, stdout, stderr = sshclient.exec_command('ls /srv/obs/workers/idle | grep -c "' + workername + ':"')
                idle_instance = stdout.read().decode('utf-8')
                if int(building_instance) + int(idle_instance) == 0:
                    validnamelist.append(workername)
                else:
                    log_check.error(f'{workername} has building or idle instance!')
            except BaseException as e:
                log_check.error(f'query {workername} building, idle instance failed! due to {e}')
        return validnamelist

    def delete_down_obsworker(self, workernamelist):
        """
        @description : delete obsworker form monitor 
        --------------
        @param :
            workernamelist : obsworkername list 
        --------------
        @return: bool dictionary express corresponding workername's result
        """
        result_dict = {}
        #establish connection to server
        decryption_str = self.get_decrypt_password()
        hostinfo = ast.literal_eval(decryption_str)
        client = self.create_ssh_connector(hostinfo['main_backend']['ip'], hostinfo['main_backend']['pass'])

        #check validation of workername
        valid_workername_list = self.valid_workername_filter(workernamelist, client)
        #delete worker in status down
        for workername in workernamelist:
            try:
                stdin, stdout, stderr = client.exec_command('ls /srv/obs/workers/down | grep -c "' + workername + ':"')
                down_instance = stdout.read().decode('utf-8')
                if int(down_instance) == 0:
                    log_check.error(f'{workername} has no instance!')
                    result_dict[workername] = False
                    continue
                stdin, stdout, stderr = client.exec_command('rm -rf /srv/obs/workers/down/*' + workername + ':*')
            except BaseException as e:
                log_check.error(f'delete down worker:{workername} failed! due to {e}')
                result_dict[workername] = False
                continue
            result_dict[workername] = True
        client.close()
        return result_dict
