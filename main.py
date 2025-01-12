from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from manzai.player import ManzaiVideoGenerator
from pydantic import BaseModel, Field
from typing import List
import httpx
import io
import sounddevice as sd
import soundfile as sf
import numpy as np
import base64

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VOICEVOX_URL = "http://localhost:50021"
N_ROUND = 5 #丸める桁数


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    speaker_id: int = Field(..., ge=0)
    volume_scale: float = Field(2.0, ge=0.5, le=10.0)
    speed_scale: float = Field(1.0, ge=0.5, le=2.0)
    pitch_scale: float = Field(0.0, ge=-0.15, le=0.15)
    intonation_scale: float = Field(0.0, ge=0.0, le=3.0)
    pre_phoneme_length: float = Field(0.1, ge=-5.0, le=5.0)
    post_phoneme_length: float = Field(0.0, ge=0.0, le=5.0)

class ManzaiRequest(BaseModel):
    title:str
    left_chara:str #キャラ名
    right_chara:str
    left_chara_path:str #キャラの画像パス
    right_chara_path:str
    voices: List[TextRequest]

def debug_play(audio_binary: bytes):
    """デバッグ用の音声再生関数"""
    try:
        # バイナリデータをメモリ上のバッファに変換
        audio_buffer = io.BytesIO(audio_binary)
    
        # soundfileで読み込み
        data, samplerate = sf.read(audio_buffer)
        
        print(f"音声データ情報:")
        print(f"- サンプルレート: {samplerate}Hz")
        print(f"- データ形状: {data.shape}")
        print(f"- データタイプ: {data.dtype}")
        print(f"- 再生時間: {len(data)/samplerate:.2f}秒")
        print("")
        
        # 音声を再生
        sd.play(data, samplerate)
        sd.wait()  # 再生完了まで待機
        
        return True
        
    except Exception as e:
        print(f"デバッグ再生でエラーが発生: {str(e)}\n")
        return False

@app.post("/synthesis")
async def generate_vvox_audio(request: TextRequest):
    try:
        async with httpx.AsyncClient() as client:
            # 音声合成用のクエリを作成（基本パラメータのみ）
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
            
            # クエリデータを取得して各パラメータを更新

            ## 開始無音がマイナス（重複）の場合は、開始無音を0secにする。
            pre_phoneme_length = 0 if request.pre_phoneme_length < 0  else request.pre_phoneme_length
            query_data = query_response.json()
            query_data.update({
                "volumeScale": request.volume_scale,
                "speedScale": request.speed_scale,
                "pitchScale": request.pitch_scale,
                "intonationScale": request.intonation_scale,
                "prePhonemeLength": pre_phoneme_length,
                "postPhonemeLength": request.post_phoneme_length
            })
            
            
            # 更新したパラメータで音声合成を実行
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
            audio_data = io.BytesIO(synthesis_response.content)



            return StreamingResponse(
                io.BytesIO(synthesis_response.content),
                media_type="audio/wav"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/concat")
async def concat_vvox_audio(request: ManzaiRequest):
    """漫才の音声を作成する"""
    print("開始: concat_vvox_audio")
    try:
        audio_arrays = []  # NumPy配列として音声データを保持
        sample_rate = 24000
        current_position = 0  # 現在の位置（秒）
        processed_voices = []  # 時間情報を追加した音声データを保存
        
        async with httpx.AsyncClient() as client:
            for i, voice in enumerate(request.voices):
                print(f"音声{i+1}の処理開始")
                
                # voice辞書をコピーして新しい辞書を作成
                processed_voice = dict(voice)
                
                query_response = await client.post(
                    f"{VOICEVOX_URL}/audio_query",
                    params={"text": voice.text, "speaker": voice.speaker_id}
                )
                
                query_data = query_response.json()
                pre_phoneme_length = 0 if voice.pre_phoneme_length < 0  else voice.pre_phoneme_length #最初の音声の開始無音がマイナスの場合、0に変換。
                query_data.update({
                    "volumeScale": voice.volume_scale,
                    "speedScale": voice.speed_scale,
                    "pitchScale": voice.pitch_scale,
                    "intonationScale": voice.intonation_scale,
                    "prePhonemeLength": pre_phoneme_length,
                    "postPhonemeLength": voice.post_phoneme_length
                })
                
                synthesis_response = await client.post(
                    f"{VOICEVOX_URL}/synthesis",
                    params={"speaker": voice.speaker_id},
                    json=query_data
                )

                # 音声データをNumPy配列として読み込む
                audio_buffer = io.BytesIO(synthesis_response.content)
                audio_data, _ = sf.read(audio_buffer)

                # 2つ目以降の音声で、前の音声との間隔を調整
                if i > 0:
                    if voice.pre_phoneme_length >= 0:
                        silence_length = int(abs(voice.pre_phoneme_length) * sample_rate)
                        silence = np.zeros(silence_length)
                        audio_arrays.append(silence)
                        current_position += len(silence) / sample_rate
                        processed_voice["start"] = round(current_position, N_ROUND)
                        processed_voice["end"] = round(current_position + len(audio_data) / sample_rate, N_ROUND)
                        
                    elif voice.pre_phoneme_length < 0:
                        overlap_length = int(abs(voice.pre_phoneme_length) * sample_rate)
                        # 結合済み音声のデータ
                        concatenated_audio = np.concatenate(audio_arrays)
                        overlap_start = len(concatenated_audio) - overlap_length

                        # 新しい結合音声を作成
                        combined = np.zeros(overlap_start + len(audio_data))
                        combined[:len(concatenated_audio)] = concatenated_audio  # 前の音声を全て保持
                        combined[overlap_start:overlap_start + len(audio_data)] += audio_data  # 新しい音声を加算（重ね合わせる）
                        
                        # 時間情報を追加
                        start_time = overlap_start / sample_rate
                        processed_voice["start"] = round(start_time, N_ROUND)
                        processed_voice["end"] = round(start_time + len(audio_data) / sample_rate, N_ROUND)
                        
                        audio_arrays = [combined]
                        current_position = len(combined) / sample_rate
                        processed_voices.append(processed_voice)
                        continue
                else:
                    processed_voice["start"] = 0
                    processed_voice["end"] = round(len(audio_data) / sample_rate, N_ROUND)
                    print(f'start-end: {processed_voice["start"]}~{processed_voice["end"]}')
                    current_position = len(audio_data) / sample_rate
                
                audio_arrays.append(audio_data)
                processed_voices.append(processed_voice)
                print(f"音声{i+1}の処理完了")

        # 全ての音声データを結合
        print("全音声の結合")
        combined_audio = np.concatenate(audio_arrays)
        
        # 結合した音声データをバイナリに変換
        output_buffer = io.BytesIO()
        sf.write(output_buffer, combined_audio, sample_rate, format='WAV')
        output_buffer.seek(0)
        
        # レスポンスデータの作成
        response_data = {
            "title": request.title,
            "left_chara": request.left_chara,
            "right_chara": request.right_chara,
            "left_chara_path": request.left_chara_path,
            "right_chara_path": request.right_chara_path,
            "voices": processed_voices
        }
        
        return JSONResponse({
            "audio": base64.b64encode(output_buffer.getvalue()).decode('utf-8'),
            "script": response_data
        })

    except Exception as e:
        print(f"エラー発生: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/play_manzai_anime")
async def play_manzai_anime(script_data: dict):
    """漫才アニメーションを再生するエンドポイント"""
    ManzaiVideoGenerator.generate(
        script_data=script_data,
        audio_path="output_script.wav"
    )
    return JSONResponse({"status": "Animation saved"})