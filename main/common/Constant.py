#!/bin/env python3
# -*- encoding=utf-8 -*-
"""
# ********************************************************************
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
# ********************************************************************
"""

#directory path constant
HISTORY_LOG_PATH = '/var/tmp/li-wen/getbuildtime_history.log'

#value constant
BUILD_TIME_ITEM_LEN = 17
BUILD_TIME_END_INDEX = 8
BUILD_TIME_END_POS = 9
BUILD_TIME_START_INDEX = 7
BUILD_TIME_START_POS = 11

#file name constant
GETBUILDTIME_CHECK_SHELL = 'getbuildtime_check_param'
