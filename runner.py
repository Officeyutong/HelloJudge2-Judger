import docker
from utils import *
from collections import namedtuple

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

    def run(self)->RunnerResult:
        """
        运行指令
        """
        self.container = self.client.containers.create(self.image_name, self.command, tty=True, detach=False, volumes={
            self.mount_dir: {"bind": "/temp", "mode": "rw"}}, mem_limit=self.memory_limit, auto_remove=False)
        import time
        import threading
        import requests.exceptions
        exit_code = 0
        self.container.start()
        count, total = 0, 0

        def memory_handle():
            for curr in self.container.stats(decode=True):
                self.container.reload()
                if self.container.status == "running":
                    nonlocal count, total
                    count, total = count+1, total+curr["memory_stats"]["usage"]
                else:
                    break
                time.sleep(0.001)
        threading.Thread(target=memory_handle).start()
        try:
            begin = time.time()
            exit_code = self.container.wait(
                timeout=self.time_limit)["StatusCode"]
            end = time.time()
        except requests.exceptions.ReadTimeout as ex:
            end = time.time()
        self.container.reload()
        output = self.container.logs().decode()
        if self.container.status == "running":
            self.container.kill()

        self.container.remove()
        return RunnerResult(output, exit_code, end-begin, 0 if count == 0 else total//count)

    def __str__(self):
        return f"<DockerRunner image_name='{self.image_name}' mount_dir='{self.mount_dir}' commands='{self.commands}'>"

    def __repr__(self):
        return str(self)
