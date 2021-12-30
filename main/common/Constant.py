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

# path of wsdm.ini
WSDM_INI_PATH = '/usr/li-wen/wsdm.ini'

# directory path constant
HISTORY_LOG_PATH = '/var/tmp/li-wen/getbuildtime_history.log'
PROJ_STATUS_RES_PATH = '/var/tmp/li-wen/projectstatus_result.log'
ARCH_STATUS_RES_PATH = '/var/tmp/li-wen/projectststus_architecture.log'
X86_TMP_STATUS_PATH = '/var/tmp/li-wen/x86_temp_status.log'
DATABASE_PATH = '/usr/li-wen/main/monitor/buildtime_cache.db'
WORKER_INFO_PATH = '/var/tmp/li-wen/all_obs_worker_info.log'
INSTANCE_STATISTICS_PATH = '/var/tmp/li-wen/instance_statistics_tmp.log'
ENCRYPTED_DATA_PATH = '/usr/li-wen/libs/conf/worker_management_platform_login_info'
DECRYPT_FILE_PATH = '/usr/li-wen/libs/conf/decryption_file'

# value constant
BUILD_TIME_ITEM_LEN = 17
BUILD_TIME_END_INDEX = 8
BUILD_TIME_END_POS = 9
BUILD_TIME_START_INDEX = 7
BUILD_TIME_START_POS = 11
PACKAGE_STATUS_ITEM = 1
PACKAGE_STATUS_START_POS = 9
EMPTY_CMD_LIST = -1
DECRYPTION_KEY = 'abcd1234'

# file name constant
GETBUILDTIME_CHECK_SHELL = 'getbuildtime_check_param'
PROJECTSTATUS_CHECK_SHELL = 'projectstatus_check_param'
LEVELSTATISTIC_CHECK_SHELL = 'levelstatistic_check_param'

# multi architecture
MULTI_ARCH = ["aarch64", "x86"]

# multi level num
MULTI_LEVELS = 3

# excluded workers
EXCLUDED_WORKERS = '/usr/li-wen/libs/conf/excluded_workers.yaml'
