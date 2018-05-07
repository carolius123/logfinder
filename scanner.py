#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : scanner.py
# @Author: Sui Huafeng
# @Date  : 2018/1/1
# @Desc  : 扫描全盘，找出候选日志文件，把文件名称等信息保存到文件中
# 

import os
import time
from re import match

from config import cfg, log, win
from judger import Judger


class Scanner(object):
    __SleepSeconds = cfg.getint('ScanFile', 'Sleep')
    __MaxFiles = cfg.getint('ScanFile', 'MaxFiles')
    __MaxSeconds = cfg.getint('ScanFile', 'MaxSeconds')
    if win:  # 根据不同操作系统设置起始扫描目录
        __InitialPaths = [chr(i) + ':\\' for i in range(0x61, 0x7a) if os.path.isdir(chr(i) + ':\\')]
        __ExcludedPaths = cfg.get('ScanFile', 'ExcludedWin').lower().split()
    else:
        __InitialPaths = ['/']
        __ExcludedPaths = cfg.get('ScanFile', 'ExcludedUnix').lower().split()

    def __init__(self, sample_list_file=os.path.join(cfg.get('Log', 'Folder'), 'samples.lst')):
        self.__SampleListFile = sample_list_file

    def run(self):
        with open(self.__SampleListFile, 'w', encoding='utf-8') as fp:
            scaned_files, sampled_files, err_counters = 0, 0, [0, 0, 0, 0, 0, 0]
            for initial_path in self.__InitialPaths:
                for dir_path, dir_names, file_names in os.walk(initial_path):
                    if False in [not match(excluded_path, dir_path) for excluded_path in
                                 self.__ExcludedPaths]:  # 跳过例外目录
                        dir_names[:] = []  # 跳过例外目录的子目录
                        continue
                    if not os.access(dir_path, os.X_OK | os.R_OK):  # 有的目录下面的循环拦不住！
                        log.warning('[Permission Denied:] ' + dir_path)
                        continue
                    for dir_name in dir_names:  # 对无权进入的子目录，从扫描列表中清除并记录告警日志
                        dir_fullname = os.path.join(dir_path, dir_name)
                        if not os.access(dir_fullname, os.X_OK | os.R_OK):
                            dir_names.remove(dir_name)
                            log.warning('[Permission denied:] ' + dir_fullname)
                    if len(file_names) > self.__MaxFiles:  # 目录下文件特别多,很可能是数据文件目录
                        log.warning('[Too Many Files]( ' + str(len(file_names)) + '), Ignoring:' + dir_path)
                        continue

                    timer = time.time()
                    for file_name in file_names:
                        try:
                            scaned_files += 1
                            if scaned_files % 1000 == 0:
                                log.info(
                                    'Files scaned:[%d], error[%d], inactive[%d], small[%d], wrong-type[%d], non-text[%d], candidate[%d]\t%s' % (
                                        scaned_files, err_counters[0], err_counters[1], err_counters[2],
                                        err_counters[3], err_counters[4] + err_counters[5], sampled_files, dir_path))
                                if time.time() - timer > self.__MaxSeconds:  # Too slow to scan a folder
                                    log.warning('[Too slow to scan, Ignoring:]( ' + dir_path)
                                    break
                                time.sleep(self.__SleepSeconds)  # 防止过多占有系统资源

                            file_fullname = os.path.join(dir_path, file_name)
                            rc = Judger.filter(file_fullname)
                            if type(rc) is int:  # 该文件不是候选日志，无需采
                                err_counters[rc] += 1
                                continue
                            print(file_fullname, file=fp)
                            sampled_files += 1
                        except Exception as err:  # 出现过目录/文件名为乱字符导致写fp文件出现字符集异常情况
                            log.error(str(err))

        log.info('Finish scan:[%d], error[%d], inactive[%d], small[%d], wrong-type[%d], non-text[%d], candidate[%d]' % (
            scaned_files, err_counters[0], err_counters[1], err_counters[2], err_counters[3],
            err_counters[4] + err_counters[5], sampled_files))


if __name__ == '__main__':
    Scanner().run()
