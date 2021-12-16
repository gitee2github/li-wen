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
# Create: 2021-11-24
# ******************************************************************************/
"""
This is an AES encryption and decryption
"""
import ast
import base64
import os
from libs.log.logger import log_check
# yum install python3-pycryptodome
from Crypto.Cipher import AES

class AESEncryAndDecry(object):
    def __init__(self, key, wait_decryption_file, wait_encryption_file=None):
        """
        @description : init aes wait_decryption_file and wait_encryption_file
        -----------
        @param :
            key: 加解密秘钥
            wait_decryption_file：待加密文件
            wait_encryption_file：待解密文件
        -----------
        @returns : NA
        -----------
        """
        self.key = self.__add_to_16(key)
        self.encryption_file = wait_encryption_file
        self.decryption_file = wait_decryption_file
        
    def __add_to_16(self, value):
        """
        @description : Supplement the data of 16 multiples
        -----------
        @param : 
            value: 待补齐16倍数据
        -----------
        @returns :
            补齐为16倍数的数据
        -----------
        """
        while len(value) % 16 != 0:
            value += '\0'
        return str.encode(value)

    # 加密方法
    def encrypt_file(self):
        """
        @description : encrypt the given file and write to file
        -----------
        @param : NA
        -----------
        @returns : NA
        -----------
        """
        try:
            with open(self.encryption_file, 'r', encoding='utf-8') as encryption_f:
                encryption_str = encryption_f.read()
        except FileNotFoundError:
            log_check.error(f"{self.encryption_file} is invalid")
            return

        text = base64.b64encode(encryption_str.encode('utf-8')).decode('ascii')
        # 初始化加密器
        aes = AES.new(self.key, AES.MODE_ECB)
        # 先进行aes加密
        encrypt_aes = aes.encrypt(self.__add_to_16(text))
        # base64转成字符串
        encrypted_text = str(base64.encodebytes(encrypt_aes), encoding='utf-8') # 执行加密并转码返回bytes

        # 写加密数据到文件
        try:
            with open(self.decryption_file,"w") as decryption_f:
                decryption_f.write(encrypted_text)
        except FileNotFoundError:
            log_check.error(f"{self.decryption_file} is invalid")

    # 解密方法
    @property
    def decrypt_file(self):
        """
        @description : decrypt the given file
        -----------
        @param : NA
        -----------
        @returns : 
            decrypted_text: Decrypted text data
        -----------
        """

        try:
            with open(self.decryption_file, 'r', encoding='utf-8') as decryption_f:
                decryption_str = decryption_f.read()
        except FileNotFoundError:
            log_check.error(f"{self.decryption_file} is invalid")
            return None
        
        # 初始化加密器
        aes = AES.new(self.key, AES.MODE_ECB)
        # 优先逆向解密base64成bytes
        base64_decrypted = base64.decodebytes(decryption_str.encode(encoding='utf-8'))
        # bytes解密
        decrypted_text = str(aes.decrypt(base64_decrypted),encoding='utf-8') 
        # 执行解密密并转码返回str
        decrypted_text = base64.b64decode(decrypted_text.encode('utf-8')).decode('utf-8')
        return decrypted_text