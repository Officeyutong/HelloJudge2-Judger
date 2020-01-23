from dataclasses import dataclass, field
from typing import List
from typing import Dict


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


