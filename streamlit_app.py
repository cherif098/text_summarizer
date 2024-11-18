import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Constants
MAX_FILE_SIZE = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "docx"}
API_BASE_URL = "http://localhost:5000"

# Language configurations
LANG_CONFIG = {
    'fr': {
        'title': "Résumé de Texte",
        'text_input': "Entrez votre texte ici",
        'file_upload': "Ou téléchargez un fichier Word ou PDF",
        'num_sentences': "Nombre de phrases dans le résumé",
        'summarize': "Résumer",
        'summary': "Résumé",
        'download_format': "Format de téléchargement",
        'download': "Télécharger en {}",
        'error': "Erreur: {}",
        'processing': "Traitement en cours...",
        'grammar_analysis': "Analyse grammaticale",
        'verb': "Verbe",
        'subject': "Sujet",
        'complement': "Complément"
    },
    'en': {
        'title': "Text Summarizer",
        'text_input': "Enter your text here",
        'file_upload': "Or upload a Word or PDF file",
        'num_sentences': "Number of sentences in summary",
        'summarize': "Summarize",
        'summary': "Summary",
        'download_format': "Download format",
        'download': "Download as {}",
        'error': "Error: {}",
        'processing': "Processing...",
        'grammar_analysis': "Grammatical Analysis",
        'verb': "Verb",
        'subject': "Subject",
        'complement': "Complement"
    }
}

def setup_requests_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session

def process_file_upload(file, language, session):
    try:
        response = session.post(
            f"{API_BASE_URL}/upload",
            files={"file": file},
            data={"language": language},
            timeout=300
        )
        response.raise_for_status()
        return response.json().get('text')
    except requests.RequestException as e:
        st.error(f"Erreur lors du téléchargement: {str(e)}")
        return None

def get_summary(text, num_sentences, language, session):
    try:
        response = session.post(
            f"{API_BASE_URL}/summarize",
            json={"text": text, "num_sentences": num_sentences, "language": language},
            timeout=60
        )
        response.raise_for_status()
        return response.json().get('summary'), response.json().get('grammatical_elements', [])
    except requests.RequestException as e:
        st.error(f"Erreur lors de la génération du résumé: {str(e)}")
        return None, None

def download_file(summary, format_type, language, session):
    try:
        response = session.post(
            f"{API_BASE_URL}/download",
            json={"text": summary, "format": format_type.lower(), "language": language},
            timeout=60,
            stream=True
        )
        response.raise_for_status()
        
        extension = 'pdf' if format_type.lower() == 'pdf' else 'docx'
        mime_type = 'application/pdf' if extension == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        return response.content, f"resume_{language}.{extension}", mime_type
    except Exception as e:
        st.error(f"Erreur lors du téléchargement: {str(e)}")
        return None, None, None

def display_summary(summary, lang):
    st.markdown(f"""
        <div style='background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 5px solid #1e88e5;'>
            <h3 style='color: #1e88e5; margin-bottom: 15px;'>{LANG_CONFIG[lang]['summary']}</h3>
            <p style='font-size: 16px; line-height: 1.6; color: #333;'>{summary}</p>
        </div>
    """, unsafe_allow_html=True)

