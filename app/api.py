from flask import Blueprint, request, jsonify, send_file, current_app
from requests import Response
from .summarizer import summarize_text
from .file_handler import read_word, read_pdf, save_as_word, save_as_pdf
import io
import os
import logging
from http import HTTPStatus
from pathlib import Path
from werkzeug.utils import secure_filename

api_bp = Blueprint('api', __name__)

# Constants
DEFAULT_NUM_SENTENCES = 3
MAX_NUM_SENTENCES = 10  #  safety limit
MIN_TEXT_LENGTH = 10    #  minimum text length requirement
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
UPLOAD_FOLDER = 'temp_uploads'

@api_bp.route('/summarize', methods=['POST'])
def summarize():
    """
    Summarizes the provided text into a specified number of sentences.
    
    Expected JSON payload:
    {
        "text": "Text to summarize...",
        "num_sentences": 3  # Optional, defaults to DEFAULT_NUM_SENTENCES
    }
    
    Returns:
    {
        "summary": "Summarized text..."
    }
    
    or in case of error:
    {
        "error": "Error message..."
    }
    """
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
        
        # Generate summary
        summary = summarize_text(text.strip(), num_sentences)
        
        logging.info(f"Successfully generated summary of {len(text)} chars into {num_sentences} sentences")
        return jsonify({'summary': summary}), HTTPStatus.OK
        
    except ValueError as ve:
        logging.warning(f"Validation error: {str(ve)}")
        return jsonify({'error': str(ve)}), HTTPStatus.BAD_REQUEST
        
    except Exception as e:
        logging.error(f"Error generating summary: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error occurred'}), HTTPStatus.INTERNAL_SERVER_ERROR


class FileProcessingError(Exception):
    """Custom exception for file processing errors"""
    pass

def allowed_file(filename):
    """
    Validate file extension and security
    Returns: bool
    """
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def validate_file_size(file):
    """
    Validate file size
    Returns: bool
    """
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)  # Reset file pointer
    return size <= MAX_FILE_SIZE

def save_file_safely(file):
    """
    Safely save file to temporary location
    Returns: Path to saved file
    """
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        
    filename = secure_filename(file.filename)
    temp_path = Path(UPLOAD_FOLDER) / filename
    file.save(temp_path)
    return temp_path

@api_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Uploads a file and extracts text from it.
    
    Accepts:
    - Multipart form data with 'file' field
    - Supported formats: PDF, DOCX
    - Maximum file size: 10MB
    
    Returns:
    {
        "text": "Extracted text..."
    }
    
    or in case of error:
    {
        "error": "Error message..."
    }
    """
    try:
        # Validate file presence
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), HTTPStatus.BAD_REQUEST
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected'}), HTTPStatus.BAD_REQUEST
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'Unsupported file format. Allowed formats: {", ".join(ALLOWED_EXTENSIONS)}'
            }), HTTPStatus.BAD_REQUEST
        
        # Validate file size
        if not validate_file_size(file):
            return jsonify({
                'error': f'File too large. Maximum size: {MAX_FILE_SIZE/1024/1024}MB'
            }), HTTPStatus.BAD_REQUEST
        
        # Save file safely
        temp_path = save_file_safely(file)
        
        try:
            # Process file based on extension
            if file.filename.endswith('.docx'):
                text = read_word(temp_path)
            elif file.filename.endswith('.pdf'):
                text = read_pdf(temp_path)
            else:
                raise FileProcessingError("Unsupported file format")
                
            logging.info(f"Successfully processed file: {file.filename}")
            return jsonify({'text': text}), HTTPStatus.OK
            
        finally:
            # Clean temporary file
            if temp_path.exists():
                temp_path.unlink()
                
    except FileProcessingError as fe:
        logging.error(f"File processing error: {str(fe)}")
        return jsonify({'error': str(fe)}), HTTPStatus.BAD_REQUEST
        
    except Exception as e:
        logging.error(f"Unexpected error processing file: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error occurred'}), HTTPStatus.INTERNAL_SERVER_ERROR

@api_bp.route('/download', methods=['POST'])
def download():
    """Generates a summary and allows the user to download it in the specified format."""
    data = request.get_json()
    text = data.get('text', '')
    file_format = data.get('format', 'pdf').lower()

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        if file_format == 'pdf':
            file_content = save_as_pdf(text)  # Get the BytesIO object
            mimetype = 'application/pdf'
            file_name = 'resume.pdf'
        elif file_format == 'word':
            file_content = save_as_word(text)  # Get the BytesIO object
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            file_name = 'resume.docx'
        else:
            return jsonify({'error': 'Unsupported file format'}), 400

        # Use send_file to send the file content
        return send_file(
            file_content,  # Pass the BytesIO object 
            as_attachment=True,  # Force download
            download_name=file_name,  # Specify the filename
            mimetype=mimetype  # Set the mime type
        )

    except Exception as e:
        logging.error(f"Error generating file: {str(e)}")
        return jsonify({'error': str(e)}), 500