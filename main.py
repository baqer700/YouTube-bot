import os, requests, time, base64, pickle
from groq import Groq
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def get_youtube():
    token_64 = os.environ.get("YOUTUBE_TOKEN_64")
    with open("token.pickle", "wb") as f:
        f.write(base64.b64decode(token_64))
    with open("token.pickle", "rb") as t:
        return build("youtube", "v3", credentials=pickle.load(t))

def run_factory():
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": "Shocking psychology fact (10 words)."}],
        model="llama-3.3-70b-versatile")
    fact_text = response.choices[0].message.content
    
    gTTS(text=fact_text, lang='en').save("audio.mp3")
    audio = AudioFileClip("audio.mp3")

    clips = []
    for i in range(3):
        img_url = f"https://pollinations.ai/p/psychology_3d_style_{i}?width=720&height=1280&seed={time.time()}"
        with open(f"{i}.jpg", "wb") as f:
            f.write(requests.get(img_url).content)
        clips.append(ImageClip(f"{i}.jpg").set_duration(audio.duration / 3 + 0.5))

    final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
    final_video.write_videofile("final.mp4", fps=24, codec="libx264")

    yt = get_youtube()
    yt.videos().insert(
        part="snippet,status",
        body={
            'snippet': {
                'title': 'Psychology Fact #shorts',
                'description': fact_text,
                'tags': ['psychology', 'facts', 'ai'],
                'categoryId': '27'
            },
            'status': {'privacyStatus': 'private'}
        },
        media_body=MediaFileUpload("final.mp4")
    ).execute()

if __name__ == "__main__":
    run_factory()
  
