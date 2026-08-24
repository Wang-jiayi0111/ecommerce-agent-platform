from app.domain import TaskPreviewRequest, TaskPreviewResponse
from app.modules.task_center import TaskInputDispatcher


class TaskPreviewService:
    """统一任务预解析入口；具体业务输入由 Dispatcher 分发。"""

    def __init__(self, dispatcher: TaskInputDispatcher) -> None:
        self.dispatcher = dispatcher

    def preview(self, payload: TaskPreviewRequest) -> TaskPreviewResponse:
        return self.dispatcher.preview(payload)


__all__ = ["TaskPreviewService"]
