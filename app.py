import streamlit as st
import os
import tempfile
import subprocess
import uuid
from groq import Groq
import yt_dlp
from datetime import datetime, timedelta

# --- CONFIG ---
def get_api_key():
    return st.secrets["GROQ_API_KEY"] if "GROQ_API_KEY" in st.secrets else os.environ.get("GROQ_API_KEY", "")

st.set_page_config(page_title="AllayeVox Pro 🇲🇱", page_icon="🎙️", layout="wide")
api_key = get_api_key()
client = Groq(api_key=api_key) if api_key else None

# --- CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
:root {
    --primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --success: #10b981;
    --bg-glass: rgba(255,255,255,0.95);
    --shadow: 0 25px 50px -12px rgba(0,0,0,0.15);
}
* { font-family: 'Inter', sans-serif !important; }
.stApp { background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%); }
[data-testid="stHeader"], #MainMenu, header, footer { display: none !important; }
.hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 3rem 2rem; border-radius: 0 0 2rem 2rem; color: white; text-align: center; }
.card { background: var(--bg-glass); border-radius: 20px; padding: 2rem; margin: 1rem 0; box-shadow: var(--shadow); }
.btn-primary { background: var(--primary) !important; border-radius: 15px !important; height: 60px !important; font-weight: 700 !important; font-size: 1.1rem !important; }
.result-box { background: white; border-radius: 16px; padding: 2rem; border-left: 5px solid var(--success); font-size: 1.1rem; line-height: 1.7; }
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS ---
def format_srt_timestamp(seconds: float):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours, minutes, secs = total_seconds // 3600, (total_seconds % 3600) // 60, total_seconds % 60
    millis = int((td.total_seconds() - total_seconds) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_srt(segments):
    if not segments: return ""
    srt = ""
    for i, segment in enumerate(segments):
        srt += f"{i+1}\n{format_srt_timestamp(segment.get('start', 0))} --> {format_srt_timestamp(segment.get('end', 0))}\n{segment.get('text', '').strip()}\n\n"
    return srt

def process_audio(input_path):
    output_path = os.path.join(tempfile.gettempdir(), f"proc_{uuid.uuid4().hex}.mp3")
    cmd = ["ffmpeg", "-y", "-i", input_path, "-vn", "-ar", "16000", "-ac", "1", "-ab", "128k", "-f", "mp3", output_path]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    except:
        return None

def download_youtube(url):
    temp_dir = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex
    output = os.path.join(temp_dir, f"yt_{unique_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output,
        'quiet': True,
        'noplaylist': True,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            return os.path.join(temp_dir, f"yt_{unique_id}.mp3")
    except:
        return None

# --- HERO ---
st.markdown("""
<div class="hero">
    <div style="max-width: 800px; margin: 0 auto;">
        <div style="background: rgba(255,255,255,0.2); padding: 10px 20px; border-radius: 50px; display: inline-block; margin-bottom: 2rem;">
            <span style="font-weight: 700; font-size: 1.1rem;">🇲🇱 BAMAKO TECH</span>
        </div>
        <h1 style="font-size: 3.5rem; font-weight: 800; margin: 0 0 1rem;">AllayeVox Pro</h1>
        <p style="font-size: 1.3rem; margin: 0; opacity: 0.95;">Transcrivez TOUTES les vidéos YouTube en 1 clic</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- FORM ---
if "transcription_done" not in st.session_state:
    st.session_state.transcription_done = False

col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; margin-bottom: 1.5rem;">🔗</div>', unsafe_allow_html=True)
    st.markdown('<h3 style="text-align: center; font-size: 1.5rem; margin-bottom: 1rem;">YouTube</h3>', unsafe_allow_html=True)
    url = st.text_input("Lien YouTube", placeholder="https://youtube.com/watch?v=...", key="youtube_url")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; margin-bottom: 1.5rem;">📁</div>', unsafe_allow_html=True)
    st.markdown('<h3 style="text-align: center; font-size: 1.5rem; margin-bottom: 1rem;">Fichier</h3>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Choisir fichier", type=["mp3","m4a","wav","mp4","webm"], key="file_upload")
    st.markdown('</div>', unsafe_allow_html=True)

# --- BOUTON PRINCIPAL ---
if st.button("🚀 **LANCER TRANSCRIPTION**", type="primary", use_container_width=True, key="transcribe_btn"):
    if not api_key:
        st.error("❌ Clé API Groq manquante (Secrets.toml)")
    elif not url and not uploaded_file:
        st.warning("👆 Choisissez YouTube OU fichier")
    else:
        st.session_state.transcription_done = False
        st.rerun()

# --- TRAITEMENT ---
if st.session_state.transcription_done == False and (url or uploaded_file) and api_key:
    with st.spinner("🎙️ Processing..."):
        audio_ready = None
        
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                tmp.write(uploaded_file.getvalue())
                audio_ready = process_audio(tmp.name)
        elif url:
            audio_ready = download_youtube(url)
            if not audio_ready:
                st.error("❌ Échec YouTube. Téléchargez le fichier manuellement.")
                st.stop()
        
        if audio_ready:
            try:
                with open(audio_ready, "rb") as f:
                    transcript = client.audio.transcriptions.create(
                        file=(os.path.basename(audio_ready), f.read()),
                        model="whisper-large-v3",
                        response_format="verbose_json",
                        language="fr"
                    )
                
                st.session_state.transcription_done = True
                st.session_state.transcript = transcript
                st.rerun()
                
            except Exception as e:
                st.error(f"Erreur: {str(e)}")
            finally:
                if audio_ready and os.path.exists(audio_ready):
                    os.remove(audio_ready)

# --- RÉSULTATS ---
if st.session_state.transcription_done and "transcript" in st.session_state:
    transcript = st.session_state.transcript
    
    st.markdown('<div class="result-box">', unsafe_allow_html=True)
    st.markdown("### ✅ **Transcription terminée !**")
    st.markdown(f'<div style="white-space: pre-wrap; font-size: 1.1rem;">{transcript.text}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📄 TXT", transcript.text, "transcription.txt", use_container_width=True)
    with col2:
        srt = generate_srt(transcript.segments)
        st.download_button("🎥 SRT", srt, "sous-titres.srt", use_container_width=True)
    
    st.markdown("### 📊 Stats")
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Segments", len(transcript.segments))
    with col2: st.metric("Langue", transcript.language)
    with col3: st.metric("Modèle", "Whisper Large-v3")

# --- FOOTER ---
st.markdown("""
<div style="text-align: center; padding: 3rem; opacity: 0.7;">
    <h4>AllayeVox Pro 🇲🇱 - Bamako Tech 2026</h4>
    <p>Whisper Large-v3 • 100% Malien • Précision ultime</p>
</div>
""", unsafe_allow_html=True)
