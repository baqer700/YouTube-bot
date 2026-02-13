import os
import asyncio
import requests
import smtplib
import json
from email.message import EmailMessage
from openai import OpenAI
import edge_tts
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# --- SYSTEM CONFIGURATION ---
SHORTAPI_KEY = os.getenv("SHORTAPI_KEY")       
HF_TOKEN = os.getenv("HF_TOKEN")               
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD") 
YT_TOKEN = os.getenv("YOUTUBE_TOKEN")
YT_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
MY_EMAIL = "baqerfazli4@gmail.com"

class EmpireFactory:
    def __init__(self):
        self.video_path = "final_output.mp4"
        self.img_path = "frame.jpg"
        self.audio_path = "voice.mp3"
        # Using ShortAPI as the primary hub for everything
        self.ai_client = OpenAI(api_key=SHORTAPI_KEY, base_url="https://api.shortapi.ai/v1")

    async def get_script(self):
        print("[PROCESS] STEP 1: GENERATING SCRIPT...")
        try:
            # Attempting to use your 0.5$ credit for GPT-4o
            resp = self.ai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Write a 15-second viral motivation about hard work."}]
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"[LOG] API Balance issue or error: {e}. Using offline fallback.")
            return "Your hard work will pay off. Keep building your empire with AI."

    def get_visuals(self, prompt):
        print("[PROCESS] STEP 2: CREATING VISUALS...")
        try:
            # Try Premium first
            res = self.ai_client.images.generate(model="flux-pro", prompt=f"Cinematic 8k, {prompt[:100]}")
            with open(self.img_path, "wb") as f:
                f.write(requests.get(res.data[0].url).content)
            return True
        except:
            print("[LOG] ShortAPI failed. Moving to Hugging Face Free tier...")
            try:
                from gradio_client import Client
                hf = Client("black-forest-labs/FLUX.1-schnell", hf_token=HF_TOKEN)
                result = hf.predict(prompt=prompt, api_name="/predict")
                import shutil
                shutil.move(result[0] if isinstance(result, tuple) else result, self.img_path)
                return True
            except:
                print("[LOG] All image APIs failed. Downloading stock image...")
                with open(self.img_path, "wb") as f:
                    f.write(requests.get("https://picsum.photos/1080/1920").content)
                return True

    async def make_audio(self, text):
        print("[PROCESS] STEP 3: RECORDING VOICE...")
        comm = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        await comm.save(self.audio_path)

    def assemble_ffmpeg(self):
        print("[PROCESS] STEP 4: FFMPEG ASSEMBLY...")
        music_url = "https://cdn.pixabay.com/download/audio/2022/11/22/audio_feb3767253.mp3"
        with open("bg.mp3", "wb") as f: f.write(requests.get(music_url).content)
        
        cmd = (
            f"ffmpeg -y -loop 1 -i {self.img_path} -i {self.audio_path} -i bg.mp3 "
            f"-filter_complex \"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0015,1.5)':d=400:s=1080x1920[v];"
            f"[2:a]volume=0.15[m];[1:a][m]amix=inputs=2:duration=first[a]\" "
            f"-map \"[v]\" -map \"[a]\" -c:v libx264 -t 15 -pix_fmt yuv420p {self.video_path}"
        )
        os.system(cmd)
        return os.path.exists(self.video_path)

    def upload_youtube(self):
        print("[PROCESS] STEP 5: YOUTUBE UPLOAD...")
        if not YT_TOKEN: return False
        try:
            creds = Credentials(token=YT_TOKEN, client_id=YT_CLIENT_ID)
            yt = build("youtube", "v3", credentials=creds)
            yt.videos().insert(
                part="snippet,status",
                body={"snippet": {"title": "AI Empire #Shorts", "categoryId": "22"}, "status": {"privacyStatus": "public"}},
                media_body=MediaFileUpload(self.video_path)
            ).execute()
            print("[SUCCESS] LIVE ON YOUTUBE!")
            return True
        except: return False

    def send_email_fallback(self):
        print("[PROCESS] STEP 6: EMAIL FALLBACK...")
        msg = EmailMessage()
        msg['Subject'] = '🚀 Production Complete: Your AI Video'
        msg['From'] = MY_EMAIL
        msg['To'] = MY_EMAIL
        msg.set_content("YouTube upload failed or skipped. Video is attached below.")
        with open(self.video_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="empire_video.mp4")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(MY_EMAIL, EMAIL_PASS)
            s.send_message(msg)
        print("[SUCCESS] SENT TO baqerfazli4@gmail.com")

async def run():
    bot = EmpireFactory()
    script = await bot.get_script()
    if bot.get_visuals(script):
        await bot.make_audio(script)
        if bot.assemble_ffmpeg():
            if not bot.upload_youtube():
                bot.send_email_fallback()

if __name__ == "__main__":
    asyncio.run(run())
    
