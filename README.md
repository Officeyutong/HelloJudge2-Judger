# 此项目已全面迁移至github(https://github.com/Officeyutong/HelloJudge2-Judger)
# HelloJudge2-Judger

#### 介绍
HelloJudge2评测机

### 部署指南
#### 前置需求
1. 一台装有任意Linux系统的机器(可以不是x86)
2. Python3.8+
3. Docker
4. g++
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

编译此扩展需要```python3.8-dev```(或者更高版本)的支持

然后在```./watcher```目录下运行```compile.sh```即可。

(如果执行时提示有找不到动态库的情况，手动修改compile.sh中的库版本为已安装的库版本即可。)
##### 其他
如果不想在同一台评测机实例上同时进行本地评测和远程评测，那么请务必保证本地评测与远程评测不使用同一个消息队列。
##### 运行
执行```celery -A main worker```即可。

如果在Windows下运行，则为```celery -A main worker -P eventlet```.

本地评测只支持在Linux下使用，远程评测可以在Windows下使用。
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
##### ENABLE_LOCAL_JUDGE
在本评测机实例上启用本地评测.
##### ENABLE_IDE_RUN 
在本评测机实例上启用在线IDE评测.

#### 其他
评测数据会在收到评测请求时通过校对时间戳的方式与Web端进行同步。

如果Web端的评测数据有更新则会自动拉取。

语言配置会在收到评测请求时从Web端拉取。
#### 与Web端添加语言的配套
Web端语言配置文件中的命令行均在评测的容器中执行，故所有相关的修改请自行构建镜像。
### Remote Judge 开发指南
如果您需要编写自己的Remote Judge实现，那么至少要做以下几点:
#### 客户端实现
一个Python模块，其中包括一个继承自judgers.remote_runners.common.JudgeClient并至少实现了```check_login_status```,```create_session```,```login```,```submit```,```get_submission_status```,```fetch_problem```,```as_session_data```的对象。
同时该模块中必须有一个顶级函数get_judge_client，用于返回评测客户端的class
关于各个函数的意义见下文

#### 在main.py中注册
在```main.py```中的JUDGE_CLIENTS中添加你所创建的评测客户端的实例。

#### 在Web端添加
在Web端配置文件中REMOTE_JUDGE_OJS添加相应的OJ配置。

其中Key为该OJ的ID，```display```为该OJ在前端的显示名,```availableLanguages```为该OJ提交可用的语言,其中Key为传递给submit函数的语言ID,```display```为该语言的显示名,```aceMode```为ACE.js所使用的高亮配置。
#### JudgeClient中的各个函数
见代码中注释。
#### JudgeClient各个函数中的session参数
session会被存储到数据库中，作为用户登录远程OJ的凭证。

同时在调用JudgeClient的部分函数时也会传入session参数。

开发者需提供自己的session实现。

session实现必须提供as_dict方法，来将此session对象序列化为dict以便存储进数据库。

同时JudgeClient必须提供as_session_data函数，以便将dict反序列化为当前客户端所使用的session对象。