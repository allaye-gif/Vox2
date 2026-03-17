import streamlit as st
import os
import tempfile
import subprocess
import uuid
from groq import Groq
import yt_dlp
from datetime import timedelta

# ==============================
# CONFIG
# ==============================

def get_api_key():
    return st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))

st.set_page_config(
    page_title="AllayeVox Pro 🇲🇱",
    page_icon="🎙️",
    layout="wide"
)

api_key = get_api_key()
client = Groq(api_key=api_key) if api_key else None


# ==============================
# DESIGN PREMIUM
# ==============================

st.markdown("""
<style>
body {
    background: linear-gradient(180deg, #0f172a, #020617);
    color: white;
    font-family: 'Inter', sans-serif;
}

.block-container {
    padding-top: 2rem;
}

.hero {
    text-align: center;
    padding: 4rem 1rem;
}

.hero h1 {
    font-size: 3.5rem;
    font-weight: 800;
}

.card {
    background: rgba(255,255,255,0.05);
    padding: 2rem;
    border-radius: 20px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.1);
}

.stButton button {
    background: linear-gradient(90deg, #2563eb, #06b6d4);
    border: none;
    border-radius: 12px;
    height: 55px;
    font-weight: bold;
    font-size: 1.1rem;
    color: white;
    width: 100%;
}

.result {
    background: white;
    color: black;
    padding: 2rem;
    border-radius: 15px;
}
</style>
""", unsafe_allow_html=True)


# ==============================
# UTILS
# ==============================

def format_srt_timestamp(seconds):
    td = timedelta(seconds=seconds)
    return str(td)[:-3].replace(".", ",")

def generate_srt(segments):
    srt = ""
    for i, seg in enumerate(segments):
        srt += f"{i+1}\n{format_srt_timestamp(seg['start'])} --> {format_srt_timestamp(seg['end'])}\n{seg['text']}\n\n"
    return srt

def process_audio(input_path):
    output = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.mp3")
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn", "-ac", "1", "-ar", "16000",
        output
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output


# ==============================
# YOUTUBE ULTRA ROBUSTE
# ==============================

def download_youtube(url):
    temp_dir = tempfile.gettempdir()
    uid = uuid.uuid4().hex
    out = os.path.join(temp_dir, f"{uid}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': out,
        'quiet': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'cookiefile': 'cookies.txt',  # 🔥 important
        'http_headers': {
            'User-Agent': 'Mozilla/5.0'
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return os.path.join(temp_dir, f"{uid}.mp3")
    except Exception as e:
        return None


# ==============================
# UI
# ==============================

st.markdown("""
<div class="hero">
<h1>🎙️ AllayeVox Pro</h1>
<p>Transcription IA ultra rapide • YouTube • Audio • Vidéo</p>
</div>
""", unsafe_allow_html=True)


col1, col2, col3 = st.columns([1,2,1])

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📁 Fichier", "🔗 YouTube"])

    uploaded = None
    url = None

    with tab1:
        uploaded = st.file_uploader("Importer fichier", type=["mp3","wav","mp4"])

    with tab2:
        url = st.text_input("Lien YouTube")

    if st.button("🚀 Transcrire maintenant"):
        if not api_key:
            st.error("Clé API manquante")
        else:
            audio = None

            # Upload
            if uploaded:
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.write(uploaded.read())
                audio = process_audio(tmp.name)

            # YouTube
            elif url:
                with st.spinner("Téléchargement YouTube..."):
                    audio = download_youtube(url)

            if not audio:
                st.error("Erreur récupération audio")
            else:
                with st.spinner("Transcription IA en cours..."):
                    with open(audio, "rb") as f:
                        result = client.audio.transcriptions.create(
                            file=(audio, f.read()),
                            model="whisper-large-v3",
                            response_format="verbose_json"
                        )

                st.success("Transcription terminée")

                st.markdown('<div class="result">', unsafe_allow_html=True)
                st.write(result.text)
                st.markdown('</div>', unsafe_allow_html=True)

                colA, colB = st.columns(2)

                with colA:
                    st.download_button("📄 TXT", result.text, "transcript.txt")

                with colB:
                    st.download_button("🎬 SRT", generate_srt(result.segments), "subtitles.srt")

                os.remove(audio)

    st.markdown('</div>', unsafe_allow_html=True)
