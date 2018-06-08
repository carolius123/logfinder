#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : Distribute.py
# @Author: Sui Huafeng
# @Date  : 2018/6/5
# @Desc  : Distribute(ssh) and launch program to neighbors which can logon
#

import base64
import os
import re
import socket
import struct
import threading
import time

import paramiko

from config import cfg, log


# 尝试以免密或密码表发生向ssh登陆列表和本网段邻居ssh登陆,上传程序并启动扫描
class Distribute(object):
    """
    Distribute program to neighbours
    """

    def __init__(self, credentials):
        self.chain_length = cfg.getint('Distribute', 'ChainLength')  # 链式分发长度，每分发一次减一
        if not self.chain_length:
            return
        self.version = '.version' + cfg.get('Distribute', 'Version')  # 分发时会覆盖小的版本号
        self.sleep_seconds = cfg.getint('Distribute', 'SleepSeconds')  # 多个用户名尝试时，间隔的秒数，防止太频烦尝试
        self.credentials = self.__loadCredentials(credentials)  # 把命令行中登录信息编码存到配置文件，以便分发使用
        self.excluded_subnets = self.__loadSubnets()
        self.objective_hosts = set()
        self.excluded_hosts = set()

        self.run()

    def __loadCredentials(self, credentials):
        if not credentials:
            credentials = cfg.get('Distribute', 'Credentials')
            if not credentials:
                return set()
            credentials = base64.decodebytes(bytes(credentials, encoding='utf8')).decode().split(';')
        self.credentials = [[v.strip() for v in c.split('/')] for c in credentials]
        credentials = ''
        for credential in self.credentials:
            credentials += '/'.join(credential) + ';'
        credentials = base64.encodebytes(bytes(credentials[:-1], encoding='utf8')).decode()
        cfg.set('Distribute', 'Credentials', credentials)

    # 从配置文件中装载需排除的子网信息
    @staticmethod
    def __loadSubnets():
        subnets = set()
        for net_mask in cfg.get('Distribute', 'ExcludeSubnets').split(';'):
            if not net_mask:
                continue
            net, mask = net_mask.split('/')
            net = net.strip()
            mask = mask.strip()
            net = socket.ntohl(struct.unpack("I", socket.inet_aton(net))[0])
            mask = socket.ntohl(struct.unpack("I", socket.inet_aton(mask))[0])
            subnets.add((net, mask))
        return subnets

    def run(self):
        self.excluded_hosts, my_subnets = self.__getLocalSubnets()  # 本机IP/MASK列表
        self.__addKnownHosts()  # 在ssh历史登陆中有的主机
        self.__addNeighbors(my_subnets - self.excluded_subnets)  # 本机所在网段上ssh开启的主机
        self.__saveExcludedSubnets(self.excluded_subnets | my_subnets, self.chain_length - 1)
        for usr, passwd in self.credentials:
            self.objective_hosts -= self.excluded_hosts  # 去掉已分发过的主机
            for host in self.objective_hosts:
                name = '@'.join([usr, host])
                # self.sshConnect(host, usr, passwd)
                threading.Thread(target=self.sshConnect, args=(host, usr, passwd), name=name, daemon=True).start()
            time.sleep(self.sleep_seconds)
        self.__saveExcludedSubnets(chain_length=0)
        return

    # {[ip, mask]}形式返回本机所在子网
    @staticmethod
    def __getLocalSubnets():
        local_subnets, local_ips = set(), set()
        for line in os.popen("/sbin/ifconfig|grep 'inet addr:'|grep -v '127.0.0.1'").read().split('\n'):
            match_ip = re.search(r'inet addr:(\d+\.\d+\.\d+\.\d+)', line)
            if not match_ip:
                continue
            match_mask = re.search(r'Mask:(\d+\.\d+\.\d+\.\d+)', line)
            if not match_mask:
                continue
            ip = match_ip.groups()[0]
            ip_int = socket.ntohl(struct.unpack("I", socket.inet_aton(ip))[0])
            mask = match_mask.groups()[0]
            mask = socket.ntohl(struct.unpack("I", socket.inet_aton(mask))[0])
            net = ip_int & mask
            local_subnets.add((net, mask))
            local_ips.add(ip)
        return local_ips, local_subnets

    # 获取当前账户ssh过的主机列表
    def __addKnownHosts(self):
        known_hosts = os.path.join(os.environ['HOME'], '.ssh/known_hosts')  # 本机ssh过的服务器
        if os.path.isfile(known_hosts):
            contents = open(known_hosts).read()
            for host in re.findall('(\d+\.\d+\.\d+\.\d+)', contents):
                if host not in self.excluded_hosts:
                    self.objective_hosts.add(host)

    # 多线程收集本机所在C网段启动了ssh的host列表
    def __addNeighbors(self, subnets):
        # current_threads = threading.active_count()
        for net, mask in subnets:
            start_ip = net + 1
            range_ = 4294967296 - mask - 2
            if range_ > 256:
                log.info('subnet %d/%d large than 256, skipped..', net, mask)
                continue
            for ip in range(start_ip, start_ip + range_):
                host = socket.inet_ntoa(struct.pack('I', socket.htonl(ip)))
                threading.Thread(target=self.__getNeighbor, args=(host, 22)).start()
        # while threading.active_count() > current_threads:
        time.sleep(5)
        return

    # 探测hos是否启动ssh
    def __getNeighbor(self, host, port):
        try:
            sk = socket.socket()
            sk.settimeout(10)
            sk.connect((host, port))
            sk.shutdown(socket.SHUT_RDWR)
            sk.close()
            self.objective_hosts.add(host)
        except Exception as err:
            log.info('ssh to %s failed:%s', host, str(err))
        return

    @staticmethod
    def __saveExcludedSubnets(excluded_subnets=None, chain_length=None):
        if excluded_subnets:
            net_string = ''
            for net, mask in sorted(list(excluded_subnets)):
                net = socket.inet_ntoa(struct.pack('I', socket.htonl(net)))
                mask = socket.inet_ntoa(struct.pack('I', socket.htonl(mask)))
                net_string += '%s/%s;' % (net, mask)
            cfg.set('Distribute', 'ExcludeSubnets', net_string[:-1])
        if chain_length is not None:
            cfg.set('Distribute', 'ChainLength', str(chain_length))
        with open('./config.ini', 'w', encoding='UTF-8') as cfg_fp:
            cfg.write(cfg_fp)

    def sshConnect(self, host, usr='', passwd='', port=22):
        if not usr:
            usr = os.environ['USER']
        rsa_id_file = os.path.join(os.environ['HOME'], '.ssh/id_rsa')
        transport = paramiko.Transport((host, port))
        try:
            if passwd:
                transport.connect(username=usr, password=passwd)
            elif os.path.isfile(rsa_id_file):
                private_key = paramiko.RSAKey.from_private_key_file(rsa_id_file)
                transport.connect(username=usr, pkey=private_key)
            else:
                raise paramiko.ssh_exception.SSHException('no password given and no .ssh/id_rsa file')
            ssh = paramiko.SSHClient()  # 创建SSH对象
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 允许连接不在know_hosts文件中的主机
            ssh._transport = transport
            if self.distribute(transport, ssh):
                log.info('logfinder launched on %s@%s ****%s', usr, host, passwd[-2:])
            self.excluded_hosts.add(host)
            ssh.close()
        except Exception as err:
            log.info('ssh to %s@%s failed:%s', usr, host, str(err))

        transport.close()
        return

    def distribute(self, transport, ssh):
        stdin, stdout, stderr = ssh.exec_command('cd .logfinder; ls .version*')
        current_version_file = bytes.decode(stdout.read()).strip()
        if current_version_file >= self.version:
            return False

        ssh.exec_command('mkdir .logfinder')  # 执行命令
        ssh.exec_command('cd .logfinder; rm .version*; touch %s' % self.version)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.put('./config.ini', '.logfinder/config.ini')
        sftp.put('./logfinder', '.logfinder/logfinder')
        sftp.close()
        ssh.exec_command('cd .logfinder;chmod +x logfinder')
        ssh.exec_command('cd .logfinder;./logfinder & ')  # 执行命令
        return True
