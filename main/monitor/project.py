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
from main.common.Constant import BUILD_TIME_ITEM_LEN
from main.common.Constant import BUILD_TIME_END_INDEX
from main.common.Constant import BUILD_TIME_END_POS
from main.common.Constant import BUILD_TIME_START_INDEX
from main.common.Constant import BUILD_TIME_START_POS
from main.common.Constant import GETBUILDTIME_CHECK_SHELL

EXECMD = ExecuteCmd()

class QueryProject(object):
    """
    query project information such as:
    1. building time of one package
    2. package amount in specified status
    3. package level distribution in specified status
    """
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
        if not 'obs-wsdm' in path_list:
            return None
        proj_index = path_list.index('obs-wsdm')
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
        valid = EXECMD.cmd_output(cmd.split())
        if valid is None:
            log_check.error(f'implement parameter check cmd failed!')
            return False
        elif 'Usage:' in valid:
            log_check.error(f'invalid parameter! effective parameters \
                              as follows: \n {valid}')
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
            query_result = EXECMD.cmd_output(cmd.split())
        except FileNotFoundError:
            log_check.error(f'packge osc dose not installed in running machine')
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
        result = EXECMD.cmd_status(cmd.split())
        #delete invalid item
        cmd = 'sed -i ' + '/jobhistlist/d' + ' ' + HISTORY_LOG_PATH
        result += EXECMD.cmd_status(cmd.split()) 
        cmd_list = ['sed', '-i', '/SSL certificate checks disable/d', \
                    HISTORY_LOG_PATH]
        result += EXECMD.cmd_status(cmd_list)
        cmd = 'sed -i ' + '1d' + ' ' + HISTORY_LOG_PATH
        result += EXECMD.cmd_status(cmd.split())
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
        history_content = EXECMD.cmd_output(cmd.split())
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

