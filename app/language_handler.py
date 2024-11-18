from typing import Dict, Optional
import spacy

class LanguageHandler:
    def __init__(self):
        self.models: Dict[str, Optional[spacy.language.Language]] = {
            'en': None,  # English model
            'es': None,  # Spanish model (if needed in future)
        }
        self.supported_languages = ['en', 'es']  # Updated to support Spanish as a future option
    
    def load_model(self, language: str) -> None:
        """Load the specified language model if not already loaded."""
        if language not in self.supported_languages:
            raise ValueError(f"Language {language} is not supported.")
            
        if self.models[language] is None:
            if language == 'en':
                try:
                    self.models[language] = spacy.load('en_core_web_sm')
                except OSError:
                    raise OSError("English model not found. Install it using: python -m spacy download en_core_web_sm")
            elif language == 'es':
                try:
                    self.models[language] = spacy.load('es_core_news_sm')  # Spanish model (when implemented)
                except OSError:
                    raise OSError("Spanish model not found. Install it using: python -m spacy download es_core_news_sm")
    
    def get_model(self, language: str) -> spacy.language.Language:
        """Get the specified language model, loading it if necessary."""
        self.load_model(language)
        return self.models[language]
    
    def process_text(self, text: str, language: str) -> spacy.tokens.Doc:
        """Process text using the specified language model."""
        model = self.get_model(language)
        return model(text)
    
    def get_sentences(self, doc: spacy.tokens.Doc) -> list:
        """Extract sentences from processed document."""
        return [sent.text.strip() for sent in doc.sents]
    
    def clean_text(self, text: str, language: str) -> str:
        """Clean and preprocess text based on language-specific rules."""
        # Example: Implement specific cleaning rules for different languages
        if language == 'en':
            text = text.replace("\n", " ").strip()  # Example English-specific cleanup
        elif language == 'es':
            text = text.replace("\n", " ").strip()  # Example Spanish-specific cleanup
        return text
