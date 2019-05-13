import docker
from utils import *


class RunnerResult:
    output: str
    exit_code: int
    time_cost: float
    memory_cost: int

    def __init__(self, output, exit_code, time_cost, memory_cost):
        self.exit_code, self.output, self.time_cost, self.memory_cost = exit_code, output, time_cost, memory_cost

    def __str__(self):
        return f"<RunnerResult output='{self.output}',exit_code={self.exit_code},time_cost={self.time_cost},memory_cost={self.memory_cost}>"

    def __repr__(self):
        return str(self)


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

    def run(self)->RunnerResult:
        """
        运行指令
        raises:
        TimeoutError: 如果超时
        """
        self.container = self.client.containers.create(self.image_name, self.command, tty=True, detach=False, volumes={
            self.mount_dir: {"bind": "/temp", "mode": "rw"}}, mem_limit=self.memory_limit)
        import time
        import requests.exceptions
        begin = time.time()
        try:
            exit_code = self.container.wait(timeout=self.time_limit)
        except requests.exceptions.ReadTimeout as ex:
            pass
        end = time.time()
        self.container.reload()
        memory_cost = self.container.stats(
            stream=False)["memory_stats"].get("max_usage", 0)
        if self.container.status == "running":
            self.container.kill()
        self.container.remove()
        return RunnerResult(self.container.logs(), exit_code, end-begin, memory_cost)

    def __str__(self):
        return f"<DockerRunner image_name='{self.image_name}' mount_dir='{self.mount_dir}' commands='{self.commands}'>"

    def __repr__(self):
        return str(self)
