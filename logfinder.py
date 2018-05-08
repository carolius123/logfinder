#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : Logfinder.py
# @Author: Sui Huafeng
# @Date  : 2018/1/1
# @Desc  : Scan all files of localhost to find candidates of log files
# 

import os
import re
import socket
import sys
import tarfile
import time
from platform import system
from shutil import rmtree

from chardet import detect

from config import cfg, log


class Logfinder(object):
    """
    Scan all files of localhost to find candidates of log files
    """
    __defaultEncoding = sys.getdefaultencoding()

    def __init__(self):
        self.__loadConfig()
        self.uploadFile('d:\\home\\ftp_upload.txt')

        if os.path.exists(self.__OutputPath):
            rmtree(self.__OutputPath)
            time.sleep(1)  # 防止立刻建立目录出错
        os.mkdir(self.__OutputPath)

        sample_dir = self.scanning()
        result_list = self.sampleFiles(sample_dir)
        tar_file = self.archiveFiles(result_list)
        rmtree(self.__OutputPath)
        self.uploadFile(tar_file)

    # 初始化配置参数
    def __loadConfig(self):
        self.__SleepSeconds = cfg.getint('ScanFile', 'Sleep')  # Sleeping seconds per 1000 files scanned
        self.__MaxFiles = cfg.getint('ScanFile', 'MaxFiles')  # skip folder if files exceed
        self.__MaxSeconds = cfg.getint('ScanFile', 'MaxSeconds')  # skip folder if too long to scan
        self.__SmallFileMaxSize = cfg.getint('ScanFile', 'SmallFile') * 1024  # skip file less than
        self.__LastUpdateSeconds = cfg.getint('ScanFile', 'LastUpdate') * 3600  # skip file elder than
        self.__CodecCheckSize = cfg.getint('ScanFile', 'CodecCheck')  # chardet sample size
        self.__ExcludedExtensions = cfg.get('ScanFile', 'ExcludedExt').lower().split()
        self.__StartLine = cfg.getint('Sample', 'StartingLine')
        self.__EndLine = self.__StartLine + cfg.getint('Sample', 'SampleLines')
        self.__MaxSize = cfg.getint('Sample', 'MaxSize') * 1024 * 1024
        self.__LogPath = cfg.get('Log', 'Folder')
        self.__OutputPath = cfg.get('Sample', 'DataPath')
        self.__OutputFormat = cfg.get('Sample', 'Format')
        self.__FromRegExp = re.compile(cfg.get('Sample', 'From'))
        self.__ToRegExp = cfg.get('Sample', 'To')
        # 根据不同操作系统设置起始扫描目录
        if system() == 'Windows':
            self.__win = True
            self.__InitialPaths = [chr(i) + ':\\' for i in range(0x61, 0x7a) if os.path.isdir(chr(i) + ':\\')]
            self.__ExcludedPathRegexp = re.compile(cfg.get('ScanFile', 'ExcludedWin'), re.IGNORECASE)
        else:
            self.__win = False
            self.__InitialPaths = ['/']
            self.__ExcludedPathRegexp = re.compile(cfg.get('ScanFile', 'ExcludedUnix'), re.IGNORECASE)

    # 扫描并识别日志文件
    def scanning(self):
        sample_list = []
        fc = {'Scanned': 0, 'sampled': 0, 'err': 0, 'old': 0, 'small': 0, 'invalid ext': 0, 'binary': 0}
        for initial_path in self.__InitialPaths:
            for dir_path, dir_names, file_names in os.walk(initial_path):
                if self.__filterFolder(dir_path, dir_names, file_names):  # 滤除无需扫描的目录
                    continue
                file_fullnames = self.__filterFiles(dir_path, file_names)
                self.__scanFolder(dir_path, file_fullnames, sample_list, fc)  # 扫描目录下文件
        log.info('Finish %s', ', '.join(['%s %d' % (k, v) for k, v in fc.items()]))
        return sample_list

    # 过滤掉配置文件指定的例外目录, 无权限目录, 文件特别多的目录
    def __filterFolder(self, dir_path, dir_names, file_names):
        # 跳过例外目录及其子目录
        if self.__ExcludedPathRegexp.match(dir_path):
            log.debug('[Excluded in config file:] ' + dir_path)
            dir_names[:] = []
            return True

        # 跳过无权限目录及其子目录
        if not os.access(dir_path, os.X_OK | os.R_OK):  # 有的目录下面的循环拦不住！
            log.warning('[Permission Denied:] ' + dir_path)
            dir_names[:] = []
            return True

        for dir_name in dir_names:  # 对无权进入的子目录，从扫描列表中清除并记录告警日志
            dir_fullname = os.path.join(dir_path, dir_name)
            if not os.access(dir_fullname, os.X_OK | os.R_OK):
                dir_names.remove(dir_name)
                log.warning('[Permission denied:] ' + dir_fullname)
        if len(file_names) == 0:
            return True

        # 目录下文件特别多,很可能是数据文件目录,忽略之
        files = len(file_names)
        if files == 0 or files > self.__MaxFiles:
            log.warning('[No or too Many Files](%d), ignoring:%s', files, dir_path)
            return True

        return False

    # 如目录中最新文件还是太老,直接跳过
    def __filterFiles(self, dir_path, file_names):
        now_ = time.time()
        file_fullnames = []
        for file_name in file_names:
            try:
                file_fullname = os.path.join(dir_path, file_name)
                if now_ - os.path.getmtime(file_fullname) > self.__LastUpdateSeconds:  # long time no update
                    continue
                file_fullnames.append(file_fullname)
            except FileNotFoundError:
                continue
        return file_fullnames

    # 扫描指定目录下文件
    def __scanFolder(self, dir_path, file_fullnames, sample_list, fc):
        now_ = time.time()
        for file_fullname in file_fullnames:
            try:
                fc['Scanned'] += 1
                if not fc['Scanned'] % 1000:
                    log.info('Files %s\t%s', ', '.join(['%s %d' % (k, v) for k, v in fc.items()]), dir_path)
                    time.sleep(self.__SleepSeconds)  # 防止过多占有系统资源

                # 目录扫描特别慢,跳过
                if time.time() - now_ > self.__MaxSeconds:  # Too slow to scan a folder
                    log.warning('[Too slow to scan, Ignoring:]( ' + dir_path)
                    break

                if self.__isLogFile(file_fullname, fc):  # 该文件候选日志，本目录需要采集
                    sample_list.append(dir_path)
                    fc['sampled'] += 1
                    break
            except Exception as err:  # 出现过目录/文件名为乱字符导致写fp文件出现字符集异常情况
                log.error(str(err))

    # 滤除太小,太旧,可执行,非文本,及无效扩展名的文件
    def __isLogFile(self, file_fullname, fc):
        try:
            size, last_update = os.path.getsize(file_fullname), os.path.getmtime(file_fullname)
            if time.time() - last_update > self.__LastUpdateSeconds:  # long time no update
                fc['old'] += 1
            elif self.__win and last_update <= os.path.getctime(file_fullname):  # no update after create
                fc['old'] += 1
            elif size < self.__SmallFileMaxSize:  # too small, looks not like a production log
                fc['small'] += 1
            elif os.path.splitext(file_fullname)[1].lower() in self.__ExcludedExtensions:  # excluded extension,
                fc['invalid ext'] += 1
            elif (not self.__win) and os.access(file_fullname, os.X_OK):  # unix executive, not log
                fc['binary'] += 1
            else:
                with open(file_fullname, 'rb') as fp:  # not txt file, not log
                    if size > self.__CodecCheckSize * 2:  # 文件中间判断，准确性可能大些
                        fp.seek(int(size / 2))
                    charset = detect(fp.read(self.__CodecCheckSize))
                    if charset['confidence'] < 0.5:
                        fc['binary'] += 1
                    else:
                        return True
            return False
        except Exception as err:
            log.warning(file_fullname + '\t' + str(err))
            fc['err'] += 1
            return False

    # 采集样本文件到__OutputPath
    def sampleFiles(self, sample_dir):
        self.__LastUpdateSeconds = cfg.getint('Sample', 'LastUpdate') * 3600  # skip file elder than
        fc = {'Scanned': 0, 'sampled': 0, 'err': 0, 'old': 0, 'small': 0, 'invalid ext': 0, 'binary': 0}
        sampled_list = []
        log.info('Starting Samples %d files' % len(sample_dir))
        for path_from in sample_dir:
            log.info('Sampling ' + path_from)
            # 分目录保存样本文件时,创建目录
            path_to = self.__OutputPath
            if self.__OutputFormat == 'Separate':
                if self.__win:
                    path_to += os.sep + path_from.replace(':', '_')
                else:
                    path_to += path_from
                os.makedirs(path_to, exist_ok=True)

            for file_name in os.listdir(path_from):
                # 判断是否是潜在日志文件
                file_from = os.path.join(path_from, file_name)
                if not self.__isLogFile(file_from, fc):  # 该文件不是候选日志，无需采
                    continue
                # 生成目标文件名
                if self.__OutputFormat == 'Separate':
                    file_to = os.path.join(path_to, file_name)
                else:  # 保存在同一目录中，文件名中体现原目录结构
                    file_to = os.path.join(path_to, path_from.replace(os.sep, '_').replace(':', '_') + file_name)
                try:
                    with open(file_to, 'w', encoding='utf-8') as fp:
                        for line in self.__readLine(file_from):
                            fp.write(line)
                    sampled_list.append(
                        [file_from, os.path.getsize(file_from), time.time(), os.path.getmtime(file_from)])
                except Exception as err:
                    log.warning('%s\t%s', file_from, str(err))
                    if os.path.exists(file_to):  # 清除出错文件样本
                        os.remove(file_to)
                    continue
        return sampled_list

    def __readLine(self, file_fullname, encoding=__defaultEncoding):
        with open(file_fullname, 'rb') as fp:
            if os.path.getsize(file_fullname) > self.__MaxSize:  # 出现过几十G大文件、第一行就非常大，导致内存耗尽情况
                fp.seek(-self.__MaxSize, 2)
            for lines, line_binary in enumerate(fp):
                if lines < self.__StartLine:
                    continue
                if lines > self.__EndLine:
                    break

                try:
                    line = line_binary.decode(encoding=encoding)
                    yield self.__FromRegExp.sub(self.__ToRegExp, line)
                except UnicodeDecodeError:
                    encoding = detect(line_binary[:self.__CodecCheckSize])['encoding']  # 出现过一行10M，不退出的情况
                    if encoding is None:
                        raise  # 无法识别编码，向上层传递异常
                    line = line_binary.decode(encoding=encoding)
                    yield self.__FromRegExp.sub(self.__ToRegExp, line)

    # 保存采集到的文件列表,归档采集到的文件
    def archiveFiles(self, sample_list):
        with open(os.path.join(cfg.get('Sample', 'DataPath'), 'descriptor.csv'), 'w', encoding='utf-8') as fp:
            for file_fullname, size_, time_sample, time_last_update in sample_list:
                fp.write('%f\t%f\t%d\t%s\n' % (time_sample, time_last_update, size_, file_fullname))

        tar_file = socket.gethostbyname(socket.gethostname()) + '.tar.gz'
        tar_file = os.path.join(self.__LogPath, tar_file)
        log.info('Archiving %d files into %s', len(sample_list), tar_file)
        tar = tarfile.open(tar_file, 'w:gz')
        current_dir = os.getcwd()
        os.chdir(self.__OutputPath)
        for dir_path, _, file_names in os.walk('.'):
            for file in file_names:
                tar.add(os.path.join(dir_path, file))
        tar.close()
        os.chdir(current_dir)
        return tar_file

    # 上载文件
    def uploadFile(self, local_file):
        for _, v_ in cfg.items('Upload'):
            protocol, host_, port_, usr_, pas_, path_ = v_.split()
            remote_file = os.path.split(local_file)[1]
            try:
                if protocol == 'sftp':
                    self.__sftp(host_, port_, usr_, pas_, path_, local_file, remote_file)
                elif protocol == 'ftp':
                    self.__ftp(host_, port_, usr_, pas_, path_, local_file, remote_file)
                break
            except Exception as err:
                log.warning('upload error %s%s: %s', protocol, host_, str(err))
                continue

    def __sftp(self, host_, port_, usr_, pas_, path_, local_file, remote_file):
        import paramiko
        paramiko.util.log_to_file(os.path.join(self.__LogPath, '.log'))
        t = paramiko.Transport((host_, int(port_)))
        t.connect(username=usr_, password=pas_)
        sftp = paramiko.SFTPClient.from_transport(t)
        sftp.chdir(path_)
        sftp.put(local_file, remote_file)
        t.close()

    def __ftp(self, host_, port_, usr_, pas_, path_, local_file, remote_file):
        import ftplib
        f = ftplib.FTP(host_)
        f.login(usr_, pas_)
        f.cwd(path_)
        fp = open(local_file, 'rb')
        f.storbinary(remote_file, fp, 1024)
        fp.close()


if __name__ == '__main__':
    Logfinder()
