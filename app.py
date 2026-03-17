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

# Configuration de la page
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

# --- DESIGN "PURE LIGHT" UI (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary-color: #0066FF;
        --text-main: #1D1D1F;
        --text-sub: #86868B;
        --bg-main: #FFFFFF;
        --bg-alt: #F5F5F7;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
        background-color: var(--bg-main) !important;
        color: var(--text-main);
    }

    .stApp {
        background-color: var(--bg-main);
    }

    /* En-tête Épurée */
    .header-section {
        padding: 4rem 1rem 2rem 1rem;
        text-align: center;
    }

    .hero-title {
        font-size: 3.5rem;
        font-weight: 700;
        color: var(--text-main);
        letter-spacing: -0.022em;
        margin-bottom: 0.5rem;
    }

    .mali-badge {
        display: inline-flex;
        align-items: center;
        background: #F2F2F7;
        padding: 5px 14px;
        border-radius: 40px;
        color: #1D1D1F;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 1rem;
    }

    /* Cartes Minimalistes */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
        background-color: transparent;
        border-bottom: 1px solid #E5E5E5;
        gap: 30px;
        margin-bottom: 2rem;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        color: var(--text-sub);
        font-weight: 500;
        font-size: 1.1rem;
        padding-bottom: 10px;
    }

    .stTabs [aria-selected="true"] {
        color: var(--primary-color) !important;
        border-bottom: 2px solid var(--primary-color) !important;
    }

    /* Bouton Pro */
    .stButton>button {
        background-color: var(--text-main) !important;
        color: white !important;
        height: 56px !important;
        border-radius: 12px !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.2s ease !important;
        margin-top: 1rem;
    }

    .stButton>button:hover {
        background-color: #323232 !important;
        transform: translateY(-1px);
    }

    /* Inputs */
    .stTextInput>div>div>input {
        background: var(--bg-alt) !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 15px !important;
        font-size: 1rem;
    }

    .stFileUploader section {
        background-color: var(--bg-alt) !important;
        border: 2px dashed #D2D2D7 !important;
        border-radius: 14px !important;
    }

    /* Hide UI Streamlit */
    #MainMenu, header, footer {visibility: hidden;}

    .footer-note {
        text-align: center;
        margin-top: 5rem;
        color: var(--text-sub);
        font-size: 0.8rem;
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
    output_path = os.path.join(tempfile.gettempdir(), f"proc_{uuid.uuid4().hex}.mp3")
    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn", "-ar", "16000", "-ac", "1", "-ab", "64k",
        "-f", "mp3", output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        st.error(f"Erreur de conversion audio : {e.stderr.decode() if e.stderr else 'Inconnue'}")
        return None

def download_youtube(url):
    temp_dir = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex
    output_path = os.path.join(temp_dir, f"yt_{unique_id}")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{output_path}.%(ext)s",
        'quiet': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'nocheckcertificate': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            return f"{output_path}.mp3"
        except Exception:
            return None

# --- CONTENU INTERFACE ---

st.markdown("""
    <div class="header-section">
        <div class="mali-badge">🇲🇱 AllayeVox - Bamako Tech</div>
        <h1 class="hero-title">Transcription Intelligente</h1>
        <p style="color: #86868B; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
            Transformez vos fichiers audio et vidéos en texte avec la plus haute précision disponible sur le marché.
        </p>
    </div>
""", unsafe_allow_html=True)

# Main columns
_, main_col, _ = st.columns([1, 2, 1])

with main_col:
    t1, t2 = st.tabs(["Fichier Audio/Vidéo", "Lien YouTube"])
    
    with t1:
        st.markdown("<br>", unsafe_allow_html=True)
        src_file = st.file_uploader("", type=["mp3", "m4a", "wav", "ogg", "opus", "mp4"])
        st.caption("Prend en charge les formats WhatsApp, dictaphones et vidéos.")
        
    with t2:
        st.markdown("<br>", unsafe_allow_html=True)
        yt_url = st.text_input("", placeholder="Collez le lien YouTube ici...")
        st.warning("⚠️ Note sur YouTube : Google bloque parfois les serveurs de Cloud. Si une erreur 403 survient, téléchargez l'audio de la vidéo et importez-la dans l'onglet 'Fichier'.")

    if st.button("Lancer la transcription"):
        if not api_key:
            st.error("Clé API non trouvée dans les Secrets.")
        elif not src_file and not yt_url:
            st.toast("Source manquante.")
        else:
            try:
                audio_path = None
                
                if src_file:
                    with st.spinner("Traitement du fichier..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(src_file.name)[1]) as f:
                            f.write(src_file.getvalue())
                            audio_path = process_audio(f.name)
                
                elif yt_url:
                    with st.spinner("Récupération de l'audio YouTube..."):
                        audio_path = download_youtube(yt_url)
                        if not audio_path:
                            st.error("🛑 Limitation YouTube (403) : Cette vidéo est bloquée par Google. Veuillez télécharger l'audio manuellement et utiliser l'onglet 'Fichier'.")
                
                if audio_path:
                    with st.status("Analyse par l'IA...", expanded=True) as status:
                        st.write("Écoute du contenu...")
                        with open(audio_path, "rb") as f:
                            res = client.audio.transcriptions.create(
                                file=(audio_path, f.read()),
                                model="whisper-large-v3",
                                response_format="verbose_json"
                            )
                        status.update(label="Analyse terminée", state="complete")
                    
                    st.balloons()
                    
                    st.markdown("### Transcription")
                    st.markdown(f'<div style="background: #F5F5F7; padding: 25px; border-radius: 12px; border: 1px solid #E5E5E5; color: #1D1D1F; line-height: 1.7;">{res.text}</div>', unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button("Télécharger le texte (.txt)", res.text, "transcription.txt", use_container_width=True)
                    with c2:
                        srt = generate_srt(res.segments)
                        st.download_button("Télécharger sous-titres (.srt)", srt, "subtitles.srt", use_container_width=True)
                    
                    if os.path.exists(audio_path): os.remove(audio_path)

            except Exception as e:
                st.error(f"Une erreur système est survenue : {str(e)}")

st.markdown("""
    <div class="footer-note">
        AllayeVox Pro • Édition Spéciale Mali • Whisper V3 Large
    </div>
""", unsafe_allow_html=True)
