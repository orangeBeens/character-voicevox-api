from typing import Dict
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip

class ManzaiVideoGenerator:
    def __init__(self, script_data: Dict, audio_path: str = "output_concat.wav"):
        self.script_data = script_data
        self.voices = script_data["voices"]
        self.audio_path = audio_path
        self.width = 800
        self.height = 600
        
        # 最後の音声のendを取得して動画の長さを決定
        self.duration = max(voice["end"] for voice in self.voices)

    def create_character_frame(self, is_left_speaking: bool, is_right_speaking: bool) -> np.ndarray:
        """キャラクターフレームを生成"""
        img = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # キャラクター位置
        left_x, right_x = 50, 550
        base_y = 250
        
        # キャラクターのサイズ
        char_width, char_height = 200, 300
        
        # 左キャラクター描画
        left_color = (100, 100, 255) if is_left_speaking else (50, 50, 127)
        draw.rectangle([(left_x, base_y), (left_x + char_width, base_y + char_height)], 
                      fill=left_color)
        
        # 右キャラクター描画
        right_color = (255, 100, 100) if is_right_speaking else (127, 50, 50)
        draw.rectangle([(right_x, base_y), (right_x + char_width, base_y + char_height)], 
                      fill=right_color)
        
        return np.array(img)

    def make_frame(self, t: float) -> np.ndarray:
        """各時間のフレームを生成"""
        # 現在の音声を特定
        current_voice = None
        for voice in self.voices:
            if voice["start"] <= t <= voice["end"]:
                current_voice = voice
                break
        
        # 発話状態を判定
        is_left_speaking = current_voice and current_voice["characterType"] == "left"
        is_right_speaking = current_voice and current_voice["characterType"] == "right"
        
        # フレーム生成
        frame = self.create_character_frame(is_left_speaking, is_right_speaking)
        
        # テキスト表示があれば追加
        if current_voice:
            img = Image.fromarray(frame)
            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
            
            text = current_voice["text"]
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # テキスト位置計算
            if current_voice["characterType"] == "left":
                text_x = 200
                text_y = 200
            else:
                text_x = 600 - text_width
                text_y = 200
            
            # 吹き出し背景
            padding = 10
            draw.rectangle([
                (text_x - padding, text_y - padding),
                (text_x + text_width + padding, text_y + text_height + padding)
            ], fill=(255, 255, 255), outline=(0, 0, 0))
            
            # テキスト描画
            draw.text((text_x, text_y), text, font=font, fill=(0, 0, 0))
            frame = np.array(img)
        
        return frame

    def generate_video(self, output_path: str = "output_manzai.mp4") -> str:
        """動画を生成"""
        print("generate_video:in")
        # 音声クリップの読み込み
        print(f"audio_path:{self.audio_path}")
        audio = AudioFileClip(self.audio_path)
        print(f"audio:{audio}")
        
        # 動画クリップの作成
        video = VideoFileClip(None, audio=False).set_duration(self.duration)
        video = video.set_make_frame(self.make_frame)
        
        # 音声と動画を結合
        final_clip = video.set_audio(audio)
        
        # mp4として出力
        final_clip.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac'
        )
        
        # クリップを閉じる
        final_clip.close()
        audio.close()
        
        return output_path

    @classmethod
    def generate(cls, script_data: Dict, audio_path: str = "output_concat.wav", 
                output_path: str = "output_manzai.mp4") -> str:
        """動画生成の実行メソッド"""
        generator = cls(script_data, audio_path)
        return generator.generate_video(output_path)