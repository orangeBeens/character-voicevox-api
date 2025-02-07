from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import manzai, scripts
from app.core.handlers import setup_exception_handlers

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# エラーハンドラーの設定
setup_exception_handlers(app)

# ルーターの登録
app.include_router(manzai.router, prefix="/manzai", tags=["manzai"])
app.include_router(scripts.router, prefix="/scripts", tags=["scripts"])
