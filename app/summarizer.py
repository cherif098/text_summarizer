# app/summarizer.py
import spacy
from spacy.lang.fr.stop_words import STOP_WORDS
from string import punctuation
from collections import Counter
from heapq import nlargest

def summarize_text(text, num_sentences):
    nlp = spacy.load('fr_core_news_sm')
    doc = nlp(text)
    tokens = [token.text.lower() for token in doc 
              if not token.is_stop and not token.is_punct and token.text != '\n']
    
    word_freq = Counter(tokens)
    if not word_freq:
        return "Aucun mot trouvé dans le texte."
    
    max_freq = max(word_freq.values())
    for word in word_freq.keys():
        word_freq[word] = word_freq[word]/max_freq
    
    sent_token = [sent.text for sent in doc.sents]
    sent_score = {}
    for sent in sent_token:
        for word in sent.split():
            if word.lower() in word_freq.keys():
                if sent not in sent_score.keys():
                    sent_score[sent] = word_freq[word]
                else:
                    sent_score[sent] += word_freq[word]
    
    summarized_sentences = nlargest(num_sentences, sent_score, key=sent_score.get)
    return " ".join(summarized_sentences)