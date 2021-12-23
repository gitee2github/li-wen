#！/usr/bin/env/python
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
# Create: 2021-11-25
# ******************************************************************************/
"""
This is main entrance
"""
import sys
# sys.path.append('/usr/li-wen')
import csv
import copy
import codecs
import configparser
from logging import log
import time
from libs.conf import global_config
from libs.cloud.HWCloud.ecs_servers import ecs_server
from main.core.auto_extend import AutoExtendWorker
from main.monitor.workerstatus import QueryOBSWorker
from main.monitor.project import QueryProject
from libs.conf.queryconfig import query_config
from libs.log.logger import log_check
from main.common.Constant import MULTI_ARCH
from main.common.Constant import MULTI_LEVELS

interval_for_check_schedule = int(query_config.get_value("Monitor", "interval_for_check_schedule"))
interval_for_cycle_check_new_worker = int(query_config.get_value("Monitor", "interval_for_cycle_check_new_worker"))
num_for_check_reserved_worker = int(query_config.get_value("Monitor", "num_for_check_reserved_worker"))
interval_for_check_reserved_worker = int(query_config.get_value("Monitor", "interval_for_check_reserved_worker"))
# 获取当前关联的project列表
projects = query_config.get_value("Monitor", "projects").split()
# 获取project所属的backend
repo_server = query_config.get_value("Monitor", "repo_server")

obs_worker = QueryOBSWorker()
project = QueryProject()
auto_extend_worker = AutoExtendWorker()

def sum_schedule(schedule_events):
    """
    @description : 计算schedule任务总数
    -----------
    @param :
        schedule_events: schedule状态任务统计列表
        {
            "aarch64":{"l1":0, "l2":0, "l3":0}, 
            "x86":{"l1":0, "l2":0, "l3":0}
        }
    -----------
    @returns :
        sum_schedule_events：schedule任务总数
    -----------
    """
    sum_schedule_events = 0

    for arch in MULTI_ARCH:
        multi_level_events = schedule_events.get(arch)
        for level_idx  in range(MULTI_LEVELS):
            level = 'l' + str(level_idx + 1)
            sum_schedule_events += multi_level_events.get(level)
            
    return sum_schedule_events

# 校验workers指向的worker的可用状态
def check_worker_enable(workers, passwd, interval, checK_start):
    """
    @description : 校验workers指向的worker的可用状态
    -----------
    @param :
        workers: worker信息列表，每一个元素是一个字典
        passwd：worker的登录密码
        interval：校验的等待时间间隔
        checK_start：校验开始时间
    -----------
    @returns : NA
    -----------
    """

    flag = "Timeout, end verification."
    check_end = time.monotonic()
    abnormal_workers = workers[:]
    
    # {"ip", "arch", "level", "vcpus", "ram", "jobs", "instances"}
    while (check_end - checK_start) < interval_for_check_schedule:
        if not workers:
            flag = "All of the workers are normal."
            break
        for worker in workers:
            wait_for_check_config = dict()
            ip = worker.get("ip")
            wait_for_check_config["vcpus"] = worker.get("vcpus")
            wait_for_check_config["ram"] = worker.get("ram")
            wait_for_check_config["jobs"] = worker.get("jobs")
            wait_for_check_config["instances"] = worker.get("instances")
            wait_for_check_config["repo_server"] = repo_server

            service_status = obs_worker.check_service(ip, passwd) # 校验worker核心服务的状态
            config_same = obs_worker.check_worker_config(ip, passwd, wait_for_check_config)

            if service_status and config_same:
                abnormal_workers.remove(worker) # 校验OK的包从列表中去掉
        
        workers = abnormal_workers[:]
        log_check.info(f"After {interval}s, we go on next checking workers' service and configuration......")
        time.sleep(interval)
        check_end = time.monotonic()
    log_check.info(flag)
        
    return abnormal_workers
    
    
