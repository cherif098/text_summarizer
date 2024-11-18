import spacy
from spacy.lang.fr.stop_words import STOP_WORDS as FR_STOP_WORDS
from spacy.lang.en.stop_words import STOP_WORDS as EN_STOP_WORDS
from string import punctuation
from collections import Counter
from heapq import nlargest
from typing import Dict, Set, List, Tuple

class MultilingualSummarizer:
    SUPPORTED_LANGUAGES = {
        'fr': 'fr_core_news_sm',
        'en': 'en_core_web_sm'
    }

    def __init__(self):
        self.nlp_models = {}
        self.stop_words = {
            'fr': FR_STOP_WORDS,
            'en': EN_STOP_WORDS
        }

    def _load_model(self, language: str) -> None:
        """Load the specified language model if not already loaded."""
        if language not in self.nlp_models:
            try:
                self.nlp_models[language] = spacy.load(self.SUPPORTED_LANGUAGES[language])
            except OSError:
                raise OSError(
                    f"Model for language '{language}' not found. Install it with: "
                    f"python -m spacy download {self.SUPPORTED_LANGUAGES[language]}"
                )

    def extract_grammatical_elements(self, sentence: spacy.tokens.Span, language: str) -> Dict:
        """
        Extraire les éléments grammaticaux (verbe, sujet, complément) d'une phrase.
        """
        elements = {
            "verbe": [],
            "sujet": [],
            "complement": []
        }
        
        for token in sentence:
            # Extraction du verbe principal
            if token.pos_ == "VERB":
                elements["verbe"].append(token.text)
            
            # Extraction du sujet
            if token.dep_ == "nsubj":
                # Inclure les modificateurs du sujet
                subtree = list(token.subtree)
                sujet = " ".join([t.text for t in subtree if t.dep_ in ["nsubj", "compound", "amod"]])
                elements["sujet"].append(sujet)
            
            # Extraction des compléments
            if token.dep_ in ["dobj", "pobj", "iobj"]:
                # Inclure les modificateurs du complément
                subtree = list(token.subtree)
                complement = " ".join([t.text for t in subtree if not any(p.dep_ == "nsubj" for p in t.ancestors)])
                if complement.strip():
                    elements["complement"].append(complement)
        
        return elements

    def summarize_text(self, text: str, num_sentences: int, language: str = 'fr') -> Tuple[str, List[Dict]]:
        if not text.strip():
            return ("Le texte est vide." if language == 'fr' else "Text is empty.", [])

        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Language '{language}' is not supported. Supported languages: "
                f"{list(self.SUPPORTED_LANGUAGES.keys())}"
            )

        self._load_model(language)
        nlp = self.nlp_models[language]
        doc = nlp(text)

        # Filter tokens to remove stop words and punctuation
        tokens = [
            token.text.lower() for token in doc
            if not token.is_stop and not token.is_punct and token.text.strip()
        ]

        if not tokens:
            return ("Aucun mot significatif trouvé." if language == 'fr' else "No meaningful words found in the text.", [])

        # Calculate word frequencies
        word_freq = Counter(tokens)
        max_freq = max(word_freq.values())
        word_freq = {word: freq / max_freq for word, freq in word_freq.items()}

        # Score sentences based on word frequencies
        sent_scores = {}
        for sent in doc.sents:
            for word in sent:
                word_lower = word.text.lower()
                if word_lower in word_freq:
                    sent_scores[sent.text] = sent_scores.get(sent.text, 0) + word_freq[word_lower]

        if not sent_scores:
            return ("Aucune phrase valide trouvée." if language == 'fr' else "No valid sentences found.", [])

        # Select the top sentences
        summarized_sentences = nlargest(
            min(num_sentences, len(sent_scores)), sent_scores, key=sent_scores.get
        )

        # Sort sentences by their order in the original text and extract grammatical elements
        ordered_sentences = []
        grammatical_elements = []
        
        for sent in doc.sents:
            if sent.text in summarized_sentences:
                ordered_sentences.append(sent.text)
                elements = self.extract_grammatical_elements(sent, language)
                grammatical_elements.append(elements)

        summary = " ".join(ordered_sentences)
        return summary, grammatical_elements