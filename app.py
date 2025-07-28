import os
import re
import tempfile
import subprocess
import webbrowser
import threading
import time
import warnings
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import whisper
from deep_translator import GoogleTranslator


warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret_key_change_me'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


os.makedirs("downloads", exist_ok=True)
print("Cargando el modelo Whisper (base)...")
try:
    
    model = whisper.load_model("base")
    print("Modelo Whisper cargado con éxito.")
except Exception as e:
    print(f"Error al cargar el modelo Whisper: {e}")
    exit()


NOTES = []

current_speaker = "Speaker 1"

class Note:
    def __init__(self, english_text, hindi_text, speaker, timestamp):
        self.english_text = english_text
        self.hindi_text = hindi_text 
        self.speaker = speaker
        self.timestamp = timestamp

    def to_dict(self):
        return {
            'english_text': self.english_text,
            'hindi_text': self.hindi_text,
            'speaker': self.speaker,
            'timestamp': self.timestamp,
            'text': self.english_text  # Add this for frontend compatibility
        }

def extract_video_id(url):
    """Extrae el ID del video de una URL de YouTube usando regex."""
    pattern = r"(?:v=|\/|be\/|embed\/|watch\?v=|youtu\.be\/)([A-Za-z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None


def translate_to_hindi(text):
    """
    Real Hindi translation using Google Translate API
    """
    try:
        translator = GoogleTranslator(source='en', target='hi')
        result = translator.translate(text)
        return result
    except Exception as e:
        print(f"Translation error: {e}")
        return f"[Hindi: {text}]"  # Fallback


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_video', methods=['POST'])
def process_video():
    video_url = request.json.get('url')
    if not video_url:
        return jsonify({'success': False, 'error': 'No URL provided'}), 400

    # Use yt-dlp to extract a unique id for the video (works for all platforms)
    try:
        # Get video info to extract id and title
        info_result = subprocess.run(
            ['yt-dlp', '--dump-json', video_url],
            capture_output=True, text=True, encoding='utf-8'
        )
        if info_result.returncode != 0:
            return jsonify({'success': False, 'error': 'URL not supported or video not found.'}), 400
        import json
        video_info = json.loads(info_result.stdout)
        video_id = video_info.get('id', 'unknown')
        ext = video_info.get('ext', 'mp3')
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error extracting video info: {str(e)}'}), 400

    try:
        filename = f"downloads/{video_id}.mp3"
        print(f"Descargando audio desde: {video_url}")
        subprocess.run(
            ['yt-dlp', '-x', '--audio-format', 'mp3', '-o', filename, video_url],
            check=True, capture_output=True, text=True, encoding='utf-8'
        )
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            return jsonify({'success': False, 'error': 'Downloaded file does not exist or is empty'}), 500
        print(f"Transcribiendo archivo de audio: {filename}")
        result_en = model.transcribe(
            filename, 
            fp16=False,
            language="en",  # Force English
            task="transcribe",
            condition_on_previous_text=False,  # Don't condition on previous text
            temperature=0.0  # Use greedy decoding for better accuracy
        )
        segments = result_en.get("segments", [])
        global NOTES
        NOTES = [] 
        for seg in segments:
            timestamp = datetime.utcfromtimestamp(seg['start']).strftime('%H:%M:%S')
            english_text = seg['text'].strip()
            if english_text:
                hindi_text = translate_to_hindi(english_text)
                note = Note(english_text=english_text, hindi_text=hindi_text,
                            speaker=current_speaker, timestamp=timestamp)
                NOTES.append(note.to_dict())
        print(f"Transcripción completa. Se generaron {len(NOTES)} notas.")
        socketio.emit('notes_updated', NOTES)
        return jsonify({
            'success': True,
            'note_count': len(NOTES),
            'audio_file': filename
        })
    except subprocess.CalledProcessError as e:
        print(f"yt-dlp error: {e.stderr}")
        return jsonify({'success': False, 'error': f'Download error: {e.stderr}'}), 500
    except Exception as e:
        print(f"Unexpected error in process_video: {e}")
        return jsonify({'success': False, 'error': f'Unexpected error: {str(e)}'}), 500

