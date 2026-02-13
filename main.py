import os
import asyncio
import shutil
import subprocess
import smtplib
from email.message import EmailMessage
from huggingface_hub import InferenceClient
import edge_tts
from gradio_client import Client

MY_EMAIL = "baqerfazli4@gmail.com"
EMAIL_PASS = os.getenv("EMAIL_APP_PASSWORD")
HF_TOKEN = os.getenv("HF_TOKEN")

IMAGE_PATH = "scene.jpg"
VIDEO_CLIP_PATH = "animated_clip.mp4"
AUDIO_PATH = "voice.mp3"
FINAL_VIDEO = "final_video.mp4"
MUSIC_PATH = "sample_music.mp3"

PROMPT_QUOTE = (
    "Write one short, powerful, viral motivational quote in English "
    "(15-25 words) with a luxury, nighttime, neon city or supercar theme."
)

def generate_content():
    client = InferenceClient(token=HF_TOKEN)

    quote_resp = client.text_generation(
        PROMPT_QUOTE,
        model="microsoft/Phi-3-mini-4k-instruct",
        max_new_tokens=60,
        temperature=0.85,
        stream=False
    )
    quote = quote_resp.strip()
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
        print(f"Generating image with {space} ...")
        result = hf.predict(
            prompt=img_prompt,
            width=1080,
            height=1920,
            num_inference_steps=4,
            seed=42,
            api_name="/infer"
        )
        temp_path = result[0] if isinstance(result, (list, tuple)) else result
        shutil.move(temp_path, IMAGE_PATH)
        print("Image saved.")
        return True
    except Exception as e:
        print(f"Image error: {str(e)}")
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
        print("Animated clip saved.")
        return True
    except Exception as e:
        print(f"Animation error: {str(e)} - Falling back to static zoom")
        return False


def build_final_video(quote):
    asyncio.run(edge_tts.Communicate(quote, "en-US-ChristopherNeural", rate="+2%").save(AUDIO_PATH))
    print("Narration saved.")

    input_file = VIDEO_CLIP_PATH if os.path.exists(VIDEO_CLIP_PATH) else IMAGE_PATH

    cmd = [
        "ffmpeg", "-y",
        "-i", input_file,
        "-i", AUDIO_PATH,
        "-i", MUSIC_PATH,
        "-filter_complex", "[1:a]volume=1.4[a1];[2:a]volume=0.35,aloop=loop=-1:size=2e9[a2];[a1][a2]amix=inputs=2:duration=first[aout]",
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
        print("Final video created.")
    except Exception as e:
        print(f"ffmpeg failed: {e}")


def judge_content(quote, img_prompt):
    client = InferenceClient(token=HF_TOKEN)
    judge_prompt = (
        f"Quote: '{quote}'\nImage prompt: {img_prompt}\n"
        "Is this viral-quality motivational content? Yes/No + reason. If No, suggest better prompt."
    )
    judgment = client.text_generation(
        judge_prompt,
        model="microsoft/Phi-3-mini-4k-instruct",
        max_new_tokens=100,
        stream=False
    )
    print("Judge:", judgment)


def send_email():
    try:
        msg = EmailMessage()
        msg['Subject'] = 'AI Video Ready (HF only)'
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
    quote, img_prompt = generate_content()

    if not await generate_image(img_prompt):
        return

    await animate_to_video()

    build_final_video(quote)

    judge_content(quote, img_prompt)

    send_email()

    print("Pipeline done - all on Hugging Face.")


if __name__ == "__main__":
    asyncio.run(main())
