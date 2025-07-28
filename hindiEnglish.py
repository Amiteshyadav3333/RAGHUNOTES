import speech_recognition as sr
from langdetect import detect
from datetime import datetime

def recognize_speech(language="en-IN"):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Speak now...")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)

    try:
        text = r.recognize_google(audio, language=language)
        return text
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError:
        return "Could not request results"

def detect_language(text):
    try:
        lang = detect(text)
        return lang
    except:
        return "unknown"

def get_speaker_name():
    # In real applications, implement speaker diarization
    return "Speaker 1"

def main():
    print("🎙️ Real-time Voice Note Taker (Hindi + English)\nPress Ctrl+C to stop.\n")
    notes = []

    try:
        while True:
            result = recognize_speech(language="hi-IN")  # Supports Hindi + English mix
            lang = detect_language(result)
            speaker = get_speaker_name()
            timestamp = datetime.now().strftime("%H:%M:%S")

            notes.append({
                "speaker": speaker,
                "language": lang,
                "timestamp": timestamp,
                "text": result
            })

            print(f"\n📝 {speaker} ({lang.upper()}, {timestamp}): {result}")

    except KeyboardInterrupt:
        print("\n🛑 Stopped recording.")
        print("\n📋 Final Notes:")
        for note in notes:
            print(f"{note['timestamp']} | {note['speaker']} ({note['language']}): {note['text']}")

        # Optional: Save to file
        with open("voice_notes.txt", "w", encoding="utf-8") as f:
            for note in notes:
                f.write(f"{note['timestamp']} | {note['speaker']} ({note['language']}): {note['text']}\n")

if __name__ == "__main__":
    main()