from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import httpx
import io
import logging
import requests

# ロギングの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VOICEVOX_URL = "http://localhost:50021"
TIMEOUT_SECONDS = 30.0

class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    speaker_id: int = Field(..., ge=0)
    volume_scale: float = Field(2.0, ge=0.5, le=10.0)
    speed_scale: float = Field(1.0, ge=0.5, le=2.0)
    pitch_scale: float = Field(0.0, ge=-0.15, le=0.15)
    intonation_scale: float = Field(0.0, ge=0.0, le=3.0)
    pre_phoneme_length: float = Field(0.1, ge=-5.0, le=5.0) 
    post_phoneme_length: float = Field(0.1, ge=0.0, le=5.0)  
    

    @validator('text')
    def text_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or only whitespace')
        return v

@app.post("/synthesis")
async def synthesize_speech(request: TextRequest):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            logger.info(f"Processing synthesis request for text: {request.text[:50]}...")
            
            # VOICEVOXサーバーの状態チェック
            try:
                health_check = await client.get(f"{VOICEVOX_URL}/version")
                if health_check.status_code != 200:
                    raise HTTPException(
                        status_code=503,
                        detail="VOICEVOX server is not responding properly"
                    )
            except httpx.RequestError:
                raise HTTPException(
                    status_code=503,
                    detail="Cannot connect to VOICEVOX server"
                )

            # 音声合成用のクエリを作成
            try:
                query_response = await client.post(
                    f"{VOICEVOX_URL}/audio_query",
                    params={
                        "text": request.text,
                        "speaker": request.speaker_id
                    }
                )
                query_response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Audio query failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate audio query: {str(e)}"
                )

            query_data = query_response.json()
            
            # パラメータの設定とログ出力
            logger.info(
                f"Synthesis parameters - Volume: {request.volume_scale}, "
                f"Speed: {request.speed_scale}, Pitch: {request.pitch_scale}, "
                f"Intonation: {request.intonation_scale}"
            )
            
            query_data.update({
                "volumeScale": request.volume_scale,
                "speedScale": request.speed_scale,
                "pitchScale": request.pitch_scale,
                "intonationScale": request.intonation_scale
            })
            
            # 音声合成を実行
            try:
                synthesis_response = await client.post(
                    f"{VOICEVOX_URL}/synthesis",
                    params={"speaker": request.speaker_id},
                    json=query_data
                )
                synthesis_response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Synthesis failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to synthesize audio: {str(e)}"
                )
            
            logger.info("Successfully synthesized audio")
            return StreamingResponse(
                io.BytesIO(synthesis_response.content),
                media_type="audio/wav"
            )
            
    except httpx.TimeoutException:
        logger.error("Request timed out")
        raise HTTPException(
            status_code=504,
            detail="Request timed out"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# def create_audio_query(self, text: str, speaker_id: int = 1, timeout: int = 10) -> Dict:
#     """音声合成用のクエリを作成します"""
#     params = {
#         "text": text,
#         "speaker": speaker_id
#     }

    
#     try:
#         response = requests.post(
#             f"{self.base_url}/audio_query",
#             params=params,
#             timeout=timeout
#         )
#         response.raise_for_status()
#         return response.json()
        
#     except requests.exceptions.RequestException as e:
#         raise Exception(f"クエリの作成に失敗しました: {str(e)}")

# @app.post("/generate_video")
# async def generate_video(json_list: list[TextRequest]):
#     try:
#         response_list = []
#         for item in json_list:
#             query_response = requests.post(
#                 f"{VOICEVOX_URL}/audio_query",
#                 params={"text": item.text, "speaker": item.speaker_id}
#             )
#             query_data = query_response.json()
            
#             query_data.update({
#                 "volumeScale": item.volume_scale,
#                 "speedScale": item.speed_scale,
#                 "pitchScale": item.pitch_scale,
#                 "intonationScale": item.intonation_scale,
#                 "prePhonemeLength": max(0.0, item.pre_phoneme_length),  # VOICEVOXには負の値を送らない
#                 "postPhonemeLength": item.post_phoneme_length
#             })
            
#             synthesis_response = requests.post(
#                 f"{VOICEVOX_URL}/synthesis",
#                 params={"speaker": item.speaker_id},
#                 json=query_data
#             )
#             response_list.append(AudioSegment.from_wav(io.BytesIO(synthesis_response.content)))

#         combined_audio = response_list[0]
#         for i, audio in enumerate(response_list[1:], 1):
#             if json_list[i].pre_phoneme_length < 0:
#                 overlap_ms = int(-json_list[i].pre_phoneme_length * 1000)
#                 position = len(combined_audio) - overlap_ms
#                 combined_audio = combined_audio.overlay(audio, position=position)
#             else:
#                 combined_audio += audio

#         buffer = io.BytesIO()
#         combined_audio.export(buffer, format="wav")
#         buffer.seek(0)
#         return StreamingResponse(buffer, media_type="audio/wav")

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# サーバー起動時の確認
@app.on_event("startup")
async def startup_event():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{VOICEVOX_URL}/version")
            if response.status_code == 200:
                logger.info("Successfully connected to VOICEVOX server")
            else:
                logger.warning("VOICEVOX server is not responding properly")
    except Exception as e:
        logger.error(f"Failed to connect to VOICEVOX server: {str(e)}")