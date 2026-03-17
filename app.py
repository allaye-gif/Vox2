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

# --- DESIGN PREMIUM UI (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
    
    :root {
        --primary: #0F172A;
        --accent: #EA580C;
        --bg: #F8FAFC;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .stApp {
        background-color: var(--bg);
    }

    /* En-tête stylisée */
    .header-container {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 4rem 2rem;
        border-radius: 24px;
        color: white;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    
    .header-container::after {
        content: "";
        position: absolute;
        top: -50%;
        right: -10%;
        width: 400px;
        height: 400px;
        background: rgba(234, 88, 12, 0.1);
        filter: blur(80px);
        border-radius: 50%;
    }

    /* Cartes */
    .premium-card {
        background: white;
        padding: 2.5rem;
        border-radius: 20px;
        border: 1px solid rgba(226, 232, 240, 0.8);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.02);
        margin-bottom: 2rem;
    }

    /* Bouton personnalisé */
    .stButton>button {
        background: linear-gradient(90deg, #EA580C 0%, #F97316 100%);
        color: white !important;
        border: none !important;
        padding: 0.75rem 2rem !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        letter-spacing: 0.5px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.25) !important;
    }

    .stButton>button:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 8px 20px rgba(234, 88, 12, 0.4) !important;
    }

    /* Onglets stylisés */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #F1F5F9;
        padding: 6px;
        border-radius: 14px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 20px;
        background-color: transparent;
        border: none;
        color: #64748B;
    }

    .stTabs [aria-selected="true"] {
        background-color: white !important;
        color: var(--primary) !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
    }

    .mali-stripe {
        display: flex;
        height: 6px;
        width: 120px;
        margin-bottom: 15px;
        border-radius: 3px;
        overflow: hidden;
    }
    .s-green { background: #14B8A6; flex: 1; }
    .s-yellow { background: #FACC15; flex: 1; }
    .s-red { background: #EF4444; flex: 1; }

    /* Historique */
    .history-item {
        background: #F8FAFC;
        padding: 10px 15px;
        border-radius: 10px;
        margin-bottom: 8px;
        border-left: 3px solid #EA580C;
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
    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn", "-ar", "16000", "-ac", "1", "-ab", "64k",
        "-f", "mp3", output_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        st.error(f"Erreur technique (Audio) : {e.stderr.decode() if e.stderr else 'Inconnue'}")
        return None

def download_youtube(url, progress_bar):
    temp_dir = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex
    output_path = os.path.join(temp_dir, f"yt_{unique_id}")
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            p_raw = d.get('_percent_str', '0%').replace('%','')
            try:
                p_float = float(p_raw.strip()) / 100
                progress_bar.progress(p_float, text=f"Récupération des données YouTube : {p_raw}%")
            except: pass

    # OPTIONS ANTI-BLOCAGE (Correction Erreur 403)
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{output_path}.%(ext)s",
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        'nocheckcertificate': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            return f"{output_path}.mp3"
        except Exception as e:
            st.error(f"Erreur YouTube (403/Forbidden) : Le serveur YouTube bloque temporairement l'accès. Réessayez dans quelques minutes ou utilisez un fichier local.")
            return None

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 💠 AllayeVox 🇲🇱")
    st.markdown("<div class='mali-stripe'><div class='s-green'></div><div class='s-yellow'></div><div class='s-red'></div></div>", unsafe_allow_html=True)
    
    st.success("💎 Compte Pro Actif")
    
    with st.expander("🛠️ Administration"):
        new_key = st.text_input("Clé Groq (Optionnel)", type="password")
        if new_key: st.session_state.custom_api_key = new_key
    
    st.divider()
    st.subheader("🕒 Derniers travaux")
    if "history" not in st.session_state: st.session_state.history = []
    for item in reversed(st.session_state.history[-3:]):
        st.markdown(f"<div class='history-item'><small>{item['time']}</small><br><b>{item['name']}</b></div>", unsafe_allow_html=True)

# --- HEADER VITRINE ---
st.markdown(f"""
    <div class="header-container">
        <h1 style='font-size: 3rem; font-weight: 800; margin-bottom: 0.5rem;'>AllayeVox 🇲🇱</h1>
        <p style='font-size: 1.25rem; opacity: 0.9; font-weight: 300; max-width: 700px;'>
            L'excellence de la transcription automatique. Convertissez vos fichiers audio, vidéos et liens YouTube avec la puissance du moteur Whisper-V3.
        </p>
    </div>
""", unsafe_allow_html=True)

# --- ZONE PRINCIPALE ---
col_main, col_info = st.columns([2.5, 1])

with col_main:
    st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["📁 Importer un média", "🔗 Lien YouTube"])
    
    with t1:
        up_file = st.file_uploader("", type=["mp3", "m4a", "wav", "ogg", "opus", "mp4"])
        st.info("Formats recommandés : MP3 pour l'audio, MP4 pour la vidéo.")
        
    with t2:
        yt_url = st.text_input("", placeholder="https://www.youtube.com/watch?v=...")
        st.caption("Prise en charge des vidéos jusqu'à 2h.")
    
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🚀 DÉMARRER L'ANALYSE"):
        if not api_key:
            st.error("⚠️ Erreur : Clé API non configurée.")
        elif not up_file and not yt_url:
            st.warning("⚠️ Action requise : Veuillez fournir une source.")
        else:
            try:
                source_path = None
                
                # 1. Traitement Source
                if up_file:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(up_file.name)[1]) as tmp:
                        tmp.write(up_file.getvalue())
                        raw_input = tmp.name
                    with st.status("⚙️ Optimisation de l'audio...") as s:
                        source_path = process_audio(raw_input)
                        s.update(label="Audio optimisé", state="complete")
                
                elif yt_url:
                    prog = st.progress(0, text="Connexion aux serveurs YouTube...")
                    source_path = download_youtube(yt_url, prog)
                    prog.empty()
                
                # 2. Transcription
                if source_path:
                    with st.status("🤖 Intelligence Artificielle en action...") as status:
                        with open(source_path, "rb") as f:
                            res = client.audio.transcriptions.create(
                                file=(source_path, f.read()),
                                model="whisper-large-v3",
                                response_format="verbose_json"
                            )
                        status.update(label="Analyse terminée !", state="complete")
                    
                    st.balloons()
                    
                    # 3. Résultats
                    st.markdown("### ✨ Résultats")
                    res_c1, res_c2 = st.columns([2, 1])
                    with res_c1:
                        st.text_area("Transcription", res.text, height=350)
                    with res_c2:
                        st.download_button("Télécharger Texte (.txt)", res.text, "allayevox.txt", use_container_width=True)
                        srt = generate_srt(res.segments)
                        st.download_button("Télécharger Sous-titres (.srt)", srt, "allayevox.srt", use_container_width=True)
                    
                    st.session_state.history.append({"time": datetime.now().strftime("%H:%M"), "name": up_file.name if up_file else "YouTube"})
                    if os.path.exists(source_path): os.remove(source_path)

            except Exception as e:
                st.error(f"Une erreur est survenue : {str(e)}")

with col_info:
    st.markdown("""
        <div class='premium-card' style='padding: 1.5rem;'>
            <h4>🔥 Pourquoi AllayeVox ?</h4>
            <p style='font-size: 0.9rem; color: #64748B;'>
                <b>Vitesse :</b> Traitement jusqu'à 10x plus rapide que le temps réel.<br><br>
                <b>Multilingue :</b> Détection automatique de plus de 50 langues.<br><br>
                <b>Qualité Pro :</b> Utilisation des derniers modèles Large-V3.
            </p>
        </div>
    """, unsafe_allow_html=True)
    st.image("https://images.unsplash.com/photo-1589903308904-1010c2294adc?auto=format&fit=crop&q=80&w=400")

st.markdown("<center style='opacity: 0.5; padding: 2rem;'><small>Propulsé par Bamako Tech & Groq | AllayeVox 🇲🇱 v2.0</small></center>", unsafe_allow_html=True)
