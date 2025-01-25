import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # プロジェクトのルートパスを動的に計算
    PROJECT_ROOT: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../")  # .envの読み込み
    )
    VOICEVOX_URL: str = "http://localhost:50021"
    SCRIPT_DIR: str | None = None

    @property
    def computed_script_dir(self):
        if not self.SCRIPT_DIR:
            self.SCRIPT_DIR = os.path.join(
                self.PROJECT_ROOT, "assets", "manzai_scripts"
            )
        return self.SCRIPT_DIR

    class Config:
        env_file = ".env"  # ルートディレクトリからの相対パス
        env_file_encoding = "utf-8"


settings = Settings()
