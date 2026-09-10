"""Generacion de embeddings con sentence-transformers."""

from __future__ import annotations

import os
from functools import lru_cache

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def cargar_modelo() -> SentenceTransformer:
    """Carga el modelo de embeddings (se cachea para no recargarlo)."""
    nombre = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    return SentenceTransformer(nombre)


def embed_textos(textos: list[str]) -> list[list[float]]:
    """Genera embeddings para una lista de textos."""
    modelo = cargar_modelo()
    vectores = modelo.encode(textos, convert_to_numpy=True, show_progress_bar=False)
    return vectores.tolist()
