from fastapi import APIRouter

router = APIRouter()


@router.post("/synthesis")
async def generate_vvox_audio():
    pass
