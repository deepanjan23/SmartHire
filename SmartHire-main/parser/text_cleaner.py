
import re
import logging
from typing import Dict, List, Tuple

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import wordpunct_tokenize


# Configure logging
logger = logging.getLogger(__name__)

# Regular expressions
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+\b"
)

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
    re.IGNORECASE
)

# Remove punctuation but retain letters, numbers and whitespace
PUNCTUATION_PATTERN = re.compile(r"[^\w\s]", re.UNICODE)
WHITESPACE_PATTERN = re.compile(r"\s+")


class TextCleaner:
    """Clean resume text while preserving email addresses and URLs."""

    def __init__(self) -> None:
        try:
            self.stop_words = set(stopwords.words("english"))
            self.lemmatizer = WordNetLemmatizer()

            # Check that the required WordNet resource is available
            self.lemmatizer.lemmatize("test")

        except LookupError as exc:
            raise RuntimeError(
                "Required NLTK data is missing. Run these commands "
                "in your terminal:\n"
                "python -m nltk.downloader stopwords wordnet"
            ) from exc

    @staticmethod
    def _protect_links(text: str) -> Tuple[str, Dict[str, str]]:
        """Protect email addresses and URLs from text modifications."""

        protected: Dict[str, str] = {}

        def replace_match(match: re.Match, kind: str) -> str:
            original = match.group(0)

            # Avoid treating trailing sentence punctuation as part of a URL
            if kind == "URL":
                trailing = ""
                while original and original[-1] in ".,!?;:":
                    trailing = original[-1] + trailing
                    original = original[:-1]

                if not original:
                    return match.group(0)

            else:
                trailing = ""

            token = f"zzprotected{len(protected)}zz"
            protected[token] = original

            return token + trailing

        # Protect emails first so their domains are not treated as URLs
        text = EMAIL_PATTERN.sub(
            lambda match: replace_match(match, "EMAIL"), text
        )

        text = URL_PATTERN.sub(
            lambda match: replace_match(match, "URL"), text
        )

        return text, protected

    def clean_text(self, text: str) -> str:
        """
        Normalize resume text while preserving email addresses and URLs.

        Args:
            text: Raw resume text.

        Returns:
            Cleaned text as a string.
        """
        if not isinstance(text, str):
            raise TypeError("Input text must be a string.")

        if not text.strip():
            return ""

        # 1. Protect emails and URLs
        text, protected = self._protect_links(text)

        # 2. Normalize the remaining text
        text = text.lower()

        # 3. Remove punctuation
        text = PUNCTUATION_PATTERN.sub(" ", text)

        # 4. Normalize whitespace
        text = WHITESPACE_PATTERN.sub(" ", text).strip()

        # 5. Tokenize
        tokens: List[str] = wordpunct_tokenize(text)

        # 6. Remove stopwords, preserving protected tokens
        tokens = [
            token for token in tokens
            if token not in self.stop_words
            or token in protected
        ]

        # 7. Lemmatize normal words only
        tokens = [
            token if token in protected
            else self.lemmatizer.lemmatize(token)
            for token in tokens
        ]

        # 8. Rebuild the cleaned text
        cleaned_text = " ".join(tokens)

        # 9. Restore original emails and URLs
        for token, original in protected.items():
            cleaned_text = cleaned_text.replace(token, original)

        return cleaned_text


# Create a reusable cleaner
_cleaner = None


def clean_text(text: str) -> str:
    """Convenience function for use throughout SmartHire."""
    global _cleaner

    if _cleaner is None:
        _cleaner = TextCleaner()

    return _cleaner.clean_text(text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    sample_text = """
    HELLO! I am a Software Developer with experience in Python,
    Java, and SQL. Contact me at Dev.Example@gmail.com.
    Portfolio: https://Example.com/MyPortfolio
    """

    print("Original Text:")
    print(sample_text)

    print("\nCleaned Text:")
    print(clean_text(sample_text))
