"""Memoria de largo plazo: experiencias de auditoria en Chroma.

Cada auditoria completada se guarda como "experiencia" (publicacion,
categoria y veredicto). En ejecuciones futuras el agente recupera por
similitud vectorial las experiencias mas parecidas y las usa como
contexto, logrando continuidad entre sesiones (flujos prolongados).
"""

from __future__ import annotations

import os
import uuid
from functools import lru_cache
from pathlib import Path

import chromadb

from src.indexer.embed import embed_textos

COLECCION_DEFAULT = "experiencias_auditoria"


@lru_cache(maxsize=1)
def _coleccion():
    ruta = Path(os.getenv("CHROMA_PATH", "data/chroma"))
    ruta.mkdir(parents=True, exist_ok=True)
    cliente = chromadb.PersistentClient(path=str(ruta))
    return cliente.get_or_create_collection(
        name=os.getenv("MEMORIA_COLECCION", COLECCION_DEFAULT),
        metadata={"hnsw:space": "cosine"},
    )


def guardar_experiencia(texto: str, categoria: str, estado: str, resumen: str = "") -> str:
    """Guarda una auditoria como experiencia. Devuelve el id asignado."""
    if estado not in ("cumple", "alerta", "no_cumple"):
        raise ValueError(f"Estado invalido para memoria: {estado}")
    doc = f"({categoria}) {texto} -> {estado}. {resumen}".strip()
    exp_id = str(uuid.uuid4())
    _coleccion().add(
        ids=[exp_id],
        embeddings=embed_textos([doc]),
        documents=[doc],
        metadatas=[{"categoria": categoria, "estado": estado, "texto": texto}],
    )
    return exp_id


def buscar_experiencias(texto: str, top_k: int = 3) -> list[dict]:
    """Recupera las experiencias previas mas similares a la publicacion."""
    coleccion = _coleccion()
    if coleccion.count() == 0:
        return []
    embedding = embed_textos([texto])[0]
    res = coleccion.query(query_embeddings=[embedding], n_results=top_k)
    experiencias: list[dict] = []
    if not res.get("documents") or not res["documents"][0]:
        return experiencias
    for i, doc in enumerate(res["documents"][0]):
        meta = res["metadatas"][0][i]
        distancia = res["distances"][0][i] if res.get("distances") else None
        experiencias.append(
            {
                "texto": meta.get("texto", doc),
                "categoria": meta.get("categoria", ""),
                "estado": meta.get("estado", ""),
                "score": 1 - distancia if distancia is not None else None,
            }
        )
    return experiencias
