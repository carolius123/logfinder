#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : config.py
# @Author: Sui Huafeng
# @Date  : 2017/12/28
# @Desc  : 读取配置文件、初始化日志设置，生成cfg、log对象
#

import logging
import sys
from configparser import ConfigParser
from os import path, mkdir


def logSettings( logger ):
    program_path, program_file = path.split(sys.argv[0])
    log_path = path.join(program_path, 'logs')
    if not path.exists(log_path):
        mkdir(log_path)

    log_level = cfg.getint('Log', 'Level')
    logger.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(filename)s %(lineno)d\t%(message)s')
    fh = logging.FileHandler(path.join(log_path, path.splitext(program_file)[0] + '.log'))
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if cfg.getboolean('Log', 'StdOut'):
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    logger.debug('%s stared!', sys.argv[0])


cfg = ConfigParser()
cfg.read(path.join(path.split(sys.argv[0])[0], 'config.ini'), encoding='UTF-8')

log = logging.getLogger(sys.argv[0])
logSettings(log)
