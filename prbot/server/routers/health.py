from typing import Any

from fastapi import APIRouter

from prbot.injection import inject_instance
from prbot.modules.lock import LockClient

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    lock = inject_instance(LockClient)

    try:
        await lock.ping()
        lock_ok = True
    except Exception:
        lock_ok = False

    return {"database": True, "lock": lock_ok}
