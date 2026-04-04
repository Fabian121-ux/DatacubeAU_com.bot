import hashlib

from app.utils.text import normalize_text


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_question_key(question: str) -> str:
    return normalize_text(question)

