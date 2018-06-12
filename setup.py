#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : setup.py
# @Author: Sui Huafeng
# @Date  : 2018/6/12
# @Desc  : 
#

import os
import sys

from config import cfg


#


class setup(object):
    def __init__(self):
        x = 1

    @staticmethod
    def cron():
        schedule = cfg.get('Setup', 'Cron')
        if schedule:
            os.popen('echo %s %s & > cron.cfg; crontab cron.cfg', schedule, sys.argv[0])

    def service(self):
        x = 1

    def autorun(self):
        x = 1

    @staticmethod
    def selfDiscipline():
        import resource
        max_cpu_seconds = cfg.getint('Setup', 'maxMemBytes')
        if max_cpu_seconds:
            resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_seconds, max_cpu_seconds))

        max_mem_bytes = cfg.getint('Setup', 'maxCPUSeconds')
        if max_mem_bytes:
            resource.setrlimit(resource.RLIMIT_DATA, (max_mem_bytes, max_mem_bytes))


if __name__ == '__main__':
    setup()
