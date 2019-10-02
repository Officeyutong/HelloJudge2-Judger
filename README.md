# HelloJudge2-Judger

#### 介绍
HelloJudge2评测机

### 部署指南
#### 前置需求
1. 一台装有任意Linux系统的机器(可以不是x86)
2. Python3.6+
3. Docker
4. g++
5. boost_python
#### 过程
##### 首先
使用```git```将本项目clone到本地。

把```config_default.py```复制一份，改名为```config.py```。

使用```pip3 install -r requirements.txt```安装依赖。
##### 构建Docker镜像
在```./docker```目录下执行```docker build .```，就会开始自动构建评测所需要使用的Docker镜像。

这个过程需要保证网络畅通。

国内用户若网络不稳定或构建过程中速度较慢可修改```./docker/DockerFile```

将

```
# RUN sed -i 's/archive.ubuntu.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list
# RUN sed -i 's/security.ubuntu.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list
```

改为

```
RUN sed -i 's/archive.ubuntu.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list
RUN sed -i 's/security.ubuntu.com/mirrors.ustc.edu.cn/g' /etc/apt/sources.list
```



构建完成后请记录下镜像ID
##### 构建watcher
评测端使用一个由C++编写的Python扩展来监控程序的运行时间。

编译此扩展需要boost_python的支持。

对于Ubuntu，可以使用```apt install libboost1.65-all-dev```进行安装。

然后在```./watcher```目录下运行```compile.sh```即可。
##### 运行
执行```celery -A main worker```即可。

#### 配置文件
##### REDIS_URI
Web端所连接的```Redis```的URI。
##### DATA_DIR
评测数据存放的目录。
相对于当前所在的目录
##### WEB_URL
Web端访问的URL
##### JUDGER_UUID
此评测机的UUID
##### DOCKER_IMAGE
构建的Docker镜像名
#### 其他
评测数据会在收到评测请求时通过校对时间戳的方式与Web端进行同步。

如果Web端的评测数据有更新则会自动拉取。

语言配置会在收到评测请求时从Web端拉取。
#### 与Web端添加语言的配套
Web端语言配置文件中的命令行均在评测的容器中执行，故所有相关的修改请自行构建镜像。
