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
import os
import configparser
import linecache
import time
import subprocess
import sqlite3
from libs.log.logger import log_check
from main.common.executecmd import ExecuteCmd

from main.common.Constant import HISTORY_LOG_PATH 
from main.common.Constant import PROJ_STATUS_RES_PATH
from main.common.Constant import ARCH_STATUS_RES_PATH
from main.common.Constant import X86_TMP_STATUS_PATH
from main.common.Constant import DATABASE_PATH

from main.common.Constant import BUILD_TIME_ITEM_LEN
from main.common.Constant import BUILD_TIME_END_INDEX
from main.common.Constant import BUILD_TIME_END_POS
from main.common.Constant import BUILD_TIME_START_INDEX
from main.common.Constant import BUILD_TIME_START_POS
from main.common.Constant import PACKAGE_STATUS_ITEM
from main.common.Constant import PACKAGE_STATUS_START_POS
from main.common.Constant import MULTI_LEVELS

from main.common.Constant import GETBUILDTIME_CHECK_SHELL
from main.common.Constant import PROJECTSTATUS_CHECK_SHELL
from main.common.Constant import LEVELSTATISTIC_CHECK_SHELL


class QueryProject(object):
    """
    query project information such as:
    1. building time of one package
    2. package amount in specified status
    3. package level distribution in specified status
    """
    def __init__(self):
        """
        @description : init function
        -----------
        @param : NA
        -----------
        @return : NA
        -----------
        """
        self.dbcon = sqlite3.connect(DATABASE_PATH)
        self.cursor = self.dbcon.cursor()

    def __del__(self):
        """
        @descirption : destruction function
        -----------
        @param : NA
        -----------
        @return : NA
        -----------
        """
        self.cursor.close()
        self.dbcon.close()

    @staticmethod
    def _get_parent_path():
        """
        @description : get check shell parent path
        -----------
        @param : NA
        -----------
        @returns : None if failed, or return shell' parent path
        -----------
        """
        currpath = os.path.dirname(os.path.realpath(__file__))
        path_list = currpath.split('/')
        if not 'li-wen' in path_list:
            return None
        proj_index = path_list.index('li-wen')
        parentpath = '/'
        for index in range(1, proj_index + 1):
            parentpath = os.path.join(parentpath, path_list[index])
        parentpath = os.path.join(parentpath, 'libs', 'api')
        return parentpath

    def _check_shell(self, shellname):
        """
        @description : check existion of shell
        -----------
        @param : shell name
        -----------
        @returns : False if shell does not exist
        -----------
        """
        parentpath = self._get_parent_path()
        if parentpath is None:
            return False
        currfile = os.path.join(parentpath, shellname)
        return os.path.exists(currfile)

    def _check_param(self, shellname, paramstring):
        """
        @description : check paramter's validity
        -----------
        @param : 
            shellname: shell name which is used to check paramters
            paramstring: parameters to be checked
        -----------
        @returns: False if parameters are invalid
        -----------
        """
        path = self._get_parent_path()
        cmd = path + '/' + shellname + ' ' + paramstring
        valid = ExecuteCmd.cmd_output(cmd.split())
        if valid is None:
            log_check.error(f'implement parameter check cmd failed!')
            return False
        elif 'Usage:' in valid:
            log_check.error(f'invalid parameter! effective parameters as follows: \n {valid}')
            return False
        else:
            return True

    @staticmethod
    def check_existion_of_osc():
        """
        @description : check existion of package osc
        -----------
        @param : NA
        -----------
        @return : False if osc does not installed in running machine
        -----------
        """
        cmd = 'osc --version'
        try:
            query_result = ExecuteCmd.cmd_output(cmd.split())
        except FileNotFoundError:
            log_check.error(f'packge osc dose not installed in running machine')
            return False
        return True
    
    @staticmethod    
    def _check_status(status):
        """
        @description : check validation of stauts
        -----------
        @param : 
            status :
        -----------
        @returns : False if status is invalid
        -----------
        """
        if not status in ['scheduled', 'dispatch', 'building', \
                          'signing', 'finished', 'succeeded', 'failed', \
                          'unresolvable', 'blocked', 'excluded']:
            log_check.error(f'invalid status')
            return False
        return True

    @staticmethod
    def _repo_to_arch(repo):
        """
        @description : transform repository to architecture
        -----------
        @param : 
            repo : repository name
        -----------
        @returns: architecture name corresponded to specified repositoryy
        -----------
        """
        if repo == 'standard_aarch64':
            return 'aarch64'
        elif repo == 'standard_x86_64':
            return 'x86_64'
        else:
            return None

    @staticmethod
    def _get_start_and_end_time(timeinfolist):
        """
        @description : get start and end time from time infomation list
        -----------
        @param : time information list got form build time file
        -----------
        @returns : package built start and end time
        -----------
        """
        endtime = int(timeinfolist[BUILD_TIME_END_INDEX]\
                      [BUILD_TIME_END_POS:-1])
        starttime = int(timeinfolist[BUILD_TIME_START_INDEX]\
                        [BUILD_TIME_START_POS: -1])
        return endtime, starttime

    @staticmethod
    def _preprocess_build_history_file():
        """
        @description : preprocess build history file
        ----------
        @param : NA
        ----------
        @returns : Non zero if failed
        ----------
        """
        #delete failed item
        cmd = 'sed -i ' + '/failed/d' + ' ' + HISTORY_LOG_PATH
        result = ExecuteCmd.cmd_status(cmd.split())
        #delete invalid item
        cmd = 'sed -i ' + '/jobhistlist/d' + ' ' + HISTORY_LOG_PATH
        result += ExecuteCmd.cmd_status(cmd.split()) 
        cmd_list = ['sed', '-i', '/SSL certificate checks disable/d', \
                    HISTORY_LOG_PATH]
        result += ExecuteCmd.cmd_status(cmd_list)
        cmd = 'sed -i ' + '1d' + ' ' + HISTORY_LOG_PATH
        result += ExecuteCmd.cmd_status(cmd.split())
        return result

    def _gen_duration_list(self, project, repo, package, boundary):
        """
        @description : generate package build duration list
        -----------
        @param :
            project: project name
            arch:    architecture name
            package: package name
            boundary:history build times
        -----------
        @returns : empty list if failed, or return history build time list
        -----------
        """
        duration_list = []
        query_item = int(boundary)
        #translate repository to architecture
        arch = self._repo_to_arch(repo)
        if arch is None:
            log_check.error(f'{repo} is not a valid repository value')
            #empty list is a reasonable return value
            return duration_list

        #get packge job history save it to history.log
        cmd = 'osc api -X GET /build/' + project + '/' + repo + '/' + \
               arch + '/_jobhistory?package=' + package
        history_content = ExecuteCmd.cmd_output(cmd.split())
        if history_content is None:
            log_check.error(f'generate package jobhistory file failed!')
            return duration_list
        with open(HISTORY_LOG_PATH, 'w+') as history_log_handle:
            history_log_handle.write(history_content)

        #preprocess history.log
        result = self._preprocess_build_history_file()
        if result != 0:
            log_check.error(f'preprocess build history file failed')
            return duration_list

        #get valid item num
        with open(HISTORY_LOG_PATH, 'r') as rd_handle:
            valid_boundary = len(rd_handle.readlines())
            if valid_boundary < query_item:
                query_item = valid_boundary

        #generate versrel and bcnt list
        linecache.clearcache()
        for index in range(valid_boundary, valid_boundary - query_item, -1):
            line_content = linecache.getline(HISTORY_LOG_PATH, index).strip()
            part_list = line_content.split(' ')
            list_len = len(part_list)
            if list_len == BUILD_TIME_ITEM_LEN:
                endtime, starttime = self._get_start_and_end_time(part_list)
                duration = endtime - starttime
                duration_list.append(duration)
        return duration_list

    def query_history_build_time_of_package(self, project, repo, package, boundary):
        """
        @description : query specified package's history build time
        -----------
        @param :
            project: project name
            repo:    repository name
            package: package name
            boundary:history build times
        -----------
        @return: None if failed, or return dictionary like {"average": xx, "history":[xx, xx, xx..]}
        -----------
        """
        time_dict = {"average": 0, "history":[]}
        #check installation of package osc
        if not self.check_existion_of_osc():
            return None
        #check tmp file directory
        if not os.path.exists(os.path.dirname(HISTORY_LOG_PATH)):
            os.makedirs(os.path.dirname(HISTORY_LOG_PATH))

        #check existion of getbuildtime_check_param
        shell = self._check_shell(GETBUILDTIME_CHECK_SHELL)
        if not shell:
            log_check.error(f'getbuildtime_check_param is not exist in ../../libs/api!')
            return None

        #check parameters
        param_seq = (project, repo, package, boundary)
        param_str = ' '.join(param_seq)
        valid = self._check_param(GETBUILDTIME_CHECK_SHELL, param_str)
        if not valid:
            return None

        #calc evaluation duration
        duration_list = self._gen_duration_list(project, repo, package, boundary)
        list_len = len(duration_list)
        if list_len == 0:
            log_check.error(f'{project}:{repo}:{package} generate duration list failed')
            return None
        duration_sum = sum(duration_list)
        duration_ever = duration_sum/list_len
        time_dict["average"] = duration_ever
        time_dict["history"] = duration_list
        return time_dict

    @staticmethod
    def _gen_arch_result_file(project, repo):
        """
        @description : generate obs result file for specified project and repository in order to get status
        -----------
        @param :
            project : project name
            repo :    repository name
        -----------
        @return : False if failed
        -----------
        """
        #generate result file for project
        cmd = 'osc api -X GET /build/' + project + '/_result'
        try:
            status_content = ExecuteCmd.cmd_output(cmd.split())
        except BaseException:
            log_check.error(f'execute cmd: osc api -X GET /build/../_result failed!')
            return False
        if status_content:
            with open(PROJ_STATUS_RES_PATH, 'w+') as status_file_handle:
                status_file_handle.write(status_content)
        #check existion for file result.log
        if not os.path.exists(PROJ_STATUS_RES_PATH):
            log_check.error(f'projectstatus_result.log file generation failed!')
            return False
        #get startline for each architecture in result.log
        cmd_x86 = 'sed -n -e /standard_x86_64/= ' + PROJ_STATUS_RES_PATH
        cmd_arm ='sed -n -e /standard_aarch64/= ' + PROJ_STATUS_RES_PATH
        try:
            x86start = ExecuteCmd.cmd_output(cmd_x86.split()).strip()
            armstart = ExecuteCmd.cmd_output(cmd_arm.split()).strip()
        except BaseException:
            log_check.error(f'get arm start line from build result file failed!')
            return False
        #generate specified architecture result file
        if repo == 'standard_aarch64':
            cmd = 'tail -n +' + str(int(armstart)+1) + ' ' + PROJ_STATUS_RES_PATH
            try:
                repo_status_content = ExecuteCmd.cmd_output(cmd.split())
            except BaseException:
                log_check.error(f'generate arm build status failed')
                return False
        elif repo == 'standard_x86_64':
            cmd_head = 'head -n ' + str(int(armstart)-1) + ' ' + PROJ_STATUS_RES_PATH
            cmd_tail = 'tail -n +' + str(int(x86start)+1) + ' ' + X86_TMP_STATUS_PATH
            try:
                repo_status_content = ExecuteCmd.cmd_output(cmd_head.split())
                with open(X86_TMP_STATUS_PATH, 'w+') as x86_tmp_handle:
                    x86_tmp_handle.write(repo_status_content)
                repo_status_content = ExecuteCmd.cmd_output(cmd_tail.split())
            except BaseException:
                log_check.error(f'generate x86 build status failed')
                return False
        else:
            log_check.error(f'invalid repository')
            return False
        with open(ARCH_STATUS_RES_PATH, 'w') as repo_status_handle:
            repo_status_handle.write(repo_status_content)
        if not os.path.exists(ARCH_STATUS_RES_PATH):
            log_check.error(f'projectstatus_architecture.log generation failed')
            return False
        return True

    @staticmethod
    def _get_package_list(status):
        """
        @description : get package name list in specified status
        -----------
        @param : 
            status : specified status 
        -----------
        @return : package list in specified status
        -----------
        """
        #existion of architecture.log should be ensured by invoker
        package_list = []
        #get package status file in specified status
        feature_str = '/code="' + status + '"/!d'
        execute_result = ExecuteCmd.cmd_status(['sed','-i', feature_str, ARCH_STATUS_RES_PATH])
        if execute_result != 0:
            log_check.error(f'execute cmd:sed -i /code=status/!d failed!')
            return package_list
        #check package amount
        with open(ARCH_STATUS_RES_PATH, 'r') as rd_handle:
            package_amount = len(rd_handle.readlines())
            if package_amount == 0:
                #empty list is a reasonalbe return value,that mean no package in specfied status
                return package_list
        #fill package_list
        for index in range(1, package_amount + 1, 1):
            line_content = linecache.getline(ARCH_STATUS_RES_PATH, index).strip()
            linecache.clearcache()
            line_content_split = line_content.split(' ')
            if 'package' in line_content_split[PACKAGE_STATUS_ITEM]:
                package_list.append(line_content_split[PACKAGE_STATUS_ITEM][PACKAGE_STATUS_START_POS:-1])
        return package_list

    def _query_status_num_of_project(self, project, repo, status):
        """
        @description : query specified project, get amount and package list in specified status
        -----------
        @param :
            project : project name
            repo :    repository name
            status :  specified status
        -----------
        @returns : stauts_dict["packages"][0] == 'fault' if failed
        -----------
        """
        status_dict = {"total": 0, "packages": ['fault']}
        #check tmp file directory
        if not os.path.exists(os.path.dirname(PROJ_STATUS_RES_PATH)):
            os.makedirs(os.path.dirname(PROJ_STATUS_RES_PATH))
        #check existion of projectstatus_check_param
        shell = self._check_shell(PROJECTSTATUS_CHECK_SHELL)
        if not shell:
            log_check.error(f'projectstatus_check_param is not exist in ../../libs/api!')
            return status_dict
        #check parameters
        param_seq = (project, repo, status)
        param_str = ' '.join(param_seq)
        valid = self._check_param(PROJECTSTATUS_CHECK_SHELL, param_str)
        if not valid:
            return status_dict
        #generate resutl file in specified architecture
        generate_res = self._gen_arch_result_file(project, repo)
        if not generate_res:
            return status_dict
        packages = self._get_package_list(status)
        status_dict["total"] = len(packages)
        status_dict["packages"] = packages
        return status_dict

    def gen_status_package_list(self, project, status):
        """
        @description : generate package list in specified status
        -----------
        @param :
            project : project name
            status :  specified status
        -----------
        @returns : status_packages['architecture']["packages"][0] == 'fault' if failed
        -----------
        """
        status_packages = {'x86': {}, 'arm': {}}
        #check installation of package osc 
        if not self.check_existion_of_osc():
            return None
        #generate status statistics dictionary
        x86_packages = self._query_status_num_of_project(project, 'standard_x86_64', status)
        if (len(x86_packages["packages"]) != 0) and (x86_packages["packages"][0] == 'fault'):
            log_check.error(f'{project}:x86:get {status} package failed')
            return None
        status_packages['x86'] = x86_packages
        arm_packages = self._query_status_num_of_project(project, 'standard_aarch64',status)
        if (len(arm_packages["packages"]) != 0) and (arm_packages["packages"][0] == 'fault'):
            log_check.error(f'{project}:aarch64:get {status} package failed')
            return None
        status_packages['arm'] = arm_packages
        return status_packages

    def _get_level_from_db(self, project, repository, package):
        """
        @description : get package build level from database
        -----------
        @param : 
            project:    project name
            repository: repository name
            package:    package name
        -----------
        @returns : package level
        -----------
        """
        query_cmd = 'SELECT level FROM buildtime WHERE project=\'' \
                    + 'openEuler:Mainline' + '\' and repository=\'' + repository \
                    + '\' and package=\'' + package + '\''
        try:
            ret_list = self.cursor.execute(query_cmd).fetchone()
        except BaseException as e:
            log_check.error(f'database query error, due to {e}')
            return None
        if not ret_list is None:
            return ret_list[0]
        else:
            log_check.error(f'{project}:{repository}:{package} build level invalid')
            return None
    
    @staticmethod
    def _gen_valid_level_list():
        """
        @description : generate valid level name list
        -----------
        @param : NA
        -----------
        @return : valid level name list
        -----------
        """
        level_list = []
        for index in range(MULTI_LEVELS):
            level_name = 'l' + str(index + 1)
            level_list.append(level_name)
        return level_list

    def _gen_arch_level_statistics(self, packagelist, project, arch):
        """
        @description : get package level statistics in specified architecture
        -----------
        @param :
            packagelist : package list
            project :     project name, validation is checked by invoker
            arch :        architecture name
        -----------
        @returns : amount of packages in each level
        -----------
        """
        level_list = [0 for n in range(MULTI_LEVELS)]
        valid_level_name = self._gen_valid_level_list()
        #check validation of param arch
        if not arch in ['standard_x86_64', 'standard_aarch64']:
            log_check.error(f'parameter {arch} is invalid')
            return level_list
        for package in packagelist:
            level = self._get_level_from_db(project, arch, package)
            if level in valid_level_name:
                index = valid_level_name.index(level)
                level_list[index] = level_list[index] + 1
            else:
                log_check.error(f'architecture:{arch} from {project} get a invalid level: {level}')
                continue
        return level_list
    
    def _gen_package_amount_in_each_level(self, project, status):
        """
        @description : get specified status package amount in each level
        -----------
        @param :
            project: project name
            status:  specified package status to be statisticd
        -----------
        @returns : level distribution of packages in specified status
        -----------
        """
        level_dict = {"aarch64": {}, "x86": {}}
        #check existion of levelstatistic_check_param
        shell = self._check_shell(LEVELSTATISTIC_CHECK_SHELL)
        if not shell:
            log_check.error(f'levelstatistic_check_param is not exists in../../libs/api!')
            return level_dict
        #check project
        valid = self._check_param(LEVELSTATISTIC_CHECK_SHELL, project)
        if not valid:
            return level_dict
        #check status
        valid = self._check_status(status)
        if not valid:
            log_check.error(f'invalid status')
            return level_dict
        #get package list in specified status
        project_list = self.gen_status_package_list(project, status)
        if project_list is None:
            #erro log is recorded by gen_status_package_list, and empty list is an reasonable value for accumulation
            return level_dict
        x86_package_list = project_list["x86"]["packages"]
        arm_package_list = project_list["arm"]["packages"]
        x86_level_list = self._gen_arch_level_statistics(x86_package_list, project, 'standard_x86_64')
        arm_level_list = self._gen_arch_level_statistics(arm_package_list, project, 'standard_aarch64')
        valid_level_name_list = self._gen_valid_level_list()
        for level in valid_level_name_list:
            index = valid_level_name_list.index(level)
            level_dict["aarch64"][level] = arm_level_list[index]
            level_dict["x86"][level] = x86_level_list[index]
        return level_dict

    def _status_statistics_add(self,status_events_list, events_list_2):
        """
        @description : add status level statistics from different project
        ----------
        @param :
            events_list_1: 
            events_list_2:
        -----------
        @returns : two distribution added results
        -----------
        """
        valid_level_name = self._gen_valid_level_list()
        for level in valid_level_name:
            status_events_list["aarch64"][level] = status_events_list["aarch64"][level] + events_list_2["aarch64"][level]
            status_events_list["x86"][level] = status_events_list["x86"][level] + events_list_2["x86"][level]

    def query_schedule_statistics(self, projectlist):
        """
        @description : get package level statistics from specified project list
        ----------
        @param projectlist: project list
        -----------
        @returns : level distribution of specified status in project list
        ----------
        """
        schedule_events_list={"aarch64":{"l1":0, "l2":0, "l3":0}, "x86":{"l1":0,"l2":0,"l3":0}}
        for project in projectlist:
            single_evens_list = self._gen_package_amount_in_each_level(project, 'scheduled')
            if len(single_evens_list) != 0:
                self._status_statistics_add(schedule_events_list, single_evens_list)
        return schedule_events_list

