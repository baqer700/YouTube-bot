import os
import asyncio
import requests
import smtplib
from email.message import EmailMessage
from openai import OpenAI
import edge_tts
from gradio_client import Client

# Configuration
MY_EMAIL = "baqerfazli4@gmail.com"
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

async def produce():
    print("--- PHASE 1: SCRIPT ---")
    try:
        client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Write one short viral motivation quote."}]
        )
        quote = resp.choices[0].message.content
        print(f"SUCCESS: {quote}")
    except Exception as e:
        print(f"CRITICAL ERROR (Script): {e}")
        return

    print("--- PHASE 2: IMAGE ---")
    try:
        hf = Client("black-forest-labs/FLUX.1-schnell", hf_token=HF_TOKEN)
        result = hf.predict(prompt=f"Cinematic, 4k, {quote}", api_name="/predict")
        import shutil
        img_temp_path = result[0] if isinstance(result, tuple) else result
        shutil.move(img_temp_path, "scene.jpg")
        print("SUCCESS: Image generated.")
    except Exception as e:
        print(f"CRITICAL ERROR (Image): {e}")
        return

    print("--- PHASE 3: AUDIO ---")
    try:
        await edge_tts.Communicate(quote, "en-US-ChristopherNeural").save("v.mp3")
        print("SUCCESS: Audio generated.")
    except Exception as e:
        print(f"CRITICAL ERROR (Audio): {e}")
        return

    print("--- PHASE 4: VIDEO RENDERING ---")
    # This is the heavy part
    cmd = "ffmpeg -y -loop 1 -i scene.jpg -i v.mp3 -vf 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920' -c:v libx264 -t 5 -pix_fmt yuv420p final.mp4"
    os.system(cmd)
    
    if not os.path.exists("final.mp4"):
        print("CRITICAL ERROR: FFmpeg failed to create final.mp4")
        return
    print("SUCCESS: Video rendered.")

    print("--- PHASE 5: EMAIL ---")
    try:
        msg = EmailMessage()
        msg['Subject'] = '🚀 YOUR AI VIDEO'
        msg['From'] = MY_EMAIL
        msg['To'] = MY_EMAIL
        with open("final.mp4", 'rb') as f:
            msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename='video.mp4')
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(MY_EMAIL, EMAIL_PASS)
            s.send_message(msg)
        print("🎉 SUCCESS: EVERYTHING DONE! Check your email.")
    except Exception as e:
        print(f"CRITICAL ERROR (Email): {e}")

if __name__ == "__main__":
    asyncio.run(produce())
    
