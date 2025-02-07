import base64
import io
import os
from logging import getLogger

import httpx
import numpy as np
import soundfile as sf
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from ..models.requests import ManzaiRequest, TextRequest

router = APIRouter()
VOICEVOX_URL = "http://localhost:50021"
N_ROUND = 5  # 丸める桁数
logger = getLogger(__name__)


@router.post("/concat")
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
                    params={"text": voice.text, "speaker": voice.speaker_id},
                )

                query_data = query_response.json()
                pre_phoneme_length = (
                    0 if voice.pre_phoneme_length < 0 else voice.pre_phoneme_length
                )  # 最初の音声の開始無音がマイナスの場合、0に変換。
                query_data.update(
                    {
                        "volumeScale": voice.volume_scale,
                        "speedScale": voice.speed_scale,
                        "pitchScale": voice.pitch_scale,
                        "intonationScale": voice.intonation_scale,
                        "prePhonemeLength": pre_phoneme_length,
                        "postPhonemeLength": voice.post_phoneme_length,
                    }
                )

                synthesis_response = await client.post(
                    f"{VOICEVOX_URL}/synthesis",
                    params={"speaker": voice.speaker_id},
                    json=query_data,
                )

                # 音声データをNumPy配列として読み込む
                audio_buffer = io.BytesIO(synthesis_response.content)
                audio_data, _ = sf.read(audio_buffer)

                # 2つ目以降の音声で、前の音声との間隔を調整
                if i > 0:
                    if voice.pre_phoneme_length >= 0:
                        silence_length = int(
                            abs(voice.pre_phoneme_length) * sample_rate
                        )
                        silence = np.zeros(silence_length)
                        audio_arrays.append(silence)
                        current_position += len(silence) / sample_rate
                        processed_voice["start"] = round(current_position, N_ROUND)
                        processed_voice["end"] = round(
                            current_position + len(audio_data) / sample_rate, N_ROUND
                        )

                    elif voice.pre_phoneme_length < 0:
                        overlap_length = int(
                            abs(voice.pre_phoneme_length) * sample_rate
                        )
                        # 結合済み音声のデータ
                        concatenated_audio = np.concatenate(audio_arrays)
                        overlap_start = len(concatenated_audio) - overlap_length

                        # 新しい結合音声を作成
                        combined = np.zeros(overlap_start + len(audio_data))
                        combined[: len(concatenated_audio)] = (
                            concatenated_audio  # 前の音声を全て保持
                        )
                        combined[
                            overlap_start : overlap_start + len(audio_data)
                        ] += audio_data  # 新しい音声を加算（重ね合わせる）

                        # 時間情報を追加
                        start_time = overlap_start / sample_rate
                        processed_voice["start"] = round(start_time, N_ROUND)
                        processed_voice["end"] = round(
                            start_time + len(audio_data) / sample_rate, N_ROUND
                        )

                        audio_arrays = [combined]
                        current_position = len(combined) / sample_rate
                        processed_voices.append(processed_voice)
                        continue
                else:
                    processed_voice["start"] = 0
                    processed_voice["end"] = round(
                        len(audio_data) / sample_rate, N_ROUND
                    )
                    print(
                        f'start-end: {processed_voice["start"]}~{processed_voice["end"]}'
                    )
                    current_position = len(audio_data) / sample_rate

                audio_arrays.append(audio_data)
                processed_voices.append(processed_voice)
                print(f"音声{i+1}の処理完了")

        # 全ての音声データを結合
        print("全音声の結合")
        combined_audio = np.concatenate(audio_arrays)

        # 結合した音声データをバイナリに変換
        output_buffer = io.BytesIO()
        sf.write(output_buffer, combined_audio, sample_rate, format="WAV")
        output_buffer.seek(0)

        # ファイルを保存
        downloads_path = os.path.expanduser("~/Downloads")
        filename = f"{request.combi_name}_{request.title}.wav"
        filepath = os.path.join(downloads_path, filename)

        # WAVファイルとして保存
        sf.write(filepath, combined_audio, sample_rate)
        print(f"音声ファイルを保存しました: {filepath}")

        # レスポンスデータの作成
        response_data = {
            "title": request.title,
            "left_chara": request.left_chara,
            "right_chara": request.right_chara,
            "left_chara_path": request.left_chara_path,
            "right_chara_path": request.right_chara_path,
            "voices": processed_voices,
        }

        return JSONResponse(
            {
                "audio": base64.b64encode(output_buffer.getvalue()).decode("utf-8"),
                "script": response_data,
            }
        )

    except Exception as e:
        print(f"エラー発生: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/play_manzai_anime")
async def play_manzai_anime():
    logger.info("壊れました:this function has been broken.")
    pass


@router.post("/synthesis")
async def generate_vvox_audio(request: TextRequest):
    try:
        async with httpx.AsyncClient() as client:
            # 音声合成用のクエリを作成（基本パラメータのみ）
            query_response = await client.post(
                f"{VOICEVOX_URL}/audio_query",
                params={"text": request.text, "speaker": request.speaker_id},
            )

            if query_response.status_code != 200:
                raise HTTPException(
                    status_code=500, detail="Failed to generate audio query"
                )

            # クエリデータを取得して各パラメータを更新

            ## 開始無音がマイナス（重複）の場合は、開始無音を0secにする。
            pre_phoneme_length = (
                0 if request.pre_phoneme_length < 0 else request.pre_phoneme_length
            )
            query_data = query_response.json()
            query_data.update(
                {
                    "volumeScale": request.volume_scale,
                    "speedScale": request.speed_scale,
                    "pitchScale": request.pitch_scale,
                    "intonationScale": request.intonation_scale,
                    "prePhonemeLength": pre_phoneme_length,
                    "postPhonemeLength": request.post_phoneme_length,
                }
            )

            # 更新したパラメータで音声合成を実行
            synthesis_response = await client.post(
                f"{VOICEVOX_URL}/synthesis",
                params={"speaker": request.speaker_id},
                json=query_data,
            )

            if synthesis_response.status_code != 200:
                raise HTTPException(
                    status_code=500, detail="Failed to synthesize audio"
                )
            audio_data = io.BytesIO(synthesis_response.content)

            return StreamingResponse(audio_data, media_type="audio/wav")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
