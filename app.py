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

# --- DESIGN ULTRA-PREMIUM (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    
    :root {
        --primary: #0F172A;
        --accent: #F59E0B;
        --glass: rgba(255, 255, 255, 0.03);
        --glass-border: rgba(255, 255, 255, 0.1);
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #020617 !important;
        color: #F8FAFC;
    }

    .stApp {
        background: radial-gradient(circle at top right, #1E1B4B, #020617);
    }

    /* En-tête Hero */
    .hero-section {
        text-align: center;
        padding: 5rem 1rem 3rem 1rem;
    }

    .hero-title {
        font-size: 5rem;
        font-weight: 800;
        background: linear-gradient(to right, #F8FAFC, #94A3B8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
        letter-spacing: -2px;
    }

    .mali-badge {
        display: inline-flex;
        align-items: center;
        background: rgba(20, 184, 166, 0.1);
        border: 1px solid rgba(20, 184, 166, 0.2);
        padding: 6px 16px;
        border-radius: 100px;
        color: #2DD4BF;
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 2rem;
    }

    /* Container de verre */
    .glass-card {
        background: rgba(30, 41, 59, 0.5);
        backdrop-filter: blur(20px);
        border: 1px solid var(--glass-border);
        border-radius: 32px;
        padding: 3rem;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }

    /* Tabs Custom */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.5);
        padding: 8px;
        border-radius: 16px;
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 12px;
        color: #94A3B8;
        font-weight: 600;
        border: none;
        transition: all 0.3s;
    }

    .stTabs [aria-selected="true"] {
        background: #F59E0B !important;
        color: #020617 !important;
    }

    /* Bouton d'action */
    .stButton>button {
        width: 100%;
        background: #F8FAFC !important;
        color: #020617 !important;
        height: 64px !important;
        border-radius: 18px !important;
        font-size: 1.2rem !important;
        font-weight: 800 !important;
        border: none !important;
        margin-top: 2rem !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
    }

    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 40px rgba(248, 250, 252, 0.2) !important;
    }

    /* Inputs */
    .stTextInput>div>div>input {
        background: rgba(15, 23, 42, 0.5) !important;
        border: 1px solid var(--glass-border) !important;
        color: white !important;
        border-radius: 14px !important;
        height: 55px;
    }
    
    /* Footer */
    .footer-text {
        text-align: center;
        padding: 4rem;
        color: #475569;
        font-size: 0.8rem;
        letter-spacing: 1px;
    }
    
    /* Hide Streamlit Header/Footer */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
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
    output_path = os.path.join(tempfile.gettempdir(), f"clean_{uuid.uuid4().hex}.mp3")
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

def download_youtube(url, progress_bar):
    temp_dir = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex
    output_path = os.path.join(temp_dir, f"allaye_{unique_id}")
    
    # PARAMÈTRES AVANCÉS POUR CONTOURNER LA 403
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{output_path}.%(ext)s",
        'quiet': True,
        'no_warnings': True,
        # Ajout de cookies et d'en-têtes plus agressifs
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'nocheckcertificate': True,
        'geo_bypass': True,
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # On tente d'abord de récupérer les infos sans télécharger pour voir si c'est bloqué
            ydl.extract_info(url, download=True)
            return f"{output_path}.mp3"
        except Exception as e:
            # Si erreur 403, on propose une alternative explicative
            st.error("🛑 Limitation YouTube détectée (Erreur 403).")
            st.warning("Le serveur de déploiement est actuellement restreint par YouTube. Solution : Téléchargez l'audio de la vidéo sur votre appareil et importez-le via l'onglet 'Fichiers'.")
            return None

# --- UI CONTENT ---

# Hero Header
st.markdown("""
    <div class="hero-section">
        <div class="mali-badge">🇲🇱 ALLAYEVOX PRO VERSION</div>
        <h1 class="hero-title">Transcrivez l'impossible.</h1>
        <p style="color: #94A3B8; font-size: 1.2rem; max-width: 800px; margin: 0 auto;">
            La puissance du moteur Whisper-V3 Large dans une interface raffinée. 
            Pensé pour les créateurs maliens.
        </p>
    </div>
""", unsafe_allow_html=True)

# Main Container
col_l, col_c, col_r = st.columns([1, 4, 1])

with col_c:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    tab_file, tab_yt = st.tabs(["📁 FICHIER LOCAL", "🌐 YOUTUBE LINK"])
    
    with tab_file:
        st.markdown("<br>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("", type=["mp3", "m4a", "wav", "ogg", "opus", "mp4"])
        st.caption("Fichiers audio ou vidéo (WhatsApp, Dictaphone, etc.)")
        
    with tab_yt:
        st.markdown("<br>", unsafe_allow_html=True)
        yt_link = st.text_input("", placeholder="Collez votre lien YouTube ici...")
        st.info("💡 Note : Si le lien est bloqué, utilisez l'onglet Fichier avec un enregistrement.")

    if st.button("DÉMARRER LA MAGIE"):
        if not api_key:
            st.error("Clé API Groq manquante dans les Secrets.")
        elif not uploaded_file and not yt_link:
            st.toast("Veuillez sélectionner une source.")
        else:
            try:
                final_audio = None
                
                # Phase 1: Acquisition
                if uploaded_file:
                    with st.spinner("📦 Préparation du fichier..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as t:
                            t.write(uploaded_file.getvalue())
                            final_audio = process_audio(t.name)
                elif yt_link:
                    with st.spinner("📡 Connexion à YouTube..."):
                        p_bar = st.progress(0)
                        final_audio = download_youtube(yt_link, p_bar)
                        p_bar.empty()

                # Phase 2: Transcription
                if final_audio:
                    with st.status("🔮 Intelligence Artificielle en cours...", expanded=True) as status:
                        st.write("Analyse des ondes sonores...")
                        start = time.time()
                        with open(final_audio, "rb") as f:
                            response = client.audio.transcriptions.create(
                                file=(final_audio, f.read()),
                                model="whisper-large-v3",
                                response_format="verbose_json"
                            )
                        duration = round(time.time() - start, 1)
                        status.update(label=f"Succès ! ({duration}s)", state="complete")
                    
                    st.balloons()
                    
                    # Phase 3: Display
                    st.markdown("### 📝 Résultat de l'analyse")
                    st.markdown(f'<div style="background: rgba(15, 23, 42, 0.8); padding: 20px; border-radius: 12px; border: 1px solid var(--glass-border); line-height: 1.6;">{response.text}</div>', unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button("📥 Télécharger (.txt)", response.text, "transcription.txt", use_container_width=True)
                    with c2:
                        srt = generate_srt(response.segments)
                        st.download_button("🎬 Sous-titres (.srt)", srt, "subtitles.srt", use_container_width=True)
                    
                    # Cleanup
                    if os.path.exists(final_audio): os.remove(final_audio)

            except Exception as e:
                st.error(f"Une erreur système est survenue : {str(e)}")

    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
    <div class="footer-text">
        &copy; 2024 ALLAYEVOX ML • ENGINE WHISPER V3 • POWERED BY GROQ
    </div>
""", unsafe_allow_html=True)

# Sidebar Ultra-Minimal
with st.sidebar:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("### ⚙️ OPTIONS")
    st.toggle("Auto-correction ponctuation", value=True)
    st.toggle("Traduction vers l'Anglais", value=False)
    
    with st.expander("Clé API"):
        custom = st.text_input("Overwrite Key", type="password")
        if custom: st.session_state.custom_api_key = custom
