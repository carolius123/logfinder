#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : config.py
# @Author: Sui Huafeng
# @Date  : 2017/12/28
# @Desc  : 读取配置文件、初始化日志设置，生成cfg、log对象
#

from os import path, mkdir
import logging
import configparser
from platform import system
import sys


def logSettings( logger ):
    log_path = cfg.get('Log', 'Folder')
    if not path.exists(log_path):
        mkdir(log_path)

    log_level = cfg.getint('Log', 'Level')
    logger.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s')
    fh = logging.FileHandler(log_path + path.splitext(path.split(sys.argv[0])[1])[0] + '.log')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if cfg.getboolean('Log', 'StdOut'):
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    logger.debug("stared!")


if system() == 'Windows':
    win = True
else:
    win = False

cfg = configparser.ConfigParser()
cfg.read('./config.ini', encoding='UTF-8')

log = logging.getLogger()
logSettings(log)
