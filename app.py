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

# --- DESIGN "ULTRA LIGHT" PREMIUM (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary: #0066FF;
        --text-main: #1D1D1F;
        --text-sub: #6E6E73;
        --bg-body: #FBFBFD;
        --border: #D2D2D7;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
        background-color: var(--bg-body) !important;
        color: var(--text-main);
    }

    .stApp {
        background-color: var(--bg-body);
    }

    /* Header */
    .header-container {
        padding: 5rem 1rem 3rem 1rem;
        text-align: center;
        background: white;
        border-bottom: 1px solid var(--border);
        margin-bottom: 3rem;
    }

    .mali-badge {
        display: inline-block;
        background: #F5F5F7;
        padding: 6px 16px;
        border-radius: 50px;
        font-size: 0.8rem;
        font-weight: 600;
        color: #1D1D1F;
        margin-bottom: 1rem;
        border: 1px solid var(--border);
    }

    .hero-title {
        font-size: 4rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin-bottom: 1rem;
        color: var(--text-main);
    }

    /* Cards */
    .action-card {
        background: white;
        padding: 2.5rem;
        border-radius: 20px;
        border: 1px solid var(--border);
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
    }

    /* Custom Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background: #F5F5F7;
        padding: 5px;
        border-radius: 12px;
        margin-bottom: 2rem;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 25px;
        background: transparent !important;
        border: none !important;
        color: var(--text-sub);
    }

    .stTabs [aria-selected="true"] {
        background: white !important;
        color: var(--primary) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }

    /* Button */
    .stButton>button {
        background: var(--primary) !important;
        color: white !important;
        width: 100%;
        height: 60px !important;
        border-radius: 14px !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        border: none !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        margin-top: 1.5rem;
    }

    .stButton>button:hover {
        background: #0052CC !important;
        transform: scale(1.01);
    }

    /* Result Area */
    .result-box {
        background: white;
        border: 1px solid var(--border);
        padding: 2rem;
        border-radius: 16px;
        margin-top: 2rem;
        line-height: 1.8;
        font-size: 1.05rem;
    }

    /* Streamlit UI Hidden */
    #MainMenu, header, footer {visibility: hidden;}
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
        "-vn", "-ar", "16000", "-ac", "1", "-ab", "128k",
        "-f", "mp3", output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        return output_path
    except Exception as e:
        st.error(f"Erreur technique audio : {str(e)}")
        return None

def download_youtube_pro(url):
    """Extraction audio robuste via yt-dlp (Méthode Ultimate)"""
    temp_dir = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex
    output_tmpl = os.path.join(temp_dir, f"yt_{unique_id}.%(ext)s")
    
    # Options de contournement avancées
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_tmpl,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        # Simulation d'un navigateur réel pour éviter les 403
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Sec-Fetch-Mode': 'navigate',
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            return os.path.join(temp_dir, f"yt_{unique_id}.mp3")
        except Exception as e:
            return str(e)

# --- INTERFACE ---

st.markdown("""
    <div class="header-container">
        <div class="mali-badge">🇲🇱 ÉDITION BAMAKO TECH</div>
        <h1 class="hero-title">AllayeVox Pro</h1>
        <p style="color: var(--text-sub); font-size: 1.2rem; max-width: 700px; margin: 0 auto;">
            La solution ultime de transcription motorisée par Whisper-V3 Large. 
            Précision maximale, sans compromis.
        </p>
    </div>
""", unsafe_allow_html=True)

_, col, _ = st.columns([1, 2, 1])

with col:
    st.markdown('<div class="action-card">', unsafe_allow_html=True)
    
    tab_f, tab_y = st.tabs(["📁 FICHIER", "🔗 YOUTUBE"])
    
    with tab_f:
        st.markdown("<br>", unsafe_allow_html=True)
        up = st.file_uploader("", type=["mp3", "m4a", "wav", "mp4"])
        st.caption("Importez n'importe quel média audio ou vidéo.")
        
    with tab_y:
        st.markdown("<br>", unsafe_allow_html=True)
        url = st.text_input("", placeholder="Lien de la vidéo YouTube...")
        st.info("💡 Méthode d'extraction haute fidélité activée.")

    if st.button("LANCER L'ANALYSE"):
        if not api_key:
            st.error("Clé API Groq manquante.")
        elif not up and not url:
            st.warning("Veuillez fournir une source.")
        else:
            try:
                audio_ready = None
                
                if up:
                    with st.spinner("Préparation du média..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(up.name)[1]) as t:
                            t.write(up.getvalue())
                            audio_ready = process_audio(t.name)
                
                elif url:
                    with st.spinner("Extraction audio YouTube (Bypass)..."):
                        result = download_youtube_pro(url)
                        if os.path.exists(result):
                            audio_ready = result
                        else:
                            st.error(f"Blocage YouTube persistant : {result}")
                            st.info("Conseil : Si l'erreur 403 persiste, téléchargez l'audio localement et utilisez l'onglet 'FICHIER'.")

                if audio_ready:
                    with st.status("Intelligence Artificielle en cours...", expanded=True) as status:
                        st.write("Modèle Whisper-V3 Large activé...")
                        with open(audio_ready, "rb") as f:
                            transcript = client.audio.transcriptions.create(
                                file=(audio_ready, f.read()),
                                model="whisper-large-v3",
                                response_format="verbose_json"
                            )
                        status.update(label="Transcription terminée !", state="complete")
                    
                    st.balloons()
                    
                    st.markdown("### 📄 Transcription Finale")
                    st.markdown(f'<div class="result-box">{transcript.text}</div>', unsafe_allow_html=True)
                    
                    d1, d2 = st.columns(2)
                    with d1:
                        st.download_button("Télécharger Texte", transcript.text, "vox_result.txt", use_container_width=True)
                    with d2:
                        srt_data = generate_srt(transcript.segments)
                        st.download_button("Télécharger Sous-titres", srt_data, "vox_result.srt", use_container_width=True)
                    
                    if os.path.exists(audio_ready): os.remove(audio_ready)

            except Exception as e:
                st.error(f"Erreur système : {str(e)}")

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
    <div style="text-align: center; margin-top: 4rem; color: #8E8E93; font-size: 0.8rem; padding-bottom: 4rem;">
        ALLAYEVOX V3 • WHISPER LARGE ENGINE • PROPRIÉTÉ DE BAMAKO TECH 🇲🇱
    </div>
""", unsafe_allow_html=True)
