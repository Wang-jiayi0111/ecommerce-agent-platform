from typing import Protocol

from app.domain import TaskCreate, TaskError, TaskPreviewRequest, TaskPreviewResponse


class TaskInputValidationError(ValueError):
    def __init__(self, error: TaskError) -> None:
        super().__init__(error.message)
        self.error = error


class TaskInputExtractor(Protocol):
    def preview(self, payload: TaskPreviewRequest) -> TaskPreviewResponse: ...

    def validate_task(self, payload: TaskCreate) -> None: ...


class TaskInputDispatcher:
    """按 intent 选择输入提取器，并复用同一规则校验正式任务。"""

    def __init__(self, extractors: dict[str, TaskInputExtractor]) -> None:
        self.extractors = dict(extractors)

    def preview(self, payload: TaskPreviewRequest) -> TaskPreviewResponse:
        extractor = self.extractors.get(payload.intent)
        if extractor is None:
            raise TaskInputValidationError(
                TaskError(
                    code="PREVIEW_INTENT_NOT_SUPPORTED",
                    message=f"Preview does not support intent: {payload.intent}.",
                    step="preview",
                    details={"intent": payload.intent},
                )
            )
        return extractor.preview(payload)

    def validate_task(self, payload: TaskCreate) -> None:
        extractor = self.extractors.get(payload.intent)
        if extractor is not None:
            extractor.validate_task(payload)


__all__ = [
    "TaskInputDispatcher",
    "TaskInputExtractor",
    "TaskInputValidationError",
]
