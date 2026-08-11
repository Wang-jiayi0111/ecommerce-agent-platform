from typing import Protocol

from app.domain import Recommendation, TaskCreate


class SpecialistAgent(Protocol):
    name: str

    def recommend(self, task: TaskCreate) -> Recommendation: ...
