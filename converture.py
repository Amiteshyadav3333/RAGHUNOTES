from flask import Flask, request, jsonify
import speech_recognition as sr
from moviepy.editor import *
import os
import whisper
import uuid

app = Flask(__name__)
model = whisper.load_model("base")  # or "small", "medium", "large"

@app.route("/process_audio", methods=["POST"])
def process_audio():
    video_url = request.json.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    audio_file = download_audio_from_youtube(video_url)
    notes = transcribe_with_speaker(audio_file)

    return jsonify(notes)

def download_audio_from_youtube(url):
    from pytube import YouTube
    yt = YouTube(url)
    stream = yt.streams.filter(only_audio=True).first()
    filename = f"temp_{uuid.uuid4()}.mp4"
    stream.download(filename=filename)

    audio = AudioFileClip(filename)
    audio_path = filename.replace('.mp4', '.wav')
    audio.write_audiofile(audio_path)
    os.remove(filename)
    return audio_path

def transcribe_with_speaker(audio_path):
    result = model.transcribe(audio_path, word_timestamps=True)
    text_segments = result["segments"]

    notes = []
    for segment in text_segments:
        notes.append({
            "speaker": f"Speaker {segment.get('speaker', 1)}",  # Placeholder, Whisper doesn't do diarization
            "text": segment["text"]
        })

    os.remove(audio_path)
    return notes

if __name__ == "__main__":
    app.run(debug=True)