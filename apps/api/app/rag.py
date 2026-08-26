"""TF-IDF retrieval over the IRIS knowledge base.

Ported from inovatalk backend/app/rag/kb.py. The sklearn vectorizer is
replaced by a small numpy TF-IDF with identical scoring semantics
(smooth IDF, l2-normalized document vectors, cosine similarity) so the API
stack stays dependency-light. Citation list is stored on Answer.citations; the farmer-facing
text does not append "[Source: file.md]" because that tag is not a link.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

CONFIDENT_MIN = 0.25

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
KB_DIR = Path(__file__).resolve().parent / "kb"


@dataclass
class Chunk:
    source: str
    title: str
    text: str


@dataclass
class Answer:
    text: str
    citations: list[str]
    confident: bool


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def load_chunks(kb_dir: str | Path = KB_DIR) -> list[Chunk]:
    out: list[Chunk] = []
    for p in sorted(Path(kb_dir).glob("*.md")):
        lines = p.read_text(encoding="utf-8").splitlines()
        title = ""
        body_start = 0
        for i, ln in enumerate(lines):
            if ln.startswith("# "):
                title = ln[2:].strip()
                body_start = i + 1
                break
        text = "\n".join(lines[body_start:]).strip()
        out.append(Chunk(source=p.name, title=title or p.stem, text=text))
    return out


class KBSearch:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self._vocab: dict[str, int] = {}
        self._idf = np.zeros(0)
        self._mat = None
        if not chunks:
            return
        docs = [_tokens(c.title + "\n" + c.text) for c in chunks]
        vocab = sorted({t for d in docs for t in d})
        self._vocab = {t: i for i, t in enumerate(vocab)}
        n_docs = len(docs)
        tf = np.zeros((n_docs, len(vocab)))
        for i, d in enumerate(docs):
            for t in d:
                tf[i, self._vocab[t]] += 1.0
        df = np.count_nonzero(tf > 0.0, axis=0).astype(float)
        self._idf = np.log((1.0 + n_docs) / (1.0 + df)) + 1.0
        tf = tf / np.maximum(tf.sum(axis=1, keepdims=True), 1e-12)
        mat = tf * self._idf
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        self._mat = mat / np.maximum(norms, 1e-12)

    def answer(self, query: str, max_chars: int = 900) -> Answer:
        if self._mat is None or not self._vocab:
            return Answer(
                "The IRIS knowledge base is empty.", [], False)
        q_tokens = _tokens(query)
        vec = np.zeros(len(self._vocab))
        if q_tokens:
            counts: dict[str, int] = {}
            for t in q_tokens:
                counts[t] = counts.get(t, 0) + 1
            for t, c in counts.items():
                idx = self._vocab.get(t)
                if idx is not None:
                    vec[idx] = (c / len(q_tokens)) * self._idf[idx]
        norm = float(np.linalg.norm(vec))
        sims = (self._mat @ (vec / norm)) if norm > 0.0 \
            else np.zeros(self._mat.shape[0])
        best_i = int(sims.argmax())
        if float(sims[best_i]) < CONFIDENT_MIN:
            return Answer(
                "This question is outside the IRIS knowledge base. "
                "Ask an extension officer, or try other keywords.",
                [], False)
        c = self.chunks[best_i]
        body = re.sub(r"\n{3,}", "\n\n", c.text.strip())[:max_chars]
        return Answer(body, [c.source], True)


_default: KBSearch | None = None


def get_kb_search() -> KBSearch:
    global _default
    if _default is None:
        _default = KBSearch(load_chunks())
    return _default


def reset_kb_cache() -> None:
    global _default
    _default = None
