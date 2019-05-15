from collections import namedtuple
import tempfile
import shutil
CompareResult = namedtuple("CompareResult", ("score", "message"))


class SPJComparator:
    """
    文件名请使用绝对路径
    updator:用于更新评测信息的函数
    """

    def __init__(self, spj_file_name, updator, code):
        updator("Compiling spj..")
        self.updator = updator
        self.work_dir = tempfile.mkdtemp()
        shutil.cop

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
        if len(user_data) != len(std_data):
            return CompareResult(0, f"Different line count: {len(user_data)} and {len(std_data)}.")
        for index, val in enumerate(zip(user_data, std_data)):
            a, b = val
            if a.strip() != b.strip():
                return CompareResult(0, f"Different at line {index}")
        return CompareResult(full_score, "Ok!")
