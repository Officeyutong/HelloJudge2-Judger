from dataclasses import dataclass
from typing import List


@dataclass
class ProblemExampleCase:
    input: str
    output: str


@dataclass
class ProblemFetchResult:
    title: str
    background: str
    content: str
    hint: str
    inputFormat: str
    outputFormat: str
    # ms
    timeLimit: int
    # KB
    memoryLimit: int
    remoteProblemID: str
    remoteOJ: str
    examples: List[ProblemExampleCase]
