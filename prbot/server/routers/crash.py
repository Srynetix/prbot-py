from fastapi import APIRouter, Response

router = APIRouter()


@router.get("/crash")
async def crash() -> Response:
    raise RuntimeError("A wild crash appeared!")
