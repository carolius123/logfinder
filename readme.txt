1. Linux开发环境搭建
    1.1 下载安装python 3.6.5
        # wget http://mirrors.sohu.com/python/3.6.5/Python-3.6.5.tgz
        # tar xf Python-3.6.5.tgz
        # cd Python-3.6.5
        # ./configure --prefix=/usr/local --enable-shared
        # makex
        # make install

        # 建立/etc/ld.so.conf.d/python3.6.5.conf, 内容为：/usr/local/lib，目的是加入共享库路径
        # /sbin/ldconfig -v

    1.2 安装python相关package
        # pip3 install pyinstaller
        # pip3 install chardet

2. 打包
   本软件需要部署到很多被管服务器上，为了降低对被管服务器软件配置的要求，本软件的py程序采样pyinstaller打包为可执行程序。打包命令为：
   pyinstaller -F logfinder.py
   pyinstaller -F distribute.py

3. 分发
