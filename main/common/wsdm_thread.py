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
"""
This is a custom thread class
"""

import threading
import time
from libs.log.logger import log_check

class WsdmThread(threading.Thread):
    def __init__(self, thread_name, func, args, result=None):
        """
        @description : init function
        -----------
        @param :
            thread_name：name of thread
            func：function of thread
            args：parameters of function
            result：out parameter of function
        -----------
        @returns : NA
        -----------
        """
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.func = func
        self.args = args
        self.result = result or list()

    def run(self):
        """
        @description : run thread
        -----------
        @param : NA
        -----------
        @returns : NA
        -----------
        """
        log_check.info(f"Start thread-{self.thread_name}:{self.args}, at {time.localtime()}")
        self.result.append(self.func(*self.args))
        log_check.info(f"End thread-{self.thread_name}:{self.args}, at {time.localtime()}")