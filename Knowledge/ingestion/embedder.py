"""
Lightweight, dependency-free embedder.

In production this would call a real embedding model (Voyage, OpenAI,
or a local sentence-transformer). To keep this codebase runnable with
zero external services, this uses a hashed bag-of-words vector, which
is enough to demonstrate retrieval behavior end to end. Swap
`embed_text` out for a real embedding API call when wiring this up
to production infrastructure.
"""

import hashlib
import math
import re
from collections import Counter

VECTOR_DIM = 512


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _hash_token(token: str) -> int:
    return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % VECTOR_DIM


def embed_text(text: str) -> list[float]:
    tokens = _tokenize(text)
    vec = [0.0] * VECTOR_DIM
    counts = Counter(tokens)
    for token, count in counts.items():
        vec[_hash_token(token)] += count

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
