from app.composition import build_application_container
from app.core.config import settings
from app.db import SessionFactory, init_database
from app.services import DashboardService, TaskPreviewService, TaskService

if settings.auto_create_schema and settings.environment.lower() not in {"production", "prod"}:
    init_database()

container = build_application_container(settings, SessionFactory)


def get_task_service() -> TaskService:
    return container.task_service


def get_task_preview_service() -> TaskPreviewService:
    return container.task_preview_service


def get_dashboard_service() -> DashboardService:
    return container.dashboard_service
