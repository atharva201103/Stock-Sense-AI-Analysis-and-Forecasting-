import pickle
import numpy as np
import re
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

def analyze_sentiment(text):
    """
    Analyze sentiment of given text using trained neural network model.
    Returns: (sentiment_score, sentiment_label, confidence)
    """
    # Load the trained model and tokenizer
    try:
        model = load_model('models/sentiment_model.h5')
        with open('models/sentiment_tokenizer.pkl', 'rb') as f:
            tokenizer = pickle.load(f)
        with open('models/sentiment_label_encoder.pkl', 'rb') as f:
            label_encoder = pickle.load(f)
    except FileNotFoundError:
        raise Exception('Model files not found. Please run train_sentiment_model command first.')

    # Preprocess text
    processed_text = preprocess_text(text)

    # Tokenize and pad
    sequence = tokenizer.texts_to_sequences([processed_text])
    padded_sequence = pad_sequences(sequence, maxlen=100)

    # Predict sentiment
    prediction = model.predict(padded_sequence, verbose=0)
    predicted_class = np.argmax(prediction, axis=1)[0]
    confidence = np.max(prediction, axis=1)[0]

    # Convert to sentiment label
    sentiment_label = label_encoder.inverse_transform([predicted_class])[0]

    # Convert to numerical score (-1 to 1 scale)
    if sentiment_label == 'positive':
        sentiment_score = confidence * 1.0  # 0.0 to 1.0
    elif sentiment_label == 'negative':
        sentiment_score = -confidence * 1.0  # -1.0 to 0.0
    else:  # neutral
        sentiment_score = 0.0  # exactly 0

    return float(sentiment_score), sentiment_label, float(confidence)

def preprocess_text(text):
    """Preprocess text same as training data"""
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words('english'))

    # Convert to lowercase
    text = text.lower()
    # Remove special characters and numbers
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    # Tokenize
    tokens = word_tokenize(text)
    # Remove stopwords and lemmatize
    tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
    return ' '.join(tokens)
