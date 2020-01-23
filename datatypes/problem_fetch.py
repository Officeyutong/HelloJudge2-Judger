from dataclasses import dataclass, field
from typing import List
from typing import Dict


@dataclass
class ProblemExampleCase:
    # 样例输入
    input: str
    # 样例输出
    output: str


@dataclass
class ProblemFetchResult:
    """
    题目爬取结果
    """
    # 题目名
    title: str
    # 题目背景
    background: str
    # 题目内容
    content: str
    # 提示
    hint: str
    # 输入格式
    inputFormat: str
    # 输出格式
    outputFormat: str
    # ms 时间限制
    timeLimit: int
    # KB 内存限制
    memoryLimit: int
    # 远程题目ID
    remoteProblemID: str
    # 远程OJ ID
    remoteOJ: str
    # 样例
    examples: List[ProblemExampleCase]
