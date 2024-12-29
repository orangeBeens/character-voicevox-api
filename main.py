from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware  # 追加
from pydantic import BaseModel
import httpx
import io

app = FastAPI()

# CORSミドルウェアの設定を追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発時は全てのオリジンを許可
    allow_credentials=True,
    allow_methods=["*"],  # 全てのメソッドを許可
    allow_headers=["*"],  # 全てのヘッダーを許可
)

# 以下は既存のコード
VOICEVOX_URL = "http://localhost:50021"

class TextRequest(BaseModel):
    text: str
    speaker_id: int

@app.post("/synthesis")
async def synthesize_speech(request: TextRequest):
    try:
        async with httpx.AsyncClient() as client:
            # 音声合成用のクエリを作成
            query_response = await client.post(
                f"{VOICEVOX_URL}/audio_query",
                params={
                    "text": request.text,
                    "speaker": request.speaker_id
                }
            )
            
            if query_response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to generate audio query"
                )
            
            query_data = query_response.json()
            
            # 音声合成を実行
            synthesis_response = await client.post(
                f"{VOICEVOX_URL}/synthesis",
                params={"speaker": request.speaker_id},
                json=query_data
            )
            
            if synthesis_response.status_code != 200:
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to synthesize audio"
                )
            
            # 音声データをStreamingResponseとして返す
            return StreamingResponse(
                io.BytesIO(synthesis_response.content),
                media_type="audio/wav"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))