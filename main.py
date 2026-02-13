import os
import asyncio
import shutil
import subprocess
import smtplib
from email.message import EmailMessage
from groq import Groq
import edge_tts
from gradio_client import Client

# Configuration from GitHub Secrets
MY_EMAIL = "baqerfazli4@gmail.com"
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # ← این secret رو اضافه کردی
HF_TOKEN = os.getenv("HF_TOKEN")

# File paths
IMAGE_PATH = "scene.jpg"
VIDEO_CLIP_PATH = "animated_clip.mp4"
AUDIO_PATH = "voice.mp3"
FINAL_VIDEO = "final_video.mp4"
MUSIC_PATH = "sample_music.mp3"  # فایل موسیقی رو در repo بگذار

PROMPT_QUOTE = (
    "Write one short, powerful, viral motivational quote in English "
    "(15-25 words) with a luxury, nighttime, neon city or supercar theme."
)

def generate_content():
    client = Groq(api_key=GROQ_API_KEY)

    resp = client.chat.completions.create(
        model="llama-3.1-70b-versatile",  # مدل قوی و رایگان در Groq
        messages=[{"role": "user", "content": PROMPT_QUOTE}],
        max_tokens=60,
        temperature=0.85
    )
    quote = resp.choices[0].message.content.strip()
    print(f"Generated quote: {quote}")

    img_prompt = (
        f"high-end cinematic vertical 9:16, matte black luxury supercar driving through neon-lit city at night, "
        f"moody dark atmosphere, sharp rim lighting, deep shadows, gold blue accents, ultra-realistic, 8k, "
        f"35mm lens, motivational vibe, subtle text overlay: '{quote}'"
    )

    return quote, img_prompt


async def generate_image(img_prompt):
    space = "black-forest-labs/FLUX.1-schnell"
    try:
        hf = Client(space, hf_token=HF_TOKEN or None)
        print(f"Generating image with {space} ... (may queue)")
        result = hf.predict(
            prompt=img_prompt,
            width=1080,
            height=1920,
            num_inference_steps=4,
            seed=42,
            api_name="/infer"
        )
        temp_path = result[0] if isinstance(result, (list, tuple)) else result
        if not os.path.exists(temp_path):
            raise FileNotFoundError("Image file not created")
        shutil.move(temp_path, IMAGE_PATH)
        print(f"Image saved: {IMAGE_PATH}")
        return True
    except Exception as e:
        print(f"Image generation error: {str(e)}")
        return False


async def animate_to_video():
    space_id = "multimodalart/stable-video-diffusion"
    try:
        hf = Client(space_id, hf_token=HF_TOKEN or None)
        print(f"Animating with {space_id} ...")
        result = hf.predict(
            image=IMAGE_PATH,
            motion_bucket_id=127,
            fps=7,
            api_name="/predict"
        )
        temp_video = result[0] if isinstance(result, (list, tuple)) else result
        shutil.move(temp_video, VIDEO_CLIP_PATH)
        print(f"Animated clip saved: {VIDEO_CLIP_PATH}")
        return True
    except Exception as e:
        print(f"Animation error: {str(e)}")
        print("Falling back to static image.")
        return False


def build_final_video(quote):
    # Generate narration
    asyncio.run(
        edge_tts.Communicate(quote, "en-US-ChristopherNeural", rate="+2%").save(AUDIO_PATH)
    )
    print("Narration saved.")

    input_file = VIDEO_CLIP_PATH if os.path.exists(VIDEO_CLIP_PATH) else IMAGE_PATH

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-i", AUDIO_PATH,
        "-i", MUSIC_PATH,
        "-filter_complex",
        "[1:a]volume=1.4[a1];[2:a]volume=0.35,aloop=loop=-1:size=2e9[a2];[a1][a2]amix=inputs=2:duration=first[aout]",
        "-map", "0:v?",
        "-map", "[aout]",
        "-c:v", "libx264", "-crf", "23",
        "-c:a", "aac",
        "-shortest",
        "-pix_fmt", "yuv420p",
        FINAL_VIDEO
    ]

    try:
        subprocess.run(cmd, check=True, timeout=300)
        print(f"Final video created: {FINAL_VIDEO}")
    except Exception as e:
        print(f"ffmpeg failed: {e}")


def send_email():
    try:
        msg = EmailMessage()
        msg['Subject'] = 'New AI Video Ready'
        msg['From'] = MY_EMAIL
        msg['To'] = MY_EMAIL

        with open(FINAL_VIDEO, 'rb') as f:
            msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename='video.mp4')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(MY_EMAIL, EMAIL_PASS)
            server.send_message(msg)
        print("Email sent.")
    except Exception as e:
        print(f"Email failed: {e}")


async def main():
    quote, img_prompt = generate_content()  # حالا sync است (Groq ساده‌تر)

    if not await generate_image(img_prompt):
        print("Image failed → stopping")
        return

    await animate_to_video()

    build_final_video(quote)

    send_email()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
