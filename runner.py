import docker
from utils import *
from collections import namedtuple
import os
from datetime import *
RunnerResult = namedtuple(
    "RunnerResult", ["output", "exit_code", "time_cost", "memory_cost"])


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

    def __init__(self, image_name: str, mount_dir: str, command, memory_limit, time_limit, task_name, client=docker.from_env()):
        self.image_name = image_name
        self.mount_dir = mount_dir
        self.command = command
        self.time_limit = time_limit
        self.client = client
        self.task_name = task_name
        self.memory_limit = memory_limit

    # @pysnooper.snoop()
    def run(self)->RunnerResult:
        """
        运行指令
        """
        self.container = self.client.containers.create(self.image_name, self.command, tty=True, detach=False, volumes={
            self.mount_dir: {"bind": "/temp", "mode": "rw"}}, mem_limit=self.memory_limit, auto_remove=False, network_disabled=True, working_dir="/temp", cpu_period=1000, cpu_quota=1000)
        print("Run with command "+self.command)
        memory_cost, time_cost = 0, 0
        self.container.start()
        self.container.reload()
        pid = self.container.attrs["State"]["Pid"]
        cpu_file, memory_file = None, None
        try:
            with open(f"/proc/{pid}/cgroup", "r") as file:
                lines = list(
                    map(lambda x: x.strip().split(":"), file.readlines()))
                for x in lines:
                    if "cpu" in x[1]:
                        cpu_file = os.path.join(
                            "/sys/fs/cgroup/cpu" + x[2], "cpu.stat")
                    if "memory" in x[1]:
                        memory_file = os.path.join(
                            "/sys/fs/cgroup/memory" + x[2], "memory.max_usage_in_bytes")
            while True:
                try:
                    with open(cpu_file, "r") as cpu:
                        time_cost = int(cpu.readline().split(" ")[1])
                        if time_cost >= self.time_limit:
                            self.container.kill()
                            break
                    with open(memory_file, "r") as memory:
                        memory_cost = int(memory.readline())
                except Exception as ex:
                    print(ex)
                    break
        except Exception as ex:
            print(ex)
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
        return RunnerResult(output, attr["State"]["ExitCode"], time_cost, memory_cost)

    def __str__(self):
        return f"<DockerRunner image_name='{self.image_name}' mount_dir='{self.mount_dir}' commands='{self.commands}'>"

    def __repr__(self):
        return str(self)
