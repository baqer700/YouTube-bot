import os
import asyncio
import shutil
import subprocess
import smtplib
from email.message import EmailMessage
from openai import OpenAI
import edge_tts
from gradio_client import Client, QueueError
from datetime import datetime

# ─── Configuration from GitHub Secrets ───────────────────────────────────────
MY_EMAIL = "baqerfazli4@gmail.com"
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

# File paths
IMAGE_PATH = "scene.jpg"
VIDEO_CLIP_PATH = "animated_clip.mp4"
AUDIO_PATH = "voice.mp3"
FINAL_VIDEO = "final_video.mp4"
MUSIC_PATH = "sample_music.mp3"  # Add a short royalty-free music file to repo

# Prompt for content generation
PROMPT_QUOTE = (
    "Write one short, powerful, viral motivational quote in English "
    "(15-25 words) with a luxury, nighttime, neon city or supercar theme."
)

async def generate_content():
    client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")

    resp = client.chat.completions.create(
        model="deepseek-chat",
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
        print(f"Image saved: {IMAGE_PATH} ({os.path.getsize(IMAGE_PATH) // 1024} KB)")
        return True
    except QueueError:
        print("Image generation: Queue full or timeout.")
        return False
    except Exception as e:
        print(f"Image generation error: {e}")
        return False


async def animate_to_video():
    # Recommended low-queue / fast spaces (Feb 2026 status):
    # - multimodalart/stable-video-diffusion (Stable Video Diffusion)
    # - ByteDance/AnimateDiff-Lightning (if active)
    # - seawolf2357/img2vid (SVD variant)
    space_id = "multimodalart/stable-video-diffusion"  # Change if queue too long

    try:
        hf = Client(space_id, hf_token=HF_TOKEN or None)
        print(f"Animating with {space_id} ... (may take 30-180 sec)")
        # Endpoint varies; check the Space page for exact api_name (usually /predict or /run)
        result = hf.predict(
            image=IMAGE_PATH,
            motion_bucket_id=127,   # Controls motion strength (adjust 50-200)
            fps=7,
            api_name="/predict"     # ← Check Space docs / code for correct endpoint
        )
        temp_video = result[0] if isinstance(result, (list, tuple)) else result
        shutil.move(temp_video, VIDEO_CLIP_PATH)
        print(f"Animated clip saved: {VIDEO_CLIP_PATH}")
        return True
    except Exception as e:
        print(f"Animation error (queue/full?): {e}")
        print("Falling back to static image with zoom.")
        return False


def build_final_video(quote):
    # Generate narration
    asyncio.run(
        edge_tts.Communicate(quote, "en-US-ChristopherNeural", rate="+2%").save(AUDIO_PATH)
    )
    print("Narration audio saved.")

    input_video = VIDEO_CLIP_PATH if os.path.exists(VIDEO_CLIP_PATH) else IMAGE_PATH

    # ffmpeg command: video + narration + background music (loop music + mix)
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-i", AUDIO_PATH,
        "-i", MUSIC_PATH,
        "-filter_complex",
        "[1:a]volume=1.4[a1];[2:a]volume=0.35,aloop=loop=-1:size=2e9[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v?",
        "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac",
        "-shortest",
        "-pix_fmt", "yuv420p",
        FINAL_VIDEO
    ]

    try:
        subprocess.run(cmd, check=True, timeout=300)
        if os.path.exists(FINAL_VIDEO):
            print(f"Final video ready: {FINAL_VIDEO} ({os.path.getsize(FINAL_VIDEO) // (1024*1024)} MB)")
        else:
            raise FileNotFoundError("Final video not created")
    except Exception as e:
        print(f"ffmpeg error: {e}")


async def judge_content(quote, img_prompt):
    client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
    judge_text = (
        f"Quote: '{quote}'\nImage prompt: {img_prompt}\n"
        "Is this motivational content viral-quality and attractive? "
        "Answer yes/no, then explain. If no, suggest improved prompt."
    )
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": judge_text}]
    )
    judgment = resp.choices[0].message.content
    print("LLM Judge:\n", judgment)


def send_email_notification():
    try:
        msg = EmailMessage()
        msg['Subject'] = 'New AI Motivational Video Ready'
        msg['From'] = MY_EMAIL
        msg['To'] = MY_EMAIL

        with open(FINAL_VIDEO, 'rb') as f:
            msg.add_attachment(f.read(), maintype='video', subtype='mp4', filename='motiv_video.mp4')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(MY_EMAIL, EMAIL_PASS)
            server.send_message(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Email error: {e}")


async def main():
    quote, img_prompt = await generate_content()

    success_image = await generate_image(img_prompt)
    if not success_image:
        print("Stopping due to image generation failure.")
        return

    success_anim = await animate_to_video()

    build_final_video(quote)

    await judge_content(quote, img_prompt)

    send_email_notification()

    # TODO: Add YouTube upload here (private + publishAt 24h later)

    print("Pipeline completed.")


if __name__ == "__main__":
    asyncio.run(main())
