import streamlit as st
import os
import tempfile
import time
import subprocess
from groq import Groq
import yt_dlp
from datetime import datetime, timedelta

# --- CONFIGURATION ET SÉCURITÉ ---
# --- CONFIGURATION ET SÉCURITÉ ---
def get_api_key():
    # On ne met plus la clé ici ! 
    # Streamlit ira la chercher dans tes "Secrets" sur le Web
    if "GROQ_API_KEY" in st.secrets:
        return st.secrets["GROQ_API_KEY"]
    return os.environ.get("GROQ_API_KEY", "")

st.set_page_config(
    page_title="VoxWhisper Pro - Bamako Tech",
    page_icon="🎙️",
    layout="wide"
)

# --- INITIALISATION ---
api_key = get_api_key()
# Possibilité de surcharger la clé via l'UI pour le créateur
if "custom_api_key" in st.session_state and st.session_state.custom_api_key:
    api_key = st.session_state.custom_api_key

client = Groq(api_key=api_key) if api_key else None

# --- FONCTIONS UTILITAIRES ---

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
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f"conv_{int(time.time())}.mp3")
    file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    bitrate = "48k" if file_size_mb > 20 else "128k"
    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn", "-ar", "16000", "-ac", "1",
        "-b:a", bitrate, output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        return output_path
    except: return None

def download_youtube(url):
    temp_dir = tempfile.gettempdir()
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, 'yt_%(id)s.%(ext)s'),
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}],
        'quiet': True,
        'no_warnings': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info).replace(info['ext'], 'mp3')

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: #f0f2f6; border-radius: 10px 10px 0 0;
    }
    .stTabs [aria-selected="true"] { background-color: #EA580C !important; color: white !important; }
    .history-card {
        padding: 12px; border-radius: 10px; background: white; margin-bottom: 8px;
        border-left: 4px solid #EA580C; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR & AUTHENTIFICATION CRÉATEUR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3602/3602051.png", width=70)
    st.title("VoxWhisper Pro")
    
    # Détection automatique Créateur (simulation par défaut à True pour toi)
    if "is_subscribed" not in st.session_state:
        st.session_state.is_subscribed = True # Activé par défaut pour le packager

    if st.session_state.is_subscribed:
        st.success("💎 Accès Privilégié Actif")
    else:
        st.warning("💳 Mode Limité")
        if st.button("Activer Premium"):
            st.session_state.is_subscribed = True
            st.rerun()
    
    with st.expander("🛠️ Paramètres Admin"):
        new_key = st.text_input("Modifier Clé API Groq", type="password")
        if new_key:
            st.session_state.custom_api_key = new_key
            st.toast("Clé mise à jour !")

    st.divider()
    st.subheader("🕒 Historique")
    if "history" not in st.session_state: st.session_state.history = []
    for item in reversed(st.session_state.history[-5:]):
        st.markdown(f"<div class='history-card'><small>{item['time']}</small><br><b>{item['name']}</b></div>", unsafe_allow_html=True)

# --- MAIN ---
st.title("VoxWhisper Pro 🇲🇱")
st.markdown("Solution de transcription haute fidélité optimisée pour le Mali.")

if not st.session_state.is_subscribed:
    st.info("👋 Veuillez activer l'accès pour continuer.")
else:
    t1, t2 = st.tabs(["📤 Fichier local", "🔗 YouTube"])
    with t1:
        up = st.file_uploader("Audio (WhatsApp, MP3, WAV...)", type=["mp3", "m4a", "wav", "ogg", "opus"])
    with t2:
        url = st.text_input("Lien de la vidéo")

    if st.button("⚡ DÉMARRER LA TRANSCRIPTION"):
        if not up and not url:
            st.error("Veuillez sélectionner une source.")
            st.stop()
            
        source = None
        name = ""
        try:
            with st.status("Analyse et conversion...") as status:
                if up:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(up.name)[1]) as tmp:
                        tmp.write(up.getvalue())
                        source = tmp.name
                    name = up.name
                elif url:
                    source = download_youtube(url)
                    name = "YouTube Video"
                
                if source:
                    proc = process_audio(source)
                    st.write("🚀 Envoi vers l'IA Groq...")
                    start = time.time()
                    with open(proc, "rb") as f:
                        resp = client.audio.transcriptions.create(
                            file=(proc, f.read()),
                            model="whisper-large-v3",
                            response_format="verbose_json"
                        )
                    dur = time.time() - start
                    status.update(label=f"Transcription réussie en {dur:.1f}s", state="complete")
                    
                    st.divider()
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.subheader("📝 Transcription")
                        st.text_area("Texte intégral", resp.text, height=400)
                    with col2:
                        st.subheader("💾 Exportation")
                        st.download_button("Télécharger Texte (.txt)", resp.text, f"{name}.txt", use_container_width=True)
                        srt = generate_srt(resp.segments)
                        st.download_button("Télécharger Sous-titres (.srt)", srt, f"{name}.srt", use_container_width=True)
                    
                    st.session_state.history.append({"time": datetime.now().strftime("%H:%M"), "name": name})
                    
                    # Nettoyage
                    if os.path.exists(source): os.remove(source)
                    if os.path.exists(proc): os.remove(proc)
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")

st.markdown("<br><hr><center><small>VoxWhisper Pro © 2024 | Version Créateur</small></center>", unsafe_allow_html=True)
