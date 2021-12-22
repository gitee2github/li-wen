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
from libs.log.logger import log_check
from main.common.Constant import WSDM_INI_PATH


class QueryConfig(object):
    """
    query config file
    """
    def __init__(self, path):
        """
        @description : initial class
        -----------
        @param :
            path: path of configuration file
        -----------
        @returns :
        -----------
        """
        self.conf_path = path
        

    def get_value(self, section, key):
        """
        @description : get value of (section, key)
        -----------
        @param :
            section:
            key:
        -----------
        @returns : value
        -----------
        """

        if not os.path.exists(self.conf_path):
            log_check.error(f"config file is not exist")
            return None

        config = configparser.ConfigParser()
        config.read(self.conf_path)
        section_list = config.sections()

        try:
            item_value = config.get(section, key)
            return item_value
        except AttributeError as err:
            log_check.error(f"reason: {err}")
            return None
        except configparser.NoSectionError:
            log_check.error(f"appointed section is not exist, valid section listed as below: {section_list}")
            return None
        except configparser.NoOptionError:
            option = config.options(section)
            log_check.error(f"section does not contain specified key, valid key value listed as below: {option}")
            return None

query_config = QueryConfig(WSDM_INI_PATH)

