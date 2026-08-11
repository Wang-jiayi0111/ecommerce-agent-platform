from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_task_service
from app.domain import AgentTask
from app.services import TaskService

router = APIRouter(prefix="/approvals", tags=["审批"])
TaskServiceDependency = Annotated[TaskService, Depends(get_task_service)]


@router.post("/{task_id}/approve", response_model=AgentTask)
def approve(task_id: str, service: TaskServiceDependency) -> AgentTask:
    try:
        return service.approve(task_id)
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{task_id}/reject", response_model=AgentTask)
def reject(task_id: str, service: TaskServiceDependency) -> AgentTask:
    try:
        return service.reject(task_id)
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
