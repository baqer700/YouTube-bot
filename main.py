import os
import random
import requests
import asyncio
import edge_tts
from huggingface_hub import InferenceClient
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip

# --- CONFIGURATION ---
HF_TOKEN = os.getenv("HF_TOKEN")
OUTPUT_VIDEO = "final_output.mp4"
IMAGE_FILE = "generated_image.png"
AUDIO_FILE = "generated_audio.mp3"

# تنظیم مدل‌ها (از مدل‌های Inference API استفاده می‌کنیم که سریعتر از Spaces هستند)
TEXT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3" 
IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell" # یا "stabilityai/stable-diffusion-xl-base-1.0"

def get_motivational_quote():
    """تولید متن انگیزشی با استفاده از Inference API"""
    print(">>> Generating Quote...")
    client = InferenceClient(api_key=HF_TOKEN)
    
    prompt = "Generate a single, powerful, short motivational quote (max 15 words) about success, discipline, or night grind. Do not add any intro text."
    
    try:
        response = client.text_generation(prompt, model=TEXT_MODEL, max_new_tokens=50, return_full_text=False)
        quote = response.strip().replace('"', '')
        print(f"Quote: {quote}")
        return quote
    except Exception as e:
        print(f"Text Gen Error: {e}")
        return "Discipline is doing what needs to be done, even if you don't want to do it."

def generate_image(prompt_text):
    """تولید تصویر با FLUX یا SDXL"""
    print(">>> Generating Image...")
    # پرامپت مهندسی شده برای استایل لوکس
    image_prompt = (
        f"Cinematic shot, luxury lifestyle, matte black sports car parked in a rainy neon city at night, "
        f"cyberpunk vibes, moody lighting, highly detailed, photorealistic, 8k, masterpiece. "
        f"Mood: {prompt_text}"
    )
    
    API_URL = f"https://api-inference.huggingface.co/models/{IMAGE_MODEL}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # تلاش برای درخواست مستقیم (سریع‌تر و بدون صف Space)
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": image_prompt}, timeout=60)
        
        if response.status_code == 200:
            with open(IMAGE_FILE, "wb") as f:
                f.write(response.content)
            print("Image Saved successfully.")
            return True
        else:
            print(f"Image Gen Failed: {response.status_code} - {response.text}")
            # اینجا می‌توان فال‌بک به یک عکس استوک گذاشت
            return False
    except Exception as e:
        print(f"Image Error: {e}")
        return False

async def generate_audio(text):
    """تولید صدا با Edge-TTS"""
    print(">>> Generating Audio...")
    voice = "en-US-ChristopherNeural"  # صدای مردانه و با ابهت
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(AUDIO_FILE)
    print("Audio Saved.")

def create_video_ffmpeg_style():
    """ترکیب تصویر و صدا و ساخت ویدیو با افکت زوم (جایگزین AI Video)"""
    print(">>> Editing Video...")
    
    if not os.path.exists(IMAGE_FILE) or not os.path.exists(AUDIO_FILE):
        print("Missing files for video creation.")
        return

    try:
        # بارگذاری فایل‌ها
        audio = AudioFileClip(AUDIO_FILE)
        image = ImageClip(IMAGE_FILE)
        
        # تنظیم مدت زمان ویدیو (کمی بیشتر از صدا)
        duration = audio.duration + 1.5 
        image = image.set_duration(duration)
        
        # تغییر سایز برای YouTube Shorts (9:16)
        # ابتدا کراپ می‌کنیم به مرکز و سپس ریسایز
        w, h = image.size
        # برش وسط برای نسبت 9:16
        target_ratio = 9/16
        current_ratio = w/h
        
        if current_ratio > target_ratio:
            new_w = h * target_ratio
            image = image.crop(x1=w/2 - new_w/2, width=new_w, height=h)
        else:
            new_h = w / target_ratio
            image = image.crop(y1=h/2 - new_h/2, width=w, height=new_h)
            
        image = image.resize(height=1920) # کیفیت بالا

        # افکت زوم نرم (Ken Burns)
        # زوم از 1.0 به 1.1 در طول ویدیو
        image = image.resize(lambda t: 1 + 0.04 * t) 
        image = image.set_position(('center', 'center'))

        # ترکیب
        final_clip = CompositeVideoClip([image]).set_audio(audio)
        final_clip.write_videofile(OUTPUT_VIDEO, fps=24, codec="libx264", audio_codec="aac")
        print(f"Video created: {OUTPUT_VIDEO}")
        
    except Exception as e:
        print(f"Video Editing Error: {e}")

async def main():
    if not HF_TOKEN:
        print("Error: HF_TOKEN not found inside Secrets!")
        return

    # 1. تولید متن
    quote = get_motivational_quote()
    
    # 2. تولید تصویر
    img_success = generate_image(quote)
    if not img_success:
        print("Aborting pipeline due to image failure.")
        return
        
    # 3. تولید صدا
    await generate_audio(quote)
    
    # 4. ساخت ویدیو
    create_video_ffmpeg_style()

    # پاکسازی فایل‌های موقت
    # if os.path.exists(IMAGE_FILE): os.remove(IMAGE_FILE)
    # if os.path.exists(AUDIO_FILE): os.remove(AUDIO_FILE)

if __name__ == "__main__":
    asyncio.run(main())
