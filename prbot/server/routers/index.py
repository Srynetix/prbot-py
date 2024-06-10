from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def index() -> dict[str, Any]:
    return {"message": "Welcome on prbot!"}
