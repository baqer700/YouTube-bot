import os
import asyncio
import requests
import smtplib
from email.message import EmailMessage
from openai import OpenAI
import edge_tts
from gradio_client import Client

# تنظیمات
MY_EMAIL = "baqerfazli4@gmail.com"
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

async def main():
    print("--- STARTING PRODUCTION ---")
    
    # 1. تولید متن با دیپسیک
    print("Generating story with DeepSeek...")
    client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Write a 1-sentence viral motivation quote."}]
        )
        quote = resp.choices[0].message.content
    except:
        quote = "Success starts with self-discipline."
    
    # 2. تولید عکس با FLUX (رایگان در Hugging Face)
    print("Generating image with FLUX...")
    try:
        hf = Client("black-forest-labs/FLUX.1-schnell", hf_token=HF_TOKEN)
        result = hf.predict(prompt=f"Cinematic, 4k, dark luxury, {quote}", api_name="/predict")
        import shutil
        shutil.move(result[0] if isinstance(result, tuple) else result, "scene.jpg")
    except:
        r = requests.get("https://picsum.photos/1080/1920")
        with open("scene.jpg", "wb") as f: f.write(r.content)

    # 3. تولید صدا
    print("Generating voice...")
    await edge_tts.Communicate(quote, "en-US-ChristopherNeural").save("v.mp3")

    # 4. رندر ویدیو (FFmpeg)
    print("Rendering video (Please wait)...")
    os.system("ffmpeg -y -loop 1 -i scene.jpg -i v.mp3 -vf 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920' -c:v libx264 -t 7 -pix_fmt yuv420p final.mp4")

    # 5. ارسال ایمیل (رفع خطای ۵۳۵)
    if os.path.exists("final.mp4"):
        print("Sending to Email...")
        try:
            msg = EmailMessage()
            msg['Subject'] = '🚀 AI Video Ready!'
            msg['From'] = MY_EMAIL
            msg['To'] = MY_EMAIL
            msg.set_content(f"Script: {quote}")
            with open("final.mp4", 'rb') as f:
                msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="video.mp4")
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(MY_EMAIL, EMAIL_PASS)
                s.send_message(msg)
            print("SUCCESS: Check your inbox!")
        except Exception as e:
            print(f"EMAIL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
    
