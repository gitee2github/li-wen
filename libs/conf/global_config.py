#!/usr/bin/python3
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
# ******************************************************************************/
"""
Global environment variable value when the tool is running
"""


LOG_PATH = '/var/log/li-wen'
CURRENT_WORKERS_INFO = '/var/log/li-wen/workers.csv'
REALTIME_CREATED_WORKERS_INFO = '/var/log/li-wen/realtime_workers.csv'
# Logging level
# The log level option value can only be as follows
# DEBUG INFO WARNING ERROR CRITICAL
LOG_CONSOLE_LEVEL = 'DEBUG'
LOG_FILE_LEVEL = 'DEBUG'

# Maximum capacity of each file, the unit is byte, default is 30M
BACKUP_COUNT = 30

# The size of each log file, in bytes, the default size of a single log file is 30M
MAX_BYTES = 31457280