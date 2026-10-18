"""What a route asks for.

Keeping this in one place means a test can swap the store for an in-memory one
without touching a route.
"""

from duewright import config
from duewright.service import TaskService


def get_service() -> TaskService:
    """Return the service over whatever the settings say."""
    return TaskService(config.make_repository())
