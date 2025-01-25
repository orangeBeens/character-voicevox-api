import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ...core.config import settings

router = APIRouter()


@router.post("/save_manzai_script")
async def save_manzai_script(script_data: dict):
    try:
        # 既存のsave_manzai_scriptと同様の処理
        sanitized_title = script_data.get("title", "untitled").replace("/", "_")
        sanitized_combi = script_data.get("combi_name", "unknown").replace("/", "_")
        filename = f"{sanitized_title}_{sanitized_combi}.json"

        script_dir = settings.computed_script_dir
        if script_dir is None:
            raise HTTPException(
                status_code=500, detail="Script directory is not configured"
            )

        if not os.path.exists(script_dir):
            os.makedirs(script_dir)

        filepath = os.path.join(script_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)

        return JSONResponse(
            content={"message": "Script saved successfully", "filename": filename}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/get_manzai_scripts")
async def get_manzai_scripts():
    try:
        script_dir = settings.computed_script_dir
        if script_dir is None:
            raise HTTPException(
                status_code=500, detail="Script directory is not configured"
            )

        # ディレクトリが存在しない場合は作成して空のリストを返す
        if not os.path.exists(script_dir):
            os.makedirs(script_dir)
            return JSONResponse(content=[])

        # JSONファイルを探してロード
        scripts = []
        for filename in os.listdir(script_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(script_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        script_data = json.load(f)
                        scripts.append(script_data)
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
                    continue

        return JSONResponse(content=scripts)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