@app.route("/add_note", methods=["POST"])
def add_note():
    data = request.json
    english_text = data.get("english_text", "").strip()
    
    if not english_text:
        return jsonify(success=False, error="El texto en inglés es obligatorio"), 400

    
    hindi_text = translate_to_hindi(english_text)

    note = Note(
        english_text=english_text,
        hindi_text=data.get("hindi_text") or hindi_text, 
        speaker=data.get("speaker", current_speaker),
        timestamp=datetime.now().strftime("%H:%M:%S")
    )
    NOTES.append(note.to_dict())
    socketio.emit('new_note', note.to_dict()) 
    return jsonify(success=True, note=note.to_dict())

@app.route("/get_notes", methods=["GET"])
def get_notes():
    return jsonify(NOTES)

@app.route("/update_speaker", methods=["POST"])
def update_speaker():
    global current_speaker
    speaker = request.json.get('speaker')
    if speaker:
        current_speaker = speaker
        return jsonify(success=True, speaker=current_speaker)
    return jsonify(success=False, error="No se proporcionó nombre de orador"), 400

@app.route("/download_pdf")
def download_pdf():
    if not NOTES:
        return "No hay notas para descargar.", 404

    # Get custom filename from query parameter
    custom_filename = request.args.get('filename', 'notas_bilingues.pdf')
    
    # Sanitize filename - remove any path separators and ensure it ends with .pdf
    if not custom_filename.endswith('.pdf'):
        custom_filename += '.pdf'
    
    # Remove any dangerous characters
    import re
    custom_filename = re.sub(r'[<>:"/\\|?*]', '_', custom_filename)

    try:
        # Create PDF using reportlab
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Title
        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width/2, height-50, "NOTES READY HAI ,MAJE KARO")
        
        # Set font for content
        p.setFont("Helvetica", 10)
        
        y_position = height - 100
        line_height = 15
        
        for note in NOTES:
            # Check if we need a new page
            if y_position < 50:
                p.showPage()
                y_position = height - 50
                p.setFont("Helvetica", 10)
            
            # English text
            en_text = f"[{note['timestamp']}] {note['speaker']} (EN): {note['english_text']}"
            # Wrap text to fit page width
            words = en_text.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if p.stringWidth(test_line, "Helvetica", 10) < width - 100:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Draw English lines
            for line in lines:
                p.drawString(50, y_position, line)
                y_position -= line_height
            
            # Hindi text (simplified to avoid encoding issues)
            hi_text = f"[{note['timestamp']}] {note['speaker']} (HI): [Hindi translation available in TXT file]"
            p.drawString(50, y_position, hi_text)
            y_position -= line_height * 2
        
        p.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=custom_filename
        )
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return jsonify({'success': False, 'error': f'Error generating PDF: {str(e)}'}), 500

@socketio.on('connect')
def handle_connect():
    print(f'Cliente conectado: {request.sid}')
    emit('server_message', {'data': '¡Conectado exitosamente al servidor!'})

@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    
    try:
        # Create a temporary file with WebM format for better compatibility
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            temp_audio.write(data)
            path = temp_audio.name

        # Check if file exists and has content
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            print("Audio file is empty or doesn't exist")
            return

        # Try to transcribe with better settings
        try:
            # Use better Whisper settings for improved transcription
            result_en = model.transcribe(
                path, 
                fp16=False,
                language="en",  # Force English
                task="transcribe",
                condition_on_previous_text=False,  # Don't condition on previous text
                temperature=0.0  # Use greedy decoding for better accuracy
            )
            english_text = result_en["text"].strip()
            
            if english_text and len(english_text) > 3:  # Only process if there's meaningful text
                
                hindi_text = translate_to_hindi(english_text)
                timestamp = datetime.now().strftime("%H:%M:%S")

                note = Note(english_text, hindi_text, current_speaker, timestamp)
                NOTES.append(note.to_dict())
                
                # Fix: Remove broadcast parameter
                socketio.emit('new_note', note.to_dict())
                print(f"Nota en tiempo real: {note.to_dict()}")
            else:
                print("No meaningful text found in audio chunk")
                
        except Exception as transcribe_error:
            print(f"Transcription error: {str(transcribe_error)}")
            # Don't emit error to client for every failed chunk
            # Only emit if it's a critical error
            if "Failed to load audio" not in str(transcribe_error):
                emit('transcript_error', {'error': str(transcribe_error)})

    except Exception as e:
        print(f"Error en la transcripción en tiempo real: {str(e)}")
        # Only emit critical errors to client
        if "Failed to load audio" not in str(e):
            emit('transcript_error', {'error': str(e)})
    finally:
        # Clean up temporary file
        if 'path' in locals() and os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass  # Ignore cleanup errors