def display_grammatical_elements(elements, lang):
    if not elements:
        return

    st.markdown(f"""
        <div style='margin-top: 30px;'>
            <h3 style='color: #1e88e5;'>{LANG_CONFIG[lang]['grammar_analysis']}</h3>
        </div>
    """, unsafe_allow_html=True)

    for idx, sentence_elements in enumerate(elements, 1):
        with st.expander(f"🔍 Analyse de la phrase {idx}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("""
                    <div style='background-color: #e3f2fd; padding: 10px; border-radius: 5px;'>
                        <h4 style='color: #1976d2; margin: 0;'>🎯 Verbe</h4>
                    </div>
                """, unsafe_allow_html=True)
                for verb in sentence_elements['verbe']:
                    st.markdown(f"""
                        <div style='background-color: #fff; padding: 8px; border-radius: 4px; margin: 5px 0; 
                        border-left: 3px solid #1976d2;'>{verb}</div>
                    """, unsafe_allow_html=True)

            with col2:
                st.markdown("""
                    <div style='background-color: #e8f5e9; padding: 10px; border-radius: 5px;'>
                        <h4 style='color: #388e3c; margin: 0;'>👤 Sujet</h4>
                    </div>
                """, unsafe_allow_html=True)
                for subj in sentence_elements['sujet']:
                    st.markdown(f"""
                        <div style='background-color: #fff; padding: 8px; border-radius: 4px; margin: 5px 0; 
                        border-left: 3px solid #388e3c;'>{subj}</div>
                    """, unsafe_allow_html=True)

            with col3:
                st.markdown("""
                    <div style='background-color: #fff3e0; padding: 10px; border-radius: 5px;'>
                        <h4 style='color: #e64a19; margin: 0;'>📝 Complément</h4>
                    </div>
                """, unsafe_allow_html=True)
                for comp in sentence_elements['complement']:
                    st.markdown(f"""
                        <div style='background-color: #fff; padding: 8px; border-radius: 4px; margin: 5px 0; 
                        border-left: 3px solid #e64a19;'>{comp}</div>
                    """, unsafe_allow_html=True)

def main():
    if 'language' not in st.session_state:
        st.session_state.language = 'fr'
    
    with st.sidebar:
        lang = st.selectbox(
            "Language / Langue",
            options=['fr', 'en'],
            format_func=lambda x: "Français" if x == 'fr' else "English",
            key='language'
        )
    
    txt = LANG_CONFIG[lang]
    session = setup_requests_session()
    
    # Page title avec style
    st.markdown(f"""
        <h1 style='color: #1e88e5; text-align: center; margin-bottom: 30px;'>
            {txt['title']}
        </h1>
    """, unsafe_allow_html=True)
    
    # Input section avec style
    st.markdown("""
        <div style='background-color: #f5f5f5; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
    """, unsafe_allow_html=True)
    
    text_input = st.text_area(txt['text_input'], height=200)
    uploaded_file = st.file_uploader(txt['file_upload'], type=list(ALLOWED_EXTENSIONS))
    num_sentences = st.slider(txt['num_sentences'], 1, 10, 3)
    
    if st.button(txt['summarize'], key='summarize_button'):
        if not text_input and not uploaded_file:
            st.error(txt['error'].format("Aucun texte fourni"))
            return
            
        with st.spinner(txt['processing']):
            if uploaded_file:
                if uploaded_file.size <= MAX_FILE_SIZE:
                    text_input = process_file_upload(uploaded_file, lang, session)
                else:
                    st.error(txt['error'].format("Fichier trop volumineux"))
                    return

            if text_input:
                summary, grammatical_elements = get_summary(text_input, num_sentences, lang, session)
                if summary:
                    st.session_state.update({
                        'summary': summary,
                        'grammatical_elements': grammatical_elements
                    })
    
    # Display results
    if 'summary' in st.session_state:
        display_summary(st.session_state.summary, lang)
        
        if 'grammatical_elements' in st.session_state:
            display_grammatical_elements(st.session_state.grammatical_elements, lang)
        
        # Download section
        st.markdown("""
            <div style='background-color: #e3f2fd; padding: 20px; border-radius: 10px; margin-top: 30px;'>
                <h4 style='color: #1976d2; margin: 0;'>📥 Téléchargement</h4>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            format_type = st.selectbox(txt['download_format'], ["PDF", "Word"])
        
        if st.button(txt['download'].format(format_type)):
            content, filename, mime_type = download_file(
                st.session_state.summary, format_type, lang, session
            )
            if content:
                st.download_button(
                    label=txt['download'].format(format_type),
                    data=content,
                    file_name=filename,
                    mime=mime_type
                )

if __name__ == "__main__":
    main()