def save_workers_info(workers, save_type, save_path, save_mode):
    """
    @description : 保存worker信息到日志文件同级目录
    -----------
    @param :
        workers：worker信息列表
        save_type: 信息类型，决定最终保存为csv的第一行属性名
        save_path：保存文件路径
        save_mode：写模式，w/a+
    -----------
    @returns : NA
    -----------
    """
    if workers is None:
        log_check.error(f"workers is empty and no related info will be save!")
        return False

    with codecs.open(save_path, save_mode, 'utf-8') as result_file:
        writer = csv.writer(result_file)
        if save_type == "new":
            writer.writerow(["ip", "name", "arch", "level", "create_time"])
        else:
            writer.writerow(["ip", "name", "arch", "vcpus", "create_time"])

        for worker in workers:
            try:
                if save_type == "new":
                    data = [worker.get("ip"), worker.get("name"), worker.get("arch"), \
                        worker.get("level")]
                else:
                    data = [worker.get("ip"), worker.get("name"), worker.get("arch"), \
                        worker.get("flavor").get("vcpus")]
                data.append(time.asctime( time.localtime(time.time())))
            except AttributeError as err:
                log_check.error(f"Abnormal data from: {workers}, error meaasge: {err}")
                return False
            writer.writerow(data)

    return True

def main_progrecess():
    """
    主函数入口
    """
    test_num = 0

    while True:
        test_num += 1
        log_check.debug(f"======================WSDM Start : {test_num}======================")
        # 开始计时
        start = time.monotonic()

        # 获取ECSServers().list返回的所欲worker 信息列表
        HWCloud_workers = ecs_server.list_servers().get('servers')
        if not save_workers_info(HWCloud_workers, "cur", global_config.CURRENT_WORKERS_INFO, 'w'):
            log_check.warning("Save data from ecs_server.list_servers() failed, terminate!")

        # 获取当前生产环境的所有worker ip列表
        obs_workers_ip = obs_worker.get_all_worker_list()

        # 获取 project中schedule状态的不同构建时长级别的统计结果
        schedule_events_list = project.query_schedule_statistics(projects)
        log_check.info(f"Get realtime schedule events: {schedule_events_list}")

        sum_schedule_enents = sum_schedule(schedule_events_list)
        if sum_schedule_enents != 0:
            log_check.info(f"++++++++++++++We have schedule events, then cacluate workers to apply!++++++++++++")

            # 获取当前生产环境中的worker中处于idle状态的instance數量统计结果
            idle_instances_list = obs_worker.query_idle_instance(obs_workers_ip)
            log_check.info(f"Get realtime idle instances: {idle_instances_list}")

            # 获取worker默认的登录密码
            passwd = auto_extend_worker.passwd

            # 评估并创建worker
            apply_worker = auto_extend_worker.evaluate_new_workers(schedule_events_list, idle_instances_list, passwd)
            save_workers_info(apply_worker, "new", global_config.REALTIME_CREATED_WORKERS_INFO, 'a+')
            log_check.debug(f"Successfully create these workers:{apply_worker} , then check their status:")

            if (time.monotonic() - start) >= interval_for_check_schedule:
                log_check.warning("Timeout, terminate the verification of the newly created worker status!")
                continue
            
            # 校验新申请的worker的可用状态,abnormal_worker表示校验后异常或者不满足规格要求的worker
            abnormal_workers = check_worker_enable(apply_worker, passwd, interval_for_cycle_check_new_worker, start)

            if (time.monotonic() - start) >= interval_for_check_schedule:
                log_check.warning("Timeout, terminate the delete of the newly created but abnormal workers!")
                continue

            # 释放未达到可用状态的worker并清理后台相关信息
            log_check.debug(f"Abnormal workers:{abnormal_workers} , then delete them:")
            auto_extend_worker.delete_workers(abnormal_workers)

            time_consume = time.monotonic() - start
            if time_consume < interval_for_check_schedule:
                log_check.info(f"After {interval_for_check_schedule - time_consume}s, we go on next WSDM......")
                time.sleep(interval_for_check_schedule - time_consume)
        else:
            log_check.info(f"-------------No schedule events, let me see see which workers were idle!-------------")
            # 查询当前生产环境的所有worker信息
            result = obs_worker.generate_all_worker_info_file()
            if not result:
                log_check.error(f"No worker info file, stop release!")
                continue
            log_check.info("Initial all_obs_worker_info.log succeeded!")
            
            # 初步筛选处于idle状态的worker ip列表
            idle_workers = obs_worker.query_idle_worker_ip(obs_workers_ip)
            log_check.info(f"Idle workers: {idle_workers}")

            # 评估长时间处于idle状态的worker，释放并清理
            result_release = auto_extend_worker.evaluate_idle_workers(idle_workers, \
                num_for_check_reserved_worker, interval_for_check_reserved_worker)
            
            log_check.info(f"-------------Idle workers {result_release}!-------------")

if __name__ == '__main__':
    main_progrecess()
