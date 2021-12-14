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
# Create: 2020-08-10
# ******************************************************************************/
"""
log module：logger.py
"""
import configparser
from concurrent_log_handler import ConcurrentRotatingFileHandler

import datetime
import logging
import os
import pathlib
from libs.conf import global_config

class Logger(object):
    """
    operation log of the system
    """
    def __init__(self, name=__name__):
        self.__current_rotating_file_handler = None
        self.__console_handler = None
        self.__path = os.path.join(global_config.LOG_PATH, "wsdm.log")
        
        if not os.path.exists(self.__path):
            try:
                os.makedirs(os.path.split(self.__path)[0])
            except FileExistsError:
                pathlib.Path(self.__path).touch(mode=0o644)
                
        self.__logger = logging.getLogger(name)
        self.__logger.setLevel(global_config.LOG_CONSOLE_LEVEL)

    def __init_handler(self):
        """
        @description : Initial handler
        -----------
        @param :NA
        -----------
        @returns :NA
        -----------
        """
        
        self.__current_rotating_file_handler = ConcurrentRotatingFileHandler(
            filename=self.__path,
            mode="a",
            maxBytes=global_config.MAX_BYTES,
            backupCount=global_config.BACKUP_COUNT,
            encoding="utf-8",
            use_gzip=True,
        )
        self.__console_handler = logging.StreamHandler()
        self.__set_formatter()
        self.__set_handler()

    def __set_formatter(self):
        """
        @description : Set log print format
        -----------
        @param :NA
        -----------
        @returns :NA
        -----------
        """
        
        formatter = logging.Formatter(
            '[%(asctime)s][%(levelname)s][%(module)s:%(lineno)d|%(funcName)s] %(message)s',
            datefmt="%a, %d %b %Y %H:%M:%S",
        )

        self.__current_rotating_file_handler.setFormatter(formatter)
        self.__console_handler.setFormatter(formatter)

    def __set_handler(self):
        self.__current_rotating_file_handler.setLevel(global_config.LOG_FILE_LEVEL)
        self.__logger.addHandler(self.__current_rotating_file_handler)
        self.__logger.addHandler(self.__console_handler)

    @property
    def logger(self):
        """
        @description :Gets the logger property, both file and console handle
        -----------
        @param :NA
        -----------
        @returns :NA
        -----------
        """
        if not self.__current_rotating_file_handler:
            self.__init_handler()
        return self.__logger

    @property
    def file_handler(self):
        """
        @description :Get the file handle to the log
        -----------
        @param :NA
        -----------
        @returns :NA
        -----------
        """
        if not self.__current_rotating_file_handler:
            self.__init_handler()
        return self.__current_rotating_file_handler

log_check = Logger(__name__).logger

