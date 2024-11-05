import docx2txt
import PyPDF2
import io
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

def read_word(file):
    return docx2txt.process(file)

def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def save_as_word(text, output):
    doc = Document()
    doc.add_paragraph(text)
    doc.save(output)

def save_as_pdf(text):
    output = BytesIO()  # Utilisation de BytesIO to hold the PDF dans la memoire
    c = canvas.Canvas(output, pagesize=letter)
    width, height = letter

    # Set the font et size
    c.setFont("Helvetica", 12)

    # Draw the text in the middle of the page 
    c.drawString(72, height / 2, text)  # Keep the left margin (72) 

    c.showPage()
    c.save()
    output.seek(0)  # Go to the beginning of the BytesIO object
    return output  # Return the BytesIO object instead of binary content