import logging
import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Constants
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {"pdf", "docx"}
API_BASE_URL = "http://localhost:5000"

def setup_requests_session():
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def is_valid_file(uploaded_file):
    """Validate file size and extension."""
    return (
        uploaded_file 
        and uploaded_file.size <= MAX_FILE_SIZE 
        and uploaded_file.name.split('.')[-1].lower() in ALLOWED_EXTENSIONS
    )

def upload_file(session, file):
    """Upload file and return text or None on failure."""
    try:
        response = session.post(f"{API_BASE_URL}/upload", files={"file": file}, timeout=300)
        response.raise_for_status()
        return response.json().get('text')
    except requests.RequestException:
        st.error("Erreur lors du téléchargement du fichier.")
        return None

def summarize_text(session, text, num_sentences):
    """Request summary from server."""
    try:
        response = session.post(
            f"{API_BASE_URL}/summarize", json={"text": text, "num_sentences": num_sentences}, timeout=60
        )
        response.raise_for_status()
        return response.json().get('summary')
    except requests.RequestException:
        st.error("Erreur lors de la génération du résumé.")
        return None

def download_summary(session, summary, format):
    try:
        # Log the format and the request payload for debugging
        logging.info(f"Requesting download in {format} format")
        
        response = session.post(
            f"{API_BASE_URL}/download",
            json={"text": summary, "format": format.lower()},
            timeout=60
        )
        response.raise_for_status()
        
        file_content = response.content
        file_name = f"resume.{format.lower()}"
        file_type = f"application/{'pdf' if format.lower() == 'pdf' else 'vnd.openxmlformats-officedocument.wordprocessingml.document'}"
        
        return file_content, file_name, file_type
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur lors de la génération du fichier: {e}")
        st.error(f"Erreur lors de la génération du fichier: {e}")
        return None, None, None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        st.error(f"Une erreur inattendue est survenue: {e}")
        return None, None, None


def main():
    st.title("Résumé de Texte")
    session = setup_requests_session()
    
    # Input options
    text_input = st.text_area("Entrez votre texte ici", height=200, key="text_input")
    uploaded_file = st.file_uploader("Ou téléchargez un fichier Word ou PDF", type=list(ALLOWED_EXTENSIONS))
    num_sentences = st.slider("Nombre de phrases dans le résumé", 1, 10, 3)

    # Summary action
    if st.button("Résumer"):
        if uploaded_file and is_valid_file(uploaded_file):
            text_input = upload_file(session, uploaded_file)
            if not text_input:
                return

        if text_input:
            summary = summarize_text(session, text_input, num_sentences)
            if summary:
                st.session_state.summary = summary  # Store summary in session state

    # Afficher le résumé seulement si le bouton a été cliqué
    if "summary" in st.session_state:
        st.subheader("Résumé:")
        st.write(st.session_state.summary)

        # Download action
        format = st.selectbox("Format de téléchargement", ["PDF", "Word"], key="download_format")
        if st.button("Télécharger le résumé"):
            file_content, file_name, file_type = download_summary(session, st.session_state.summary, format)
            if file_content:
                st.download_button(label=f"Télécharger le résumé en {format}", data=file_content, file_name=file_name, mime=file_type)

if __name__ == "__main__":
    main()
