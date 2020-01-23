from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TestcaseResult:
    # Bytes 内存占用
    memory_cost: int
    # ms 时间占用
    time_cost: int
    # HJ2评测状态
    status: str
    # 输入文件名
    input: str
    # 输出文件名
    output: str
    # 附加信息
    message: str
    # 得分
    score: int
    # 总分
    # 注:得分与总分仅用于显示，题目总分的计算为各Subtask的分数之和。
    full_score: int


@dataclass
class SubtaskResult:
    # 当前子任务分数
    score: int
    # 当前子任务状态
    status: str
    # 当前子任务的测试点列表
    testcases: List[TestcaseResult]


@dataclass
class SubmissionResult:
    # 子任务名 -> 子任务
    subtasks: Dict[str, SubtaskResult] = field(default_factory=dict)
    # 附加信息
    message: str = ""
    # 提交状态
    extra_status: str = ""
