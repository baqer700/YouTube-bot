import os
import asyncio
import requests
import smtplib
from email.message import EmailMessage
from openai import OpenAI
import edge_tts
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# --- LOAD SECRETS FROM GITHUB ---
SHORTAPI_KEY = os.getenv("SHORTAPI_KEY")       
HF_TOKEN = os.getenv("HF_TOKEN")               
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD") 
YT_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YT_TOKEN = os.getenv("YOUTUBE_TOKEN")
MY_EMAIL = "baqerfazli4@gmail.com"

class UltimateEmpireBot:
    def __init__(self):
        self.video_file = "final_viral_video.mp4"
        self.audio_file = "voice.mp3"
        self.image_file = "scene.jpg"

    async def generate_story(self):
        print("[!] CONSULTING DEEPSEEK AI...")
        client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Create a high-energy 15-second script about the future of AI."}]
        )
        return response.choices[0].message.content

    def create_visuals(self, prompt):
        print("[!] GENERATING CINEMATIC VISUALS...")
        try:
            # Try ShortAPI first (Premium)
            s_client = OpenAI(base_url="https://api.shortapi.ai/v1", api_key=SHORTAPI_KEY)
            res = s_client.images.generate(model="flux-pro", prompt=f"Hyper-realistic, 8k, cinematic: {prompt[:100]}")
            img_data = requests.get(res.data[0].url).content
            with open(self.image_file, "wb") as f: f.write(img_data)
        except:
            print("[#] SHORTAPI FAILED. SWITCHING TO HUGGING FACE...")
            # Backup: Hugging Face (Free)
            from gradio_client import Client
            hf = Client("black_forest_labs/FLUX.1-schnell", hf_token=HF_TOKEN)
            result = hf.predict(prompt=prompt, api_name="/predict")
            import shutil
            shutil.move(result[0] if isinstance(result, tuple) else result, self.image_file)

    async def create_voice(self, text):
        print("[!] RECORDING AI VOICE...")
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        await communicate.save(self.audio_file)

    def build_video(self):
        print("[!] ASSEMBLING MASTERPIECE WITH FFMPEG...")
        # Music URL (Royalty Free)
        music_url = "https://www.bensound.com/bensound-music/bensound-epic.mp3"
        with open("bg_music.mp3", "wb") as f: f.write(requests.get(music_url).content)

        cmd = (
            f"ffmpeg -y -loop 1 -i {self.image_file} -i {self.audio_file} -i bg_music.mp3 "
            f"-filter_complex \"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0015,1.5)':d=300:s=1080x1920[v];"
            f"[2:a]volume=0.1[m];[1:a][m]amix=inputs=2:duration=first[a]\" "
            f"-map \"[v]\" -map \"[a]\" -c:v libx264 -t 15 -pix_fmt yuv420p {self.video_file}"
        )
        os.system(cmd)
        return os.path.exists(self.video_file)

    def upload_to_youtube(self):
        print("[!] ATTEMPTING YOUTUBE UPLOAD...")
        try:
            # Use your saved token from GitHub Secrets
            creds = Credentials(token=YT_TOKEN, client_id=YT_CLIENT_ID)
            youtube = build("youtube", "v3", credentials=creds)
            
            request = youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {"title": "AI Revolution #Shorts", "description": "Made by Baqer Empire Bot", "categoryId": "27"},
                    "status": {"privacyStatus": "public"}
                },
                media_body=MediaFileUpload(self.video_file, chunksize=-1, resumable=True)
            )
            request.execute()
            print(">>> SUCCESS: VIDEO IS LIVE ON YOUTUBE!")
            return True
        except Exception as e:
            print(f">>> YOUTUBE UPLOAD FAILED: {e}")
            return False

    def email_backup(self):
        print("[!] SENDING TO EMAIL AS BACKUP...")
        msg = EmailMessage()
        msg['Subject'] = '🚀 Empire Video Ready (YouTube Upload Failed/Skipped)'
        msg['From'] = MY_EMAIL
        msg['To'] = MY_EMAIL
        msg.set_content("The YouTube upload failed, but your video is ready here.")
        
        with open(self.video_file, 'rb') as f:
            msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename=self.video_file)
            
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(MY_EMAIL, EMAIL_PASS)
            s.send_message(msg)
        print(">>> SUCCESS: VIDEO SENT TO GMAIL!")

async def run_empire():
    bot = UltimateEmpireBot()
    script = await bot.generate_story()
    bot.create_visuals(script)
    await bot.create_voice(script)
    if bot.build_video():
        if not bot.upload_to_youtube():
            bot.email_backup()

if __name__ == "__main__":
    asyncio.run(run_empire())
    
