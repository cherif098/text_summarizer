from flask import Blueprint, request, jsonify, send_file, current_app
from requests import Response
from .file_handler import read_word, read_pdf, save_as_word, save_as_pdf
import io
import os
import logging
from http import HTTPStatus
from pathlib import Path
from werkzeug.utils import secure_filename
from .summarizer import MultilingualSummarizer
import logging


# Define the custom exception class
class FileProcessingError(Exception):
    """Custom exception for file processing errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


api_bp = Blueprint('api', __name__)

# Constants
DEFAULT_NUM_SENTENCES = 3
MAX_NUM_SENTENCES = 10  # safety limit
MIN_TEXT_LENGTH = 10    # minimum text length requirement
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
UPLOAD_FOLDER = 'temp_uploads'
SUPPORTED_LANGUAGES = {'fr', 'en'}  # Add supported languages here
DEFAULT_LANGUAGE = 'fr'  # Default to French


@api_bp.route('/summarize', methods=['POST'])
def summarize():

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing JSON payload'}), HTTPStatus.BAD_REQUEST
        
        # Validate text
        text = data.get('text')
        if not text or not isinstance(text, str) or len(text.strip()) < MIN_TEXT_LENGTH:
            return jsonify({
                'error': f'Invalid text. Must be a non-empty string with at least {MIN_TEXT_LENGTH} characters'
            }), HTTPStatus.BAD_REQUEST
        
        # Validate and process num_sentences
        num_sentences = data.get('num_sentences', DEFAULT_NUM_SENTENCES)
        if not isinstance(num_sentences, int) or not (0 < num_sentences <= MAX_NUM_SENTENCES):
            return jsonify({
                'error': f'num_sentences must be an integer between 1 and {MAX_NUM_SENTENCES}'
            }), HTTPStatus.BAD_REQUEST
        
        # Validate and process language
        language = data.get('language', DEFAULT_LANGUAGE).lower()
        if language not in SUPPORTED_LANGUAGES:
            return jsonify({
                'error': f'Unsupported language. Supported languages: {", ".join(SUPPORTED_LANGUAGES)}'
            }), HTTPStatus.BAD_REQUEST
        
        # Generate summary
        summarizer = MultilingualSummarizer()
        summary = summarizer.summarize_text(text.strip(), num_sentences, language)

        logging.info(f"Successfully generated {language} summary of {len(text)} chars into {num_sentences} sentences")
        return jsonify({
            'summary': summary,
            'language': language
        }), HTTPStatus.OK
        
    except ValueError as ve:
        logging.warning(f"Validation error: {str(ve)}")
        return jsonify({'error': str(ve)}), HTTPStatus.BAD_REQUEST
        
    except Exception as e:
        logging.error(f"Error generating summary: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error occurred'}), HTTPStatus.INTERNAL_SERVER_ERROR

@api_bp.route('/upload', methods=['POST'])
def upload_file():

    try:
        # Vérification de la présence du fichier
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), HTTPStatus.BAD_REQUEST
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), HTTPStatus.BAD_REQUEST
        
        # Vérification du type de fichier (si c'est bien un .docx)
        if not file.filename.endswith('.docx'):
            return jsonify({'error': 'Invalid file type. Only .docx files are supported.'}), HTTPStatus.BAD_REQUEST
        
        # Taille du fichier (max 10MB par exemple)
        if len(file.read()) > MAX_FILE_SIZE:
            return jsonify({'error': 'File size is too large.'}), HTTPStatus.BAD_REQUEST
        
        # Revenir au début du fichier après la lecture de sa taille
        file.seek(0)
        
        # Traitement du fichier (lecture du texte du fichier DOCX)
        text = read_word(file)
        
        # Retourner le texte extrait et la langue (facultatif)
        language = request.form.get('language', DEFAULT_LANGUAGE).lower()
        
        logging.info(f"Successfully processed file: {file.filename} in {language}")
        return jsonify({'text': text, 'language': language}), HTTPStatus.OK

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error occurred'}), HTTPStatus.INTERNAL_SERVER_ERROR
    


@api_bp.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        text = data.get('text', '')
        file_format = data.get('format', 'pdf').lower()
        language = data.get('language', DEFAULT_LANGUAGE).lower()

        if not text:
            return jsonify({'error': 'No text provided'}), HTTPStatus.BAD_REQUEST

        if language not in SUPPORTED_LANGUAGES:
            return jsonify({'error': f'Unsupported language. Supported languages: {", ".join(SUPPORTED_LANGUAGES)}'}), HTTPStatus.BAD_REQUEST

        if file_format == 'pdf':
            file_content = save_as_pdf(text)
            if file_content is None:
                raise FileProcessingError("Failed to generate PDF")
            mimetype = 'application/pdf'
            file_name = f'summary_{language}.pdf'
        elif file_format == 'word':
            file_content = save_as_word(text)
            if file_content is None:
                raise FileProcessingError("Failed to generate Word file")
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            file_name = f'summary_{language}.docx'
        else:
            return jsonify({'error': 'Invalid file format. Use "pdf" or "word"'}), HTTPStatus.BAD_REQUEST

        return send_file(
            file_content,
            mimetype=mimetype,
            as_attachment=True,
            download_name=file_name
        )
    except FileProcessingError as fe:
        logging.error(f"File processing error: {str(fe)}")
        return jsonify({'error': str(fe)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logging.error(f"Unexpected error during download: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error occurred'}), HTTPStatus.INTERNAL_SERVER_ERROR



def allowed_file(filename):
    """Check if the file has a valid extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_size(file):
    """Check if the file exceeds the maximum allowed size."""
    # Reset file pointer after checking the size
    file.seek(0, os.SEEK_END)
    return file.tell() <= MAX_FILE_SIZE

def save_file_safely(file):
    """Save file safely to a temporary location."""
    temp_filename = secure_filename(file.filename)
    temp_path = Path(UPLOAD_FOLDER) / temp_filename
    if not temp_path.parent.exists():
        os.makedirs(temp_path.parent)
    file.save(temp_path)
    return temp_path
