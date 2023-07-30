
from typing import Callable

class Achievement:
    def __init__(self, name: str, category: str, filename: str, condition: Callable) -> None:
        self.name      = name
        self.category  = category
        self.filename  = filename
        self.condition = condition

    def __repr__(self) -> str:
        return f'[{self.category}] {self.name}'

    def check(self, score) -> bool:
        return self.condition(score)
