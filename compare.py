from collections import namedtuple

CompareResult = namedtuple("CompareResult", ("same", "message"))


class SPJComparator:

    def __init__(self, spj_file_name):
        pass


class SimpleComparator:
    def __init__(self):
        pass

    def compare(self, user_data, std_data)->CompareResult:
        while user_data and not user_data[-1].strip():
            user_data.pop()
        while std_data and not std_data[-1].strip():
            std_data.pop()
        if len(user_data) != len(std_data):
            return CompareResult(False, f"Different line count: {len(user_data)} and {len(std_data)}.")
        for index, val in enumerate(zip(user_data, std_data)):
            a, b = val
            if a.strip() != b.strip():
                return CompareResult(False, f"Different at line {index}")
        return CompareResult(True, "Ok!")
