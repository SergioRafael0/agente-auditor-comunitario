"""Tests del indexer (ingest + chunk + embed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.indexer.chunk import (
    _extraer_articulo,
    _inferir_categoria,
    adjuntar_metadata,
    dividir_en_chunks,
)
from src.indexer.ingest import _inferir_metadata, cargar_normativa


def test_dividir_en_chunks_texto_corto():
    texto = "Articulo 1. El edificio es responsable de las areas comunes.\n\nArticulo 2. Los gastos comunes se reparten."
    chunks = dividir_en_chunks(texto, max_tokens=200)
    assert len(chunks) >= 2


def test_dividir_en_chunks_texto_vacio():
    assert dividir_en_chunks("") == []


def test_dividir_en_chunks_respeta_max_tokens():
    texto = "Articulo 1. " + ("Texto legal de prueba. " * 100)
    chunks = dividir_en_chunks(texto, max_tokens=50)
    assert all(len(c.split()) < 200 for c in chunks)


def test_extraer_articulo():
    assert _extraer_articulo("Articulo 17 dice que...") == "Artículo 17"
    assert _extraer_articulo("Sin articulo aqui") == ""


def test_inferir_categoria_electricidad():
    cats = _inferir_categoria("Trabajo de instalacion electrica en edificio")
    assert "electricidad" in cats


def test_inferir_categoria_ascensor():
    cats = _inferir_categoria("El ascensor presenta ruidos")
    assert "ascensor" in cats


def test_adjuntar_metadata():
    chunks = adjuntar_metadata(
        ["Articulo 1 sobre ascensores"],
        fuente="norma_sec",
        tipo="norma_tecnica",
        metadata_base={"numero": "20"},
    )
    assert len(chunks) == 1
    assert chunks[0]["articulo"] == "Artículo 1"
    assert chunks[0]["numero"] == "20"
    assert "ascensor" in chunks[0]["categoria_publicacion"]


def test_inferir_metadata_nombre_archivo():
    meta = _inferir_metadata("ley_21442_copropiedad")
    assert meta.get("numero") == "21442"


def test_cargar_normativa_vacio(tmp_path: Path):
    assert cargar_normativa(tmp_path) == []


def test_cargar_normativa_txt(tmp_path: Path):
    archivo = tmp_path / "ley_21442.txt"
    archivo.write_text("Articulo 1. Texto legal.", encoding="utf-8")
    docs = cargar_normativa(tmp_path)
    assert len(docs) == 1
    assert docs[0]["nombre"] == "ley_21442"
    assert "Articulo 1" in docs[0]["texto"]
