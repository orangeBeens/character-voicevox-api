from fastapi import Request
from fastapi.responses import JSONResponse

from .errors import VoiceVoxError


def setup_exception_handlers(app):
    @app.exception_handler(VoiceVoxError)
    async def voicevox_exception_handler(request: Request, exc: VoiceVoxError):
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message}
        )
