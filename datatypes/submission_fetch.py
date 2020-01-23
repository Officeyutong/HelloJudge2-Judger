from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TestcaseResult:
    # Bytes
    memory_cost: int
    # ms
    time_cost: int
    status: str
    input: str
    output: str
    description: str
    score: int
    full_score: int


@dataclass
class SubtaskResult:
    # 当前测试点分数
    score: int
    # 当前测试点状态
    status: str
    testcases: List[TestcaseResult]


@dataclass
class SubmissionResult:
    # 子任务名 -> 子任务
    subtasks: Dict[str, SubtaskResult] = field(default_factory=dict)
    message: str = ""
    # 如果指定,则会把此作为评测结果
    extra_status: str = ""
