#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : sampler.py
# @Author: Sui Huafeng
# @Date  : 2017/12/31
# @Desc  :  从输入文件尾部采样，保存为utf-8格式
#

import os
from shutil import rmtree
from chardet import detect
from time import sleep
import re
from config import cfg, log, win
from socket import gethostbyname, gethostname


class Sampler(object):
    __CodecCheckSize = cfg.getint('ScanFile', 'CodecCheck')
    __StartLine = cfg.getint('Sample', 'StartingLine')
    __EndLine = __StartLine + cfg.getint('Sample', 'SampleLines')
    __MaxSize = cfg.getint('Sample', 'MaxSize') * 1024 * 1024
    __OutputPath = cfg.get('Sample', 'DataPath')
    __OutputFormat = cfg.getint('Sample', 'Format')
    __RegularExpFrom = cfg.get('Sample', 'From')
    __RegularExpTo = cfg.get('Sample', 'To')
    if os.path.exists(__OutputPath):
        rmtree(__OutputPath)
        sleep(1)  # 防止立刻建立目录出错
    os.mkdir(__OutputPath)

    @classmethod
    def sample( cls, files_list ):
        log.info('Starting Samples %d files' % len(files_list))
        if cls.__OutputFormat == 0:
            cls.__merge(cls, files_list)
        else:
            cls.__copy(cls, files_list)

    def __merge(self, file_fullnames):  # 列表中文件每个一行的形式输出到os.ipaddress.sample.dat
        if win:
            output_filename = gethostbyname(gethostname()) + '.samples.dat'
        else:
            cmd = "ifconfig|grep 'inet addr:'|grep -v '127.0.0.1'|cut -d: -f2|awk '{print $1}'|head -1"
            output_filename = os.popen(cmd).read().strip() + '.samples.dat'

        with open(os.path.join(self.__OutputPath, output_filename), 'w', encoding='utf-8') as fp:
            for file_fullname in file_fullnames:
                log.info('Sampling ' + file_fullname)
                current_position = fp.tell()
                try:
                    fp.write('\n' + file_fullname + '\t')
                    for line in self.__readLine(self, file_fullname):
                        fp.write(line.replace('\n', '\0'))
                except Exception as err:
                    log.warning(file_fullname + '\t' + str(err))
                    fp.seek(current_position)
                    continue

    def __copy(self, file_fullnames):
        output_file = ''
        for input_file in file_fullnames:
            log.info('Sampling ' + input_file)
            try:
                if self.__OutputFormat == 2:  # 分目录保存样本文件
                    if win:
                        curr_path = self.__OutputPath + os.sep + os.path.split(input_file)[0].replace(':', '_')
                    else:
                        curr_path = self.__OutputPath + os.path.split(input_file)[0]
                    os.makedirs(curr_path, exist_ok=True)
                    output_file = os.path.join(curr_path, os.path.split(input_file)[1])
                else:  # 保存在同一目录中，文件名中体现原目录结构
                    file_name = input_file.replace(os.sep, '_').replace(':', '_')
                    output_file = self.__OutputPath + '/' + file_name

                with open(output_file, 'w', encoding='utf-8') as fp:
                    for line in self.__readLine(self, input_file):
                        fp.write(line)
            except Exception as err:
                log.warning(input_file + '\t' + str(err))
                if os.path.exists(output_file):
                    os.remove(output_file)
                continue

    def __readLine(self, file_fullname, encoding='ascii'):
        with open(file_fullname, 'rb') as fp:
            size = os.path.getsize(file_fullname)
            if size > self.__MaxSize:   # 出现过几十G大文件、第一行就非常大，导致内存耗尽情况
                fp.seek(-self.__MaxSize, 2)
            for lines, line_binary in enumerate(fp):
                if lines < self.__StartLine:
                    continue
                if lines > self.__EndLine:
                    break

                try:
                    line = line_binary.decode(encoding=encoding)
                    log.debug(str(lines) + ' ' + line)
                    if self.__RegularExpFrom != '':
                        line = re.sub(self.__RegularExpFrom, self.__RegularExpTo, line)
                    yield line
                except UnicodeDecodeError:
                    encoding = detect(line_binary[:self.__CodecCheckSize])['encoding']  # 出现过一行10M，本函数不退出的情况
                    if encoding is None:
                        raise  # 无法识别编码，向上层传递异常
                    line = line_binary.decode(encoding=encoding)
                    if self.__RegularExpFrom != '':
                        line = re.sub(self.__RegularExpFrom, self.__RegularExpTo, line)
                    yield line


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        init_path = sys.argv[1]
    else:
        init_path = input("input path of filename")

    if os.path.isdir(init_path):
        for dir_path, dir_names, file_names in os.walk(init_path):
            file_names = [os.path.join(dir_path, file_name) for file_name in file_names]

            Sampler.sample(file_names)
    else:
        Sampler.sample([init_path])
