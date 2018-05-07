#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : judger.py
# @Author: Sui Huafeng
# @Date  : 2018/1/1
# @Desc  : 判断输入文件是否是候选的日志文件，并返回其字符集。默认判断依据包括：
#           - 文件更新时间小于<1>个月，保证覆盖循环日志文件和定期批处理任务日志
#           - 更新时间比创建时间晚1分钟以上，滤除近期安装软件或者复制来的文件，以及临时文件等
#           - 文件不小于<1M>，不是<已知扩展名>，不是可执行文件
#           - 是某字符集的文本文件，滤除二进制文件
#         前两个条件不会漏采，且可以滤除绝大部分文件；后三个条件可适当调整。
#         可能误采的主要会是文本输出的数据文件
# 

from os import path, access, X_OK
from time import time
from chardet import detect
from config import cfg, log, win


class Judger(object):
    __SmallFileMaxSize = cfg.getint('ScanFile', 'SmallFile') * 1024
    __LastUpdateSeconds = cfg.getint('ScanFile', 'LastUpdate') * 3600
    __CodecCheckSize = cfg.getint('ScanFile', 'CodecCheck')
    __ExcludedExtensions = cfg.get('ScanFile', 'ExcludedExt').lower().split()

    @classmethod
    def filter(cls, file_fullname):
        try:
            size = path.getsize(file_fullname)
            last_update = path.getmtime(file_fullname)
            if time() - last_update > cls.__LastUpdateSeconds:  # long time no update
                return 1
            if win and last_update <= path.getctime(file_fullname):   # not update after create(no create time for linux)
                return 1
            if size < cls.__SmallFileMaxSize:  # too small, looks not like a production log
                return 2
            if file_fullname[
               file_fullname.rfind('.'):].lower() in cls.__ExcludedExtensions:  # known file extension, not log
                return 3
            if (not win) and access(file_fullname, X_OK):  # unix executive, not log
                return 4
            with open(file_fullname, 'rb') as fp:  # not txt file, not log
                if size > cls.__CodecCheckSize * 2:  # 文件中间判断，准确性可能大些
                    fp.seek(int(size / 2))
                charset = detect(fp.read(cls.__CodecCheckSize))
                if charset['confidence'] < 0.5:
                    return 5
            return charset
        except Exception as err:
            log.warning(file_fullname + '\t' + str(err))
            return 0


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        file = sys.argv[1]
    else:
        file = input("请输入文件名称：")

    err_info = ['操作错误', '久未更新', '文件太小', '扩展名不符', '可执行文件', '无效字符集']
    rc = Judger.filter(file)
    if type(rc) is int:  # 该文件不是候选日志，无需采
        print(err_info[rc])
    else:
        print(rc)
