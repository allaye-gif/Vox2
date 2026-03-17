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
    page_title="AllayeVox Pro 🇲🇱",
    page_icon="🎙️",
    layout="wide"
)

# --- INITIALISATION ---
api_key = get_api_key()
# Si l'utilisateur saisit une clé manuellement, elle écrase la clé configurée
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

def download_youtube_pro(url, cookies_file=None):
    """Extraction audio robuste via yt-dlp avec fallback et gestion d'erreurs avancée."""
    temp_dir = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex
    output_tmpl = os.path.join(temp_dir, f"yt_{unique_id}.%(ext)s")
    
    # Options de base
    ydl_opts = {
        'outtmpl': output_tmpl,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'nocheckcertificate': True,
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
    
    # Si un fichier cookies est fourni, l'ajouter
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts['cookiefile'] = cookies_file
    
    # Liste des formats à essayer en ordre de priorité
    formats_to_try = [
        'bestaudio/best',
        'bestaudio[ext=m4a]/bestaudio',
        'worstaudio/worst',
        'best'  # dernier recours : vidéo + extraction audio
    ]
    
    last_error = None
    for fmt in formats_to_try:
        try:
            st.write(f"Tentative avec le format : {fmt}")
            ydl_opts['format'] = fmt
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                # Vérifier que le fichier a bien été généré
                expected_file = os.path.join(temp_dir, f"yt_{unique_id}.mp3")
                if os.path.exists(expected_file):
                    return expected_file
                else:
                    # Parfois le nom peut varier, on cherche un fichier avec le bon préfixe
                    for f in os.listdir(temp_dir):
                        if f.startswith(f"yt_{unique_id}") and f.endswith('.mp3'):
                            return os.path.join(temp_dir, f)
                    raise Exception("Fichier audio non trouvé après extraction")
        except Exception as e:
            last_error = e
            continue  # essayer le format suivant
    
    # Si toutes les tentatives échouent, retourner l'erreur
    return str(last_error)

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

# --- BARRE LATÉRALE POUR CONFIGURATION AVANCÉE ---
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    # Saisie manuelle de la clé API Groq (optionnelle)
    custom_key = st.text_input("Clé API Groq (optionnelle)", type="password", 
                                help="Si vous avez votre propre clé, vous pouvez la saisir ici. Elle remplace la clé configurée.")
    if custom_key:
        st.session_state.custom_api_key = custom_key
        # Mettre à jour le client
        client = Groq(api_key=custom_key)
    else:
        # Si la clé est effacée, on revient à la clé configurée
        if "custom_api_key" in st.session_state:
            del st.session_state.custom_api_key
        client = Groq(api_key=api_key) if api_key else None
    
    st.markdown("---")
    st.markdown("### 🔧 Options YouTube")
    st.caption("Pour débloquer les vidéos restreintes, vous pouvez fournir un fichier cookies.txt (exporté depuis votre navigateur).")
    cookies_file = st.file_uploader("Fichier cookies.txt (optionnel)", type=["txt"], 
                                    help="Exportez vos cookies YouTube au format Netscape.")
    if cookies_file:
        # Sauvegarder temporairement le fichier cookies
        cookies_path = os.path.join(tempfile.gettempdir(), f"cookies_{uuid.uuid4().hex}.txt")
        with open(cookies_path, "wb") as f:
            f.write(cookies_file.getvalue())
        st.session_state.cookies_path = cookies_path
        st.success("Fichier cookies chargé.")
    else:
        if "cookies_path" in st.session_state:
            os.remove(st.session_state.cookies_path)  # nettoyage
            del st.session_state.cookies_path

_, col, _ = st.columns([1, 2, 1])

with col:
    st.markdown('<div class="action-card">', unsafe_allow_html=True)
    
    tab_f, tab_y = st.tabs(["📁 FICHIER", "🔗 YOUTUBE"])
    
    with tab_f:
        st.markdown("<br>", unsafe_allow_html=True)
        up = st.file_uploader("", type=["mp3", "m4a", "wav", "mp4", "mov", "avi"])
        st.caption("Importez n'importe quel média audio ou vidéo.")
        
    with tab_y:
        st.markdown("<br>", unsafe_allow_html=True)
        url = st.text_input("", placeholder="Lien de la vidéo YouTube...")
        st.info("💡 L'extraction utilise plusieurs méthodes de contournement. Si une erreur persiste, utilisez l'onglet FICHIER après téléchargement manuel.")
    
    if st.button("LANCER L'ANALYSE"):
        if not api_key and not custom_key:
            st.error("Clé API Groq manquante. Veuillez en saisir une dans la barre latérale ou configurer la clé par défaut.")
        elif not up and not url:
            st.warning("Veuillez fournir une source (fichier ou lien YouTube).")
        else:
            try:
                audio_ready = None
                
                if up:
                    with st.status("Préparation du média...", expanded=True) as status:
                        status.write("Sauvegarde du fichier...")
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(up.name)[1]) as t:
                            t.write(up.getvalue())
                            tmp_path = t.name
                        status.write("Conversion audio (16kHz, mono)...")
                        audio_ready = process_audio(tmp_path)
                        if audio_ready:
                            status.update(label="Fichier prêt", state="complete")
                        else:
                            status.update(label="Erreur de conversion", state="error")
                            st.stop()
                
                elif url:
                    # Récupérer le chemin des cookies s'ils existent
                    cookies_path = st.session_state.get("cookies_path", None)
                    with st.status("Extraction audio YouTube...", expanded=True) as status:
                        status.write("Connexion à YouTube...")
                        # Simuler une progression visuelle
                        progress_bar = st.progress(0)
                        for i in range(1, 5):
                            time.sleep(0.3)  # juste pour l'effet
                            progress_bar.progress(i * 25)
                            status.write(f"Tentative {i}...")
                        
                        result = download_youtube_pro(url, cookies_file=cookies_path)
                        
                        if os.path.exists(result):
                            audio_ready = result
                            status.update(label="Extraction réussie !", state="complete")
                            progress_bar.empty()
                        else:
                            status.update(label="Échec de l'extraction", state="error")
                            st.error(f"Erreur YouTube : {result}")
                            st.info("Conseils : vérifiez le lien, ou téléchargez la vidéo manuellement et utilisez l'onglet FICHIER.")
                            st.stop()
                
                if audio_ready:
                    with st.status("Transcription par intelligence artificielle...", expanded=True) as status:
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
                    
                    # Compteur de mots et durée estimée
                    word_count = len(transcript.text.split())
                    if hasattr(transcript, 'segments') and transcript.segments:
                        duration = transcript.segments[-1].get('end', 0)
                        st.caption(f"📊 {word_count} mots · Durée estimée : {int(duration//60)}min {int(duration%60)}s")
                    else:
                        st.caption(f"📊 {word_count} mots")
                    
                    d1, d2, d3 = st.columns(3)
                    with d1:
                        st.download_button("📥 Texte brut", transcript.text, "vox_result.txt", use_container_width=True)
                    with d2:
                        srt_data = generate_srt(transcript.segments)
                        st.download_button("📥 Sous-titres SRT", srt_data, "vox_result.srt", use_container_width=True)
                    with d3:
                        # Aperçu des sous-titres dans un expander (optionnel)
                        with st.expander("👁️ Aperçu SRT"):
                            st.text(srt_data[:500] + ("..." if len(srt_data) > 500 else ""))
                    
                    # Nettoyage
                    if os.path.exists(audio_ready):
                        os.remove(audio_ready)
                    if up and os.path.exists(tmp_path):
                        os.remove(tmp_path)
            
            except Exception as e:
                st.error(f"Erreur système : {str(e)}")
                # Nettoyage de sécurité
                if 'audio_ready' in locals() and audio_ready and os.path.exists(audio_ready):
                    os.remove(audio_ready)
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
    <div style="text-align: center; margin-top: 4rem; color: #8E8E93; font-size: 0.8rem; padding-bottom: 4rem;">
        ALLAYEVOX V3 • WHISPER LARGE ENGINE • PROPRIÉTÉ DE BAMAKO TECH 🇲🇱
    </div>
""", unsafe_allow_html=True)
