# import whisper
# from pytube import YouTube
# from moviepy.editor import *
import os
import uuid
from datetime import datetime

 
def clean_youtube_url(url):
    if "?" in url:
        url = url.split("?")[0]
    return url

def main():
    print("🎥 YouTube Video Notes (Whisper-based Hindi + English)\n")
    url = input("🔗 Paste YouTube video URL: ").strip()
    url = clean_youtube_url(url)  # 🛠️ Clean the URL here

    print("⬇️ Downloading YouTube video...")
    audio_path = download_audio_from_youtube(url)
    # ... आगे का प्रोसेस


def download_audio_from_youtube(url):
    print("⬇️ Downloading YouTube video...")
    yt = YouTube(url)
    stream = yt.streams.filter(only_audio=True).first()
    filename = f"video_{uuid.uuid4()}.mp4"
    stream.download(filename=filename)

    print("🎧 Extracting audio...")
    audio = AudioFileClip(filename)
    audio_path = filename.replace('.mp4', '.wav')
    audio.write_audiofile(audio_path)

    os.remove(filename)
    

def transcribe_with_whisper(audio_path):
    print("🧠 Transcribing with Whisper...")
    model = whisper.load_model("small")  # You can also try "base", "medium", or "large"
    result = model.transcribe(audio_path, language="hi")  # auto-detects English-Hindi mix

    notes = []
    for segment in result['segments']:
        timestamp = f"{int(segment['start'])//60:02d}:{int(segment['start'])%60:02d}"
        notes.append({
            "speaker": "Speaker 1",
            "timestamp": timestamp,
            "text": segment['text']
        })

    return notes

def save_notes(notes, output_file="notes.txt"):
    print("💾 Saving notes...")
    with open(output_file, "w", encoding="utf-8") as f:
        for note in notes:
            line = f"{note['timestamp']} | {note['speaker']}: {note['text']}\n"
            print("📝", line.strip())
            f.write(line)

def main():
    print("🎥 YouTube Video Notes (Whisper-based Hindi + English)\n")
    url = input("🔗 Paste YouTube video URL: ")

    audio_path = download_audio_from_youtube(url)
    notes = transcribe_with_whisper(audio_path)
    os.remove(audio_path)

    if notes:
        save_notes(notes)
        print("\n✅ Notes saved to 'notes.txt'")
    else:
        print("⚠️ No notes generated.")

