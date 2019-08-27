from collections import namedtuple
import tempfile
import shutil
import os
from runner import *
import pathlib
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
    user_out: 用户程序输出
    answer: 测试点标准答案
    SPJ应该在限制的时间内将结果输出到以下文件
    score: 该测试点得分(0~100,自动折合)
    message: 发送给用户的信息
    """

    def __init__(self, spj_file_name, updator, code, lang, run_time_limit, image):
        updator("编译SPJ中..")
        self.updator = updator
        self.work_dir = tempfile.mkdtemp()
        self.word_dir_path = pathlib.PurePath(self.work_dir)
        self.lang = lang
        self.run_time_limit = run_time_limit
        self.image = image
        shutil.copyfile(spj_file_name, os.path.join(
            self.work_dir, lang.SOURCE_FILE.format(filename="spj")))
        runner = DockerRunner(
            image,
            self.work_dir,
            lang.COMPILE.format(source=lang.SOURCE_FILE.format(
                filename="spj"), output=lang.OUTPUT_FILE.format(filename="spj"), extra=""),
            512*1024*1024,
            3000,
            "SPJ"
        )
        result = runner.run()
        if not os.path.exists(os.path.join(self.work_dir, lang.OUTPUT_FILE.format(filename="spj"))) or result.exit_code != 0:
            raise RuntimeError(
                f"SPJ编译失败: {result.output}\nExit code:{result.exit_code}")

    def compare(self, user_data, std_data, full_score) -> CompareResult:
        with open(self.word_dir_path/"user_out", "w") as user_out:
            for line in user_data:
                user_out.write(line+"\n")
        with open(self.word_dir_path/"answer", "w") as answer:
            for line in std_data:
                answer.write(line+"\n")
        with open(self.word_dir_path/"full_score", "w") as f:
            f.write(str(full_score))
        self.updator("运行SPJ中..")
        runner = DockerRunner(
            self.image,
            self.work_dir,
            self.lang.RUN.format(
                program=self.lang.OUTPUT_FILE.format(filename="spj"), redirect=""),
            512*1024*1024,
            3000,
            "SPJ"
        )
        result: RunnerResult = runner.run()
        if result.exit_code != 0:
            return CompareResult(-1, f"SPJ exit with a code{result.exit_code}")
        import os
        if not os.path.exists(self.word_dir_path/"score"):
            return CompareResult(-1, "SPJ didn't provide a valid score file.")
        with open(self.word_dir_path/"score", "r") as f:
            score = int(f.readline().strip())
        message = "SPJ told you nothing but a score"
        if os.path.exists(self.word_dir_path/"message"):
            with open(self.word_dir_path/"message", "r") as f:
                message = f.readline()
        if score < 0 or score > 100:
            return CompareResult(-1, f"SPJ output an unrecognizable score: {score}")
        return CompareResult(int(score/100*full_score+0.5), message)

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
