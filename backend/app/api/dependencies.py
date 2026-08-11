from app.services import DashboardService, TaskService

task_service = TaskService()
dashboard_service = DashboardService()


def get_task_service() -> TaskService:
    return task_service


def get_dashboard_service() -> DashboardService:
    return dashboard_service
