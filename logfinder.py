#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : logfinder.py
# @Author: Sui Huafeng
# @Date  : 2017/12/8
# @Desc  : 扫描本机所有目录，根据config.ini配置参数识别候选日志文件，并采样。
#   packaged by pyinstaller -F main,py
#   dependence package: chardet,pyinstaller

from os import path
from config import cfg
from sampler import Sampler
from scanner import Scanner


if __name__ == '__main__':
    samples_listfile = path.join(cfg.get('Log', 'Folder'), 'samples.lst')
    Scanner(samples_listfile).run()

    file_fullnames = [line.split('\t')[0].strip() for line in open(samples_listfile, 'r', encoding='utf-8')]
    Sampler.sample(file_fullnames)
