from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import manzai, scripts, synthesis

app = FastAPI()

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# プレフィックスなしでルーターを登録
app.include_router(scripts.router)
app.include_router(manzai.router)
app.include_router(synthesis.router)

# または、APIプレフィックスを付ける場合は以下のように設定
# app.include_router(scripts.router, prefix="/api")
# app.include_router(manzai.router, prefix="/api")
# app.include_router(synthesis.router, prefix="/api")
