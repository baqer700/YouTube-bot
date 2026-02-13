import os
import asyncio
import requests
import smtplib
from email.message import EmailMessage
from openai import OpenAI
import edge_tts
from gradio_client import Client

# --- CONFIG ---
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")
MY_EMAIL = "baqerfazli4@gmail.com"

async def produce_video():
    print("--- EMPIRE PRODUCTION STARTED ---")
    
    # 1. GENERATE TEXT (DeepSeek)
    print("Step 1: DeepSeek thinking...")
    client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Write a 1-sentence alpha male motivational quote."}]
        )
        quote = resp.choices[0].message.content
    except:
        quote = "Master your mind, master your life."
    print(f"Quote: {quote}")

    # 2. GENERATE IMAGE (HF - FLUX)
    print("Step 2: Hugging Face painting...")
    try:
        hf_client = Client("black-forest-labs/FLUX.1-schnell", hf_token=HF_TOKEN)
        result = hf_client.predict(prompt=f"Dark cinematic, luxury, 4k, {quote}", api_name="/predict")
        import shutil
        shutil.move(result[0] if isinstance(result, tuple) else result, "scene.jpg")
    except Exception as e:
        print(f"HF Error: {e}")
        r = requests.get("https://picsum.photos/1080/1920")
        with open("scene.jpg", "wb") as f: f.write(r.content)

    # 3. GENERATE VOICE (Edge-TTS)
    print("Step 3: Recording voice...")
    await edge_tts.Communicate(quote, "en-US-ChristopherNeural").save("v.mp3")

    # 4. RENDER VIDEO (FFmpeg)
    print("Step 4: Rendering video...")
    cmd = (
        "ffmpeg -y -loop 1 -i scene.jpg -i v.mp3 "
        "-vf \"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.001,1.5)':d=250:s=1080x1920\" "
        "-c:v libx264 -t 8 -pix_fmt yuv420p -shortest final.mp4"
    )
    os.system(cmd)

    # 5. SEND EMAIL
    if os.path.exists("final.mp4"):
        print("Step 5: Sending to Gmail...")
        msg = EmailMessage()
        msg['Subject'] = '🚀 Your AI Video is Ready!'
        msg['From'] = MY_EMAIL ; msg['To'] = MY_EMAIL
        with open("final.mp4", 'rb') as f:
            msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="video.mp4")
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(MY_EMAIL, EMAIL_PASS)
            s.send_message(msg)
        print("Done! Check your email.")

if __name__ == "__main__":
    asyncio.run(produce_video())
    
