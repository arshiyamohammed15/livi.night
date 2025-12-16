#calucator
from __future__ import annotations


def add(a: float, b: float) -> float:
    return a + b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def is_palindrome(text: str) -> bool:
    # ignore spaces + case
    cleaned = "".join(ch.lower() for ch in text if not ch.isspace())
    return cleaned == cleaned[::-1]


def word_count(sentence: str) -> int:
    # count words (handles extra spaces)
    words = [w for w in sentence.strip().split() if w]
    return len(words)

if __name__ == "__main__":
    print("2 + 3 =", add(2, 3))
    print("8 / 2 =", divide(8, 2))
    print("'Race car' palindrome?", is_palindrome("Race car"))
    print("Word count:", word_count("hello   world"))

    
