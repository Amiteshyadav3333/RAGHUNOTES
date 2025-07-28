from pytube import YouTube
from moviepy.audio.io.AudioFileClip import AudioFileClip
import speech_recognition as sr
from langdetect import detect
from datetime import datetime
import os
import uuid

def download_youtube_audio(url):
    print("⬇️ Downloading YouTube video...")
    yt = YouTube(url)
    stream = yt.streams.filter(only_audio=True).first()
    filename = f"yt_{uuid.uuid4()}.mp4"
    stream.download(filename=filename)

    print("🔊 Converting to WAV audio...")
    audio = AudioFileClip(filename)
    audio_path = filename.replace('.mp4', '.wav')
    audio.write_audiofile(audio_path)

    os.remove(filename)
    return audio_path

def transcribe_audio(audio_path):
    recognizer = sr.Recognizer()
    audio_file = sr.AudioFile(audio_path)
    notes = []

    print("🧠 Transcribing audio...")

    with audio_file as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.record(source)

    try:
        # Mixed Hindi + English works best with 'hi-IN'
        text = recognizer.recognize_google(audio, language="hi-IN")
        lang = detect(text)
        speaker = "Speaker 1"
        timestamp = datetime.now().strftime("%H:%M:%S")

        note = {
            "speaker": speaker,
            "language": lang,
            "timestamp": timestamp,
            "text": text
        }

        notes.append(note)
        return notes

    except sr.UnknownValueError:
        print("❌ Could not understand the audio.")
    except sr.RequestError:
        print("❌ Could not connect to recognition service.")

    return []

def save_notes(notes, output_file="notes.txt"):
    with open(output_file, "w", encoding="utf-8") as f:
        for note in notes:
            line = f"{note['timestamp']} | {note['speaker']} ({note['language']}): {note['text']}\n"
            print("📝", line.strip())
            f.write(line)

def main():
    print("🎥 YouTube to Notes (Hindi + English)\n")
    url = input("🔗 Paste YouTube video URL: ")

    audio_path = download_youtube_audio(url)
    notes = transcribe_audio(audio_path)
    os.remove(audio_path)

    if notes:
        save_notes(notes)
        print("\n✅ Notes saved to 'notes.txt'")
    else:
        print("⚠️ No notes generated.")

if __name__ == "__main__":
    main()