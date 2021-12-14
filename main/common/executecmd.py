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
# Create: 2021-07-3
# ******************************************************************************/

import os
import subprocess
from libs.log.logger import log_check
import logging

class ExecuteCmd(object):
    """
    Encapsulates the external interface for executing shell statements 
    """
    @classmethod
    def cmd_status(cls, command, time_out=20):
        """
        @description :Execute command and return to status
        -----------
        @param :
            command: command to be executed
        -----------
        @returns :
            subprocess.run(xxx).returncode
        -----------
        """
        ret = subprocess.run(command, shell=False, stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, encoding="utf-8", timeout = time_out)
        if ret.returncode:
            log_check.error(f"args:{ret.args} \n stderr:{ret.stderr}")
        
        return ret.returncode

    @classmethod
    def cmd_output(cls, command):
        """
        @description : Execute the command and return the output
        -----------
        @param :
            command: command to be executed
        -----------
        @returns :
            subprocess.check_output(xxx)
        -----------
        """
        try:
            subp = subprocess.check_output(command, shell=False, stderr=subprocess.STDOUT, encoding="utf-8")
            return subp
        except subprocess.CalledProcessError as err:
            log_check.error(f"{command}:{err}")
            return None
    