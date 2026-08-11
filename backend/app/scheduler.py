"""经营节奏任务入口：晨报、午间监控、晚间回读与观察窗复盘。"""

from app.core import settings


def main() -> None:
    print(f"scheduler initialized for {settings.environment}")


if __name__ == "__main__":
    main()