# AI Features
@app.route("/ai_summarize", methods=["POST"])
def ai_summarize():
    """AI-powered summarization of notes"""
    try:
        if not NOTES:
            return jsonify({'success': False, 'error': 'No hay notas para resumir'}), 400
        
        # Combine all English text
        all_text = " ".join([note['english_text'] for note in NOTES])
        
        # Simple summarization (you can integrate with OpenAI or other AI services)
        summary = f"Resumen de {len(NOTES)} notas:\n\n"
        summary += f"Total de notas: {len(NOTES)}\n"
        summary += f"Tiempo total: {len(NOTES) * 3} segundos aproximadamente\n"
        summary += f"Temas principales: {extract_main_topics(all_text)}\n"
        
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/ai_title", methods=["POST"])
def ai_title():
    """AI-powered title generation"""
    try:
        if not NOTES:
            return jsonify({'success': False, 'error': 'No hay notas para generar título'}), 400
        
        # Combine all English text
        all_text = " ".join([note['english_text'] for note in NOTES[:5]])  # Use first 5 notes
        
        # Generate title based on content
        title = generate_title_from_content(all_text)
        
        return jsonify({'success': True, 'title': title})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/ai_video_analysis", methods=["POST"])
def ai_video_analysis():
    """AI-powered video analysis"""
    try:
        data = request.json
        video_url = data.get('url')
        
        if not video_url:
            return jsonify({'success': False, 'error': 'No se proporcionó URL'}), 400
        
        # Extract video info
        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({'success': False, 'error': 'URL de YouTube inválida'}), 400
        
        # Analyze video content
        analysis = analyze_video_content(video_url, video_id)
        
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def extract_main_topics(text):
    """Extract main topics from text"""
    # Simple keyword extraction
    words = text.lower().split()
    common_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
    keywords = [word for word in words if word not in common_words and len(word) > 3]
    
    # Count frequency
    from collections import Counter
    word_count = Counter(keywords)
    top_words = word_count.most_common(5)
    
    return ", ".join([word for word, count in top_words])

def generate_title_from_content(text):
    """Generate title from content"""
    # Simple title generation
    words = text.split()
    if len(words) > 0:
        # Use first meaningful sentence or first few words
        first_sentence = text.split('.')[0]
        if len(first_sentence) > 10:
            return first_sentence[:50] + "..."
        else:
            return " ".join(words[:5]) + "..."
    return "Notas de la Sesión"

def analyze_video_content(video_url, video_id):
    """Analyze video content"""
    try:
        # Get video info using yt-dlp
        result = subprocess.run(
            ['yt-dlp', '--dump-json', video_url],
            capture_output=True, text=True, encoding='utf-8'
        )
        
        if result.returncode == 0:
            import json
            video_info = json.loads(result.stdout)
            
            analysis = {
                'title': video_info.get('title', 'Unknown'),
                'duration': video_info.get('duration', 0),
                'view_count': video_info.get('view_count', 0),
                'upload_date': video_info.get('upload_date', 'Unknown'),
                'description': video_info.get('description', '')[:200] + "...",
                'tags': video_info.get('tags', [])[:5]
            }
            
            return analysis
        else:
            return {'error': 'No se pudo obtener información del video'}
            
    except Exception as e:
        return {'error': f'Error analizando video: {str(e)}'}

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Cliente desconectado: {request.sid}')



def open_browser():
    """Abre el navegador web en la URL de la aplicación después de un breve retraso."""
    print("Abriendo el navegador en http://127.0.0.1:5050")
    time.sleep(1)
    webbrowser.open_new("http://127.0.0.1:5050")

if __name__ == "__main__":
    
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Thread(target=open_browser).start()

    print("Iniciando servidor en http://127.0.0.1:5050...")
    
    socketio.run(app, debug=True, port=5050, use_reloader=True)

@app.route('/get_audio')
def get_audio():
    path = request.args.get('path')
    if not path or not os.path.exists(path):
        return "Audio file not found", 404
    return send_file(path, mimetype='audio/mpeg', as_attachment=False)