from collections import namedtuple
import tempfile
import shutil
import os
from runner import *
CompareResult = namedtuple("CompareResult", ("score", "message"))


class SPJComparator:
    """
    spj_file_name:str文件名 请使用绝对路径
    updator:用于更新评测信息的函数
    lang:module 语言配置
    image:str docker镜像名
    SPJ可以为任何所支持的语言编写的程序，但是文件名格式应该为 spj_语言ID.xxx,扩展名不限
    例如spj_cpp11.cpp ,spj_java8.java
    SPJ运行时间不会被计算在这个测试点的时间开销中
    评测时spj所在目录下将会有以下文件:
    full_score: 这个测试点的满分
    user_code: 用户代码
    user_output: 用户程序输出
    answer: 测试点标准答案
    SPJ应该在限制的时间内将结果输出到以下文件
    score: 该测试点得分
    message: 发送给用户的信息
    """

    def __init__(self, spj_file_name, updator, code, lang, run_time_limit, image):
        updator("编译SPJ中..")
        self.updator = updator
        self.work_dir = tempfile.mkdtemp()
        self.lang = lang
        self.run_time_limit = run_time_limit
        self.image = image
        shutil.copyfile(spj_file_name, os.path.join(
            self.work_dir, lang.SOURCE_FILE.format(filename="spj")))
        runner = DockerRunner(
            image,
            work_dir,
            lang.COMPILE.format(source=lang.SOURCE_FILE.format(
                filename="spj"), output=lang.OUTPUT_FILE.format(filename="spj")),
            512*1024*1024,
            3000
        )
        result = runner.run()
        if not os.path.exists(os.path.join(work_dir, lang.OUTPUT_FILE.format(filename="spj"))):
            raise RuntimeError(f"SPJ编译失败: {result.output}")
        

    def compare(self, user_data, std_data, full_score) -> CompareResult:
        pass

    def __del__(self):
        shutil.rmtree(self.work_dir)


class SimpleComparator:
    def __init__(self):
        pass

    def compare(self, user_data, std_data, full_score) -> CompareResult:
        while user_data and not user_data[-1].strip():
            user_data.pop()
        while std_data and not std_data[-1].strip():
            std_data.pop()

        # print(user_data,std_data)
        if len(user_data) != len(std_data):
            return CompareResult(0, f"Different line count: Your:{len(user_data)} and {len(std_data)}.")
        for index, val in enumerate(zip(user_data, std_data)):
            a, b = val
            if a.strip() != b.strip():
                return CompareResult(0, f"Different at line {index}")
        return CompareResult(full_score, "Ok!")
