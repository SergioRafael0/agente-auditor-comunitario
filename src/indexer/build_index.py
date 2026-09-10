"""Orquesta la indexacion: normativa -> chunks -> embeddings -> Chroma."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import chromadb

from src.indexer.chunk import adjuntar_metadata, dividir_en_chunks
from src.indexer.embed import embed_textos
from src.indexer.ingest import cargar_normativa

logger = logging.getLogger(__name__)

CARPETA_NORMATIVA = Path("data/normativa")


def construir_indice(sobreescribir: bool = False) -> int:
    """Carga la normativa, la divide en chunks, embebe y guarda en Chroma.

    Devuelve la cantidad de chunks indexados.
    """
    ruta_chroma = Path(os.getenv("CHROMA_PATH", "data/chroma"))
    coleccion_nombre = os.getenv("CHROMA_COLLECTION", "normativa_comunidades")

    ruta_chroma.mkdir(parents=True, exist_ok=True)
    cliente = chromadb.PersistentClient(path=str(ruta_chroma))

    if sobreescribir:
        try:
            cliente.delete_collection(coleccion_nombre)
        except Exception:
            pass

    coleccion = cliente.get_or_create_collection(
        name=coleccion_nombre,
        metadata={"hnsw:space": "cosine"},
    )

    if coleccion.count() > 0 and not sobreescribir:
        logger.info("Indice ya existe con %d chunks. Use --sobreescribir para regenerar.", coleccion.count())
        return coleccion.count()

    documentos = cargar_normativa(CARPETA_NORMATIVA)
    if not documentos:
        logger.warning("No se encontraron documentos en %s", CARPETA_NORMATIVA)
        return 0

    chunks_totales: list[dict] = []
    for doc in documentos:
        textos = dividir_en_chunks(doc["texto"])
        chunks = adjuntar_metadata(textos, doc["nombre"], doc["tipo"], doc["metadata"])
        chunks_totales.extend(chunks)

    if not chunks_totales:
        logger.warning("No se generaron chunks.")
        return 0

    textos_planos = [c["texto"] for c in chunks_totales]
    logger.info("Generando embeddings para %d chunks...", len(textos_planos))
    embeddings = embed_textos(textos_planos)

    coleccion.add(
        ids=[c["chunk_id"] for c in chunks_totales],
        embeddings=embeddings,
        documents=textos_planos,
        metadatas=[
            {
                "fuente": c["fuente"],
                "tipo_norma": c["tipo_norma"],
                "numero": c["numero"],
                "numero_norma": c.get("numero_norma", ""),
                "articulo": c["articulo"],
                "categoria_publicacion": c["categoria_publicacion"],
            }
            for c in chunks_totales
        ],
    )

    logger.info("Indexados %d chunks en Chroma.", len(chunks_totales))
    return len(chunks_totales)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Indexar normativa en Chroma.")
    parser.add_argument("--sobreescribir", action="store_true", help="Borra el indice previo antes de regenerar.")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    total = construir_indice(sobreescribir=args.sobreescribir)
    print(f"\nListo. {total} chunks indexados.")
