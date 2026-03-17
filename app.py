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
# DESIGN
# ==============================

st.markdown("""
<style>
body {
    background: linear-gradient(180deg, #0f172a, #020617);
    color: white;
    font-family: 'Inter', sans-serif;
}
.hero {
    text-align: center;
    padding: 3rem;
}
.card {
    background: rgba(255,255,255,0.05);
    padding: 2rem;
    border-radius: 20px;
}
.stButton button {
    background: linear-gradient(90deg, #2563eb, #06b6d4);
    border-radius: 10px;
    height: 50px;
    font-weight: bold;
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

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output
    except Exception as e:
        st.error("❌ Erreur FFmpeg")
        st.code(str(e))
        return None

# ==============================
# YOUTUBE DEBUG VERSION
# ==============================

def download_youtube(url):
    temp_dir = tempfile.gettempdir()
    uid = uuid.uuid4().hex
    out = os.path.join(temp_dir, f"{uid}.%(ext)s")

    cookie_path = os.path.join(os.getcwd(), "cookies.txt")

    st.write("📂 Dossier courant :", os.getcwd())
    st.write("📄 cookies.txt existe ?", os.path.exists(cookie_path))

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out,
        'quiet': False,
        'noplaylist': True,

        # cookies
        'cookiefile': cookie_path,

        'http_headers': {
            'User-Agent': 'Mozilla/5.0'
        },

        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]
    }

    try:
        st.info("🚀 Téléchargement YouTube en cours...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        final_path = os.path.join(temp_dir, f"{uid}.mp3")

        st.write("📁 Fichier attendu :", final_path)
        st.write("📁 Existe ?", os.path.exists(final_path))

        if os.path.exists(final_path):
            return final_path
        else:
            st.error("❌ MP3 non généré")
            return None

    except Exception as e:
        st.error("❌ ERREUR YT-DLP :")
        st.code(str(e))
        return None

# ==============================
# UI
# ==============================

st.markdown("""
<div class="hero">
<h1>🎙️ AllayeVox Pro</h1>
<p>Transcription IA • YouTube • Audio</p>
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
            st.error("❌ Clé API manquante")
            st.stop()

        audio = None

        # ================= FILE =================
        if uploaded:
            with st.spinner("Préparation audio..."):
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.write(uploaded.read())
                audio = process_audio(tmp.name)

        # ================= YOUTUBE =================
        elif url:
            audio = download_youtube(url)

        else:
            st.warning("⚠️ Ajoute un fichier ou un lien")
            st.stop()

        # ================= ERREUR =================
        if not audio:
            st.error("❌ Erreur récupération audio")
            st.stop()

        # ================= TRANSCRIPTION =================
        with st.spinner("🤖 Transcription IA en cours..."):
            try:
                with open(audio, "rb") as f:
                    result = client.audio.transcriptions.create(
                        file=(audio, f.read()),
                        model="whisper-large-v3",
                        response_format="verbose_json"
                    )
            except Exception as e:
                st.error("❌ Erreur IA")
                st.code(str(e))
                st.stop()

        st.success("✅ Transcription terminée")

        st.markdown('<div class="result">', unsafe_allow_html=True)
        st.write(result.text)
        st.markdown('</div>', unsafe_allow_html=True)

        colA, colB = st.columns(2)

        with colA:
            st.download_button("📄 TXT", result.text, "transcript.txt")

        with colB:
            st.download_button("🎬 SRT", generate_srt(result.segments), "subtitles.srt")

        try:
            os.remove(audio)
        except:
            pass

    st.markdown('</div>', unsafe_allow_html=True)
