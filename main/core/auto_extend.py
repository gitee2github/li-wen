#! /usr/bin/env python
# coding=utf-8
# ******************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2020-2020. All rights reserved.
# licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# Author: senlin
# Create: 2021-06-20
# ******************************************************************************/

import ast
import configparser
import math
import os
import re

import time
from libs.cloud.HWCloud.ecs_servers import ECSServers
from libs.log.logger import log_check
from libs.conf.queryconfig import query_config
from main.common.aes_decode import AESEncryAndDecry
from main.common.wsdm_thread import WsdmThread
from main.monitor.workerstatus import QueryOBSWorker

class AutoExtendWorker(object):
    """
    This is a class for dynamically extending OBS worker machine resources 
    """
    def __init__(self):
        self.server = ECSServers()
        self.worker_query = QueryOBSWorker()
        self.worker_conf = ["L1_Worker_Conf", "L2_Worker_Conf", "L3_Worker_Conf"]
        
    def calcuate_and_create_worker(self, schedule_events_list, idle_instances_list, passwd):
        """
        @description : 计算各个规格的worker申请数目并调用华为云的创建接口
        -----------
        @param :
            schedule_events_list:并发构建任务统计列表，例如：
                schedule_events_list = [
                    {"aarch64":{"l1":0, "l2":12, "l3":0}},
                    {"x86":{"l1":0, "l2":0, "l3":0}}
                ]
            idle_instances_list:空闲instance统计列表，例如：
                idle_instances_list = [
                    {"aarch64":{"l1":0, "l2":0, "l3":0}},
                    {"x86":{"l1":0, "l2":0, "l3":0}}
                ]
            passwd: 创建worker的初始登录密码
        -----------
        @returns :
            new_workers_info: 创建好的worker详细信息（部分字段为申请时的初始值，为了后面的校验做对比）
        -----------
        """
        start_time = time.time()
        new_workers_info = []
        thread_arch_level = []
        multi_arch = ["aarch64", "x86"]
        for idx in range(2):
            arch = multi_arch[idx]
            for level_idx in range(3):
                level = 'l' + str(level_idx + 1)
                try:
                    schedule = (schedule_events_list[idx].get(arch)).get(level)
                    idle = (idle_instances_list[idx].get(arch)).get(level)
                except (AttributeError, KeyError) as err:
                    log_check.error(f"reason: {err}")
                    continue
                except (configparser.NoOptionError, configparser.NoSectionError) as err:
                    log_check.error(f"reason: {err.message}")
                    continue

                default_instances = query_config(self.worker_conf[level_idx], "instances")
                max_limit = query_config(self.worker_conf[level_idx], "max_limit")

                # 计算得到预申请的数目
                if schedule <= idle: 
                    continue
                worker_num = math.ceil((schedule - idle) / int(default_instances)) # 向上取整
                if worker_num > max_limit:
                    log_check.warning(f"Expected number of workers has exceeded the limit: {worker_num} > {max_limit}")
                    worker_num = max_limit

                log_check.info(f"Start thread for applying {arch}-{level} workers num: ({schedule}-{idle}) / {default_instances} = {worker_num}")
                # 创建多线程，调用创建worker的接口
                thread_name = arch + '_' + level
                thread_func_args = [arch, level_idx, passwd, worker_num]
                thread = WsdmThread(thread_name, self.create_workers, thread_func_args, new_workers_info)
                thread.start()
                thread_arch_level.append(thread)
        for thread in thread_arch_level:
            thread.join()
        
        # 回到主线程
        log_check.info(f"end_time: {time.time() - start_time}")
        return new_workers_info

    def evaluate_new_workers(self, schedule_events_list, idle_instances_list, passwd):
        """
        @description : 评估申请worker
        -----------
        @param :
            schedule_events_list:并发构建任务统计列表
            idle_instances_list:空闲instance统计列表
            passwd: 创建worker的初始登录密码
        -----------
        @returns :创建好的worker详细信息（部分字段为申请时的初始值，为了后面的校验做对比）
        -----------
        """
        if len(schedule_events_list) != 2 or len(idle_instances_list) != 2:
            log_check.error(f"incomplete input data, please check! ")
            return None
        return self.calcuate_and_create_worker(schedule_events_list, idle_instances_list, passwd)

    def evaluate_workers_to_release(self, idle_workers, arch, num_check, interval):
        """
        @description :评估并释放空闲worker
        -----------
        @param :
            idle_workers：处于空闲状态的worker
            arch：架构
            num_check:校验worker的次数
            interval：校验等待的时间间隔
        -----------
        @returns :NA
        -----------
        """
        release_worker_ip = idle_workers
        hostnames = []
        count = 0

        while release_worker_ip and count < num_check:

            # 获取worker的instance信息
            workers_instance_state = self.worker_query.get_worker_instance(release_worker_ip)
            if workers_instance_state is None:
                log_check.error(f"No worker instance info, stop release!")
                continue
            for worker_instance in workers_instance_state:
                try:
                    ip = worker_instance.get("ip")
                except (AttributeError, KeyError) as err:
                    log_check.error(f"reason: {err}")
                    continue
                except (configparser.NoOptionError, configparser.NoSectionError) as err:
                    log_check.error(f"reason: {err.message}")
                    continue
                hostname = self.server.get_hostname(ip)
                instance_run = worker_instance.get("instance_run")
                if instance_run > 0:
                    log_check.warning(f"No release {ip}, {hostname}: it has running instances")
                    release_worker_ip.remove(ip)
                else:
                    log_check.warning(f"Release {ip}, {hostname}: it has no running instances")
            log_check.info(f"After {interval}s, we go on checking idle workers......")
            time.sleep(interval)
            count += 1

        # 释放worker
        if release_worker_ip:
            hostnames = [self.server.get_hostname(ip) for ip in release_worker_ip]
            log_check.info(f"These {arch} workers will be released: {release_worker_ip}")
            log_check.info(f"These {arch} workers will be released: {hostnames}")
            self.delete_workers(release_worker_ip)
        else:
            log_check.info(f"No workers will be released")
        
    # 创建worker
    def create_workers(self, arch, level_idx, passwd, num=1):
        """
        @description :创建对应架构、规格和数目的worker
        -----------
        @param :
            arch：结构
            level_idx：规格等级
            passwd：新worker的初始登录密码，账号默认为root
            num：数目，不传则默认为1
        -----------
        @returns :
            apply_worker:新worker的详细信息
        -----------
        """
        apply_worker = []
        default_instances = query_config(self.worker_conf[level_idx], "instances")
        vcpus = query_config(self.worker_conf[level_idx], "vcpus")
        ram = query_config(self.worker_conf[level_idx], "ram")
        jobs = query_config(self.worker_conf[level_idx], "jobs")
        level = 'l' + str(level_idx + 1)
        log_check.info(f"Apply new workers: arch: {arch}, flavor: {level}, number: {num}")
        result = self.server.create(arch, level, passwd, num)

        try:
            return_code = int(result.get("code"))
            if return_code != 200:
                return_error = result.get("error")
                log_check.error(f"ECSServers().create return: {return_error}")
                return apply_worker
            new_workers_ip = result.get("server_ips")
        except (AttributeError, KeyError) as err:
            log_check.error(f"reason: {err}")
            return apply_worker
        except (configparser.NoOptionError, configparser.NoSectionError) as err:
            log_check.error(f"reason: {err.message}")
            return apply_worker

        # 回到主进程：记录预申请的worker的关键属性
        for ip in new_workers_ip:
            new_worker = dict()
            new_worker["ip"] = ip
            new_worker["name"] = self.server.get_hostname(ip)
            new_worker["arch"] = arch
            new_worker["level"] = level
            new_worker["vcpus"] = vcpus
            new_worker["ram"] = ram
            new_worker["jobs"] = jobs
            new_worker["instances"] = default_instances
            new_worker["running_status"] = "BUILDING"
            new_worker["service_status"] = "NA"
            new_worker["check_time"] = time.clock()
            apply_worker.append(new_worker)
        return apply_worker

    def delete_workers(self, release_workers):
        """
        @description : 释放worker并清理后台残留信息
        -----------
        @param :
            release_workers：待释放的worker ip列表
        -----------
        @returns :NA
        -----------
        """
        
        delete_result = self.server.delete(release_workers)
        log_check.info(f"Call HWCloud delete：{delete_result}")

        hostanmes = []
        for worker in release_workers:
            hostanmes.append(self.worker_query.ipaddr_to_worker_feature(worker, 'name'))
        
        clean_result = self.worker_query.delete_down_obsworker(hostanmes)
        log_check.info(f"Call clean up：{clean_result}")

    @property
    def get_passwd(self):
        """
        @description :获取worker的初始登录密码
        -----------
        @param :NA
        -----------
        @returns :
            passwd: 密码
        -----------
        """
        passwd = "**********"
        key = query_config("AES_Decry_Conf", "key")
        decryption_file = query_config("AES_Decry_Conf", "worker_login")

        if not os.path.isfile(decryption_file):
            log_check.error("NO decrption file")
            return passwd
        
        aes = AESEncryAndDecry(key, decryption_file)
        decryption_str = aes.decrypt_file
        user_dict = ast.literal_eval(decryption_str)
        passwd = user_dict.get("passwd")
        return passwd

    @property
    def get_excluded_workers(self):
        """
        @description : 获取不在评估是否释放范围内的worker
        -----------
        @param :
        -----------
        @returns :
        -----------
        """
        excluded_workers = []
        key = query_config("AES_Decry_Conf", "key")
        decryption_file = query_config("AES_Decry_Conf", "worker_excluded")

        if not os.path.isfile(decryption_file):
            log_check.error("NO decrption file")
            return excluded_workers
        
        aes = AESEncryAndDecry(key, decryption_file)
        decryption_str = aes.decrypt_file
        excluded_workers = decryption_str.split('\n')
        return excluded_workers
        
