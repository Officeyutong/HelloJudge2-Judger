import docker
# from common.utils import
from collections import namedtuple
import os
from datetime import *
import time
import docker
RunnerResult = namedtuple(
    "RunnerResult", "output exit_code time_cost memory_cost")


class DockerRunner:
    """
    创建一个给定镜像名的Docker容器，然后把mount_dir读写挂载到/temp，然后依次执行commands里面的命令。
    执行完毕后销毁容器。
    args:
    image_name: 镜像名
    mount_dir: 要挂载到docker里的目录
    command: 要执行的命令
    memory_limit: 内存限制,格式形如"500mb"
    time_limit: 时间限制,int，单位ms
    client: 所使用的docker客户端
    """

    def __init__(self, image_name: str, mount_dir: str, command, memory_limit, time_limit, task_name, memory_limit_in_bytes, client=docker.from_env()):
        self.image_name = image_name
        self.mount_dir = mount_dir
        self.command = command
        self.time_limit = time_limit
        self.client = client
        self.task_name = task_name
        self.memory_limit = memory_limit
        self.memory_limit_in_bytes = memory_limit_in_bytes

    # @pysnooper.snoop()
    def run(self) -> RunnerResult:
        """
        运行指令
        """
        self.container = self.client.containers.create(
            self.image_name,
            self.command,
            tty=True,
            detach=False,
            volumes={
                self.mount_dir: {"bind": "/temp", "mode": "rw"}},
            mem_limit=self.memory_limit,
            memswap_limit=self.memory_limit,
            oom_kill_disable=False,
            auto_remove=False,
            network_disabled=True,
            working_dir="/temp",
            cpu_period=1000000,
            cpu_quota=1000000,
            ulimits=[docker.types.Ulimit(name="stack", soft=8277716992, hard=8277716992)])
        print("Run with command "+self.command)

        self.container.start()
        self.container.reload()
        import docker_watcher
        time_cost, memory_cost = docker_watcher.watch(
            self.container.attrs["State"]["Pid"], self.time_limit)
        self.container.reload()
        try:
            if self.container.status != "exited":
                self.container.kill()
        except:
            pass
        self.container.reload()
        output = self.container.logs().decode()
        attr = self.container.attrs.copy()
        self.container.remove()
        if attr["State"]["OOMKilled"]:
            memory_cost = int(attr["HostConfig"]["Memory"])
        elif memory_cost > self.memory_limit_in_bytes and not attr["State"]["OOMKilled"]:
            memory_cost = 0

        # import json
        # print(json.JSONEncoder().encode(attr))
        # if time_cost>self.memo
        return RunnerResult(output, attr["State"]["ExitCode"], time_cost, memory_cost)

    # def __str__(self):
    #     return f"<DockerRunner image_name='{self.image_name}' mount_dir='{self.mount_dir}' commands='{self.commands}'>"

    def __repr__(self):
        return str(self)
