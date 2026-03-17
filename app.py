import streamlit as st
import os
import tempfile
import time
import subprocess
import uuid
from groq import Groq
import yt_dlp
from datetime import datetime, timedelta

# --- CONFIGURATION SÉCURISÉE ---
def get_api_key():
    if "GROQ_API_KEY" in st.secrets:
        return st.secrets["GROQ_API_KEY"]
    return os.environ.get("GROQ_API_KEY", "")

# Configuration de la page avec le nouveau nom
st.set_page_config(
    page_title="AllayeVox 🇲🇱",
    page_icon="🎙️",
    layout="wide"
)

# --- INITIALISATION ---
api_key = get_api_key()
if "custom_api_key" in st.session_state and st.session_state.custom_api_key:
    api_key = st.session_state.custom_api_key

client = Groq(api_key=api_key) if api_key else None

# --- DESIGN SOFT UI (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #1E293B;
    }
    
    .main {
        background: linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%);
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background: linear-gradient(90deg, #0F172A 0%, #334155 100%);
        color: white;
        border: none;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        color: #F8FAFC;
    }
    
    .stTextInput>div>div>input, .stFileUploader>section {
        border-radius: 12px !important;
        border: 1px solid #E2E8F0 !important;
    }
    
    .card {
        padding: 2rem;
        border-radius: 16px;
        background: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
    
    .mali-flag {
        background: linear-gradient(90deg, #14B8A6 33%, #FACC15 33%, #FACC15 66%, #EF4444 66%);
        height: 4px;
        width: 100%;
        border-radius: 2px;
        margin-bottom: 20px;
    }

    .status-box {
        padding: 15px;
        border-radius: 12px;
        background: #F8FAFC;
        border-left: 5px solid #0F172A;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS TECHNIQUES ---

def format_srt_timestamp(seconds: float):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((td.total_seconds() - total_seconds) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_srt(segments):
    srt_output = ""
    if not segments: return ""
    for i, segment in enumerate(segments):
        start = format_srt_timestamp(segment.get('start', 0))
        end = format_srt_timestamp(segment.get('end', 0))
        text = segment.get('text', '').strip()
        srt_output += f"{i+1}\n{start} --> {end}\n{text}\n\n"
    return srt_output

def process_audio(input_path):
    output_path = os.path.join(tempfile.gettempdir(), f"final_{uuid.uuid4().hex}.mp3")
    # Paramètres FFmpeg optimisés pour éviter les erreurs de codec et réduire le poids
    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn", "-ar", "16000", "-ac", "1", "-ab", "64k",
        "-f", "mp3", output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        st.error(f"Erreur FFmpeg : {e.stderr.decode()}")
        return None

class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): st.error(msg)

def download_youtube(url, progress_bar):
    temp_dir = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex
    output_template = os.path.join(temp_dir, f"yt_{unique_id}.%(ext)s")
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%','')
            try:
                progress_bar.progress(float(p)/100, text=f"Téléchargement YouTube : {p}%")
            except: pass

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'logger': MyLogger(),
        'progress_hooks': [progress_hook],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info).replace(info['ext'], 'mp3')

# --- INTERFACE UTILISATEUR ---

# Sidebar
with st.sidebar:
    st.markdown("<h1 style='text-align: center;'>AllayeVox 🇲🇱</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    if "is_subscribed" not in st.session_state:
        st.session_state.is_subscribed = True # Créateur
    
    st.success("💎 Accès Créateur Actif")
    
    with st.expander("⚙️ Configuration"):
        new_key = st.text_input("Clé API Groq", type="password")
        if new_key:
            st.session_state.custom_api_key = new_key
    
    st.markdown("---")
    st.info("Cette application utilise Whisper-V3 pour une précision maximale.")

# Header Vitrine
st.markdown("<div class='mali-flag'></div>", unsafe_allow_html=True)
col_h1, col_h2 = st.columns([2, 1])

with col_h1:
    st.title("AllayeVox 🇲🇱")
    st.markdown("""
        ### L'intelligence artificielle au service de vos contenus.
        Transcrivez vos réunions, vos vidéos YouTube ou vos vocaux WhatsApp en quelques secondes avec une précision chirurgicale.
    """)

with col_h2:
    st.image("https://images.unsplash.com/photo-1478737270239-2f02b77fc618?auto=format&fit=crop&q=80&w=400", use_container_width=True)

# Zone d'action
st.markdown("<div class='card'>", unsafe_allow_html=True)
t1, t2 = st.tabs(["📁 Fichiers Audio/Vidéo", "🔗 Lien YouTube"])

source_file = None
youtube_url = None

with t1:
    source_file = st.file_uploader("Glissez votre fichier ici", type=["mp3", "m4a", "wav", "ogg", "opus", "mp4"])
    st.caption("Supporte WhatsApp (.opus), MP3, et MP4.")

with t2:
    youtube_url = st.text_input("Collez l'URL de la vidéo YouTube", placeholder="https://www.youtube.com/watch?v=...")
    st.caption("L'audio sera extrait et analysé automatiquement.")

st.markdown("</div>", unsafe_allow_html=True)

if st.button("🚀 LANCER LA TRANSCRIPTION"):
    if not api_key:
        st.error("Clé API manquante. Ajoutez-la dans les paramètres.")
    elif not source_file and not youtube_url:
        st.warning("Veuillez fournir un fichier ou un lien YouTube.")
    else:
        try:
            temp_input = None
            audio_ready = None
            
            # 1. Acquisition de la source
            if source_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(source_file.name)[1]) as tmp:
                    tmp.write(source_file.getvalue())
                    temp_input = tmp.name
                
                with st.status("🛠️ Préparation de l'audio...") as s:
                    audio_ready = process_audio(temp_input)
                    s.update(label="Audio prêt !", state="complete")
            
            elif youtube_url:
                progress_bar = st.progress(0, text="Initialisation YouTube...")
                audio_ready = download_youtube(youtube_url, progress_bar)
                progress_bar.empty()
            
            # 2. Transcription
            if audio_ready:
                with st.status("🧠 L'IA AllayeVox analyse votre contenu...") as status:
                    start_time = time.time()
                    with open(audio_ready, "rb") as f:
                        transcript = client.audio.transcriptions.create(
                            file=(audio_ready, f.read()),
                            model="whisper-large-v3",
                            response_format="verbose_json",
                            language="fr" # Forçage français par défaut
                        )
                    end_time = time.time()
                    status.update(label=f"Analyse terminée en {int(end_time - start_time)}s", state="complete")
                
                # 3. Affichage des résultats
                st.balloons()
                res_col1, res_col2 = st.columns([3, 1])
                
                with res_col1:
                    st.markdown("### 📝 Texte Transcrit")
                    st.text_area("", transcript.text, height=400)
                
                with res_col2:
                    st.markdown("### 📥 Téléchargement")
                    st.download_button("Format Texte (.txt)", transcript.text, "allayevox_export.txt", use_container_width=True)
                    srt_data = generate_srt(transcript.segments)
                    st.download_button("Format Sous-titres (.srt)", srt_data, "allayevox_subtitles.srt", use_container_width=True)
                
                # Nettoyage final
                if temp_input and os.path.exists(temp_input): os.remove(temp_input)
                if audio_ready and os.path.exists(audio_ready): os.remove(audio_ready)

        except Exception as e:
            st.error(f"Une erreur est survenue : {str(e)}")

st.markdown("""
    <div style='text-align: center; margin-top: 50px; color: #94A3B8;'>
        <small>AllayeVox 🇲🇱 - Technologie Whisper-V3 & Groq Cloud<br>Fait avec passion pour le Mali</small>
    </div>
    """, unsafe_allow_html=True)
