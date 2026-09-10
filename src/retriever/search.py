"""Busqueda vectorial en Chroma con filtro opcional por categoria."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import chromadb

from src.indexer.embed import embed_textos


@lru_cache(maxsize=1)
def _cliente() -> chromadb.PersistentClient:
    ruta = Path(os.getenv("CHROMA_PATH", "data/chroma"))
    return chromadb.PersistentClient(path=str(ruta))


@lru_cache(maxsize=1)
def _coleccion():
    nombre = os.getenv("CHROMA_COLLECTION", "normativa_comunidades")
    return _cliente().get_or_create_collection(name=nombre, metadata={"hnsw:space": "cosine"})


def buscar(query: str, categoria: str | None = None, top_k: int = 5) -> list[dict]:
    """Busca los chunks mas relevantes para una query.

    Si se pasa `categoria`, intenta filtrar por esa categoria en metadata.
    Si el filtro devuelve 0 resultados (problema conocido de Chroma con $contains
    sobre metadata strings), hace fallback a busqueda sin filtro.
    """
    coleccion = _coleccion()
    if coleccion.count() == 0:
        return []

    embedding = embed_textos([query])[0]

    fragmentos = _query_con_filtro(coleccion, embedding, categoria, top_k) if categoria else None
    if not fragmentos:
        fragmentos = _query_sin_filtro(coleccion, embedding, top_k)
    return fragmentos


def _query_con_filtro(coleccion, embedding: list[float], categoria: str, top_k: int) -> list[dict]:
    where = {"categoria_publicacion": {"$contains": categoria}}
    resultados = coleccion.query(query_embeddings=[embedding], n_results=top_k, where=where)
    return _a_fragments(resultados)


def _query_sin_filtro(coleccion, embedding: list[float], top_k: int) -> list[dict]:
    resultados = coleccion.query(query_embeddings=[embedding], n_results=top_k)
    return _a_fragments(resultados)


def _a_fragments(resultados: dict) -> list[dict]:
    fragments: list[dict] = []
    if not resultados.get("documents") or not resultados["documents"][0]:
        return fragments
    for i, texto in enumerate(resultados["documents"][0]):
        meta = resultados["metadatas"][0][i]
        distancia = resultados["distances"][0][i] if resultados.get("distances") else None
        fragments.append(
            {
                "texto": texto,
                "fuente": meta.get("fuente", ""),
                "articulo": meta.get("articulo", ""),
                "tipo_norma": meta.get("tipo_norma", ""),
                "numero_norma": meta.get("numero_norma", ""),
                "score": 1 - distancia if distancia is not None else None,
            }
        )
    return fragments
