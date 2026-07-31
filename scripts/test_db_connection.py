import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.core.database import check_database_connection


async def main() -> None:
    settings = get_settings()
    print(f"Testing database connection to: {settings.database_url}")
    await check_database_connection()
    print("Database connection successful.")


if __name__ == "__main__":
    asyncio.run(main())
