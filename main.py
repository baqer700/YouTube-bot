import os
import asyncio
import requests
import smtplib
from email.message import EmailMessage
from openai import OpenAI
import edge_tts
from gradio_client import Client

# Config
MY_EMAIL = "baqerfazli4@gmail.com"
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

async def run_factory():
    print("--- EMPIRE BOT STARTED ---")
    
    # 1. TEXT GENERATION (DeepSeek)
    print("Task 1: Generating Text...")
    try:
        client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Write a 1-sentence viral motivation quote."}]
        )
        quote = resp.choices[0].message.content
    except Exception as e:
        print(f"DeepSeek Error: {e}")
        quote = "Do not stop until you are proud."

    # 2. IMAGE GENERATION (Hugging Face - FREE)
    print("Task 2: Generating Image...")
    try:
        hf = Client("black-forest-labs/FLUX.1-schnell", hf_token=HF_TOKEN)
        result = hf.predict(prompt=f"Cinematic, 4k, dark luxury, {quote}", api_name="/predict")
        import shutil
        image_path = result[0] if isinstance(result, tuple) else result
        shutil.move(image_path, "scene.jpg")
    except Exception as e:
        print(f"HF Error: {e}. Using fallback image.")
        r = requests.get("https://picsum.photos/1080/1920")
        with open("scene.jpg", "wb") as f: f.write(r.content)

    # 3. VOICE GENERATION
    print("Task 3: Generating Voice...")
    await edge_tts.Communicate(quote, "en-US-ChristopherNeural").save("v.mp3")

    # 4. VIDEO RENDERING (FFmpeg)
    print("Task 4: Rendering Video (This takes time)...")
    render_cmd = (
        "ffmpeg -y -loop 1 -i scene.jpg -i v.mp3 "
        "-vf 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920' "
        "-c:v libx264 -t 7 -pix_fmt yuv420p final.mp4"
    )
    os.system(render_cmd)

    # 5. DELIVERY (Always try Email first to ensure you see the result)
    if os.path.exists("final.mp4"):
        print("Task 5: Sending to Email...")
        try:
            msg = EmailMessage()
            msg['Subject'] = '🚀 SUCCESS: Your AI Video'
            msg['From'] = MY_EMAIL
            msg['To'] = MY_EMAIL
            msg.set_content(f"Production Complete!\nQuote: {quote}")
            with open("final.mp4", 'rb') as f:
                msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename="video.mp4")
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(MY_EMAIL, EMAIL_PASS)
                s.send_message(msg)
            print("--- ALL DONE! CHECK YOUR EMAIL ---")
        except Exception as e:
            print(f"Email Final Error: {e}")
    else:
        print("CRITICAL: Video file was never created.")

if __name__ == "__main__":
    asyncio.run(run_factory())
    
