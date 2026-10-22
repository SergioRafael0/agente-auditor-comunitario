"""Tests de memoria de corto y largo plazo (mockeando embeddings)."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture()
def chroma_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    vectores_falsos = lambda texto: [0.1, 0.2, 0.3]
    with patch("src.memoria.largo_plazo.embed_textos", side_effect=[[0.1, 0.2, 0.3]] * 99):
        from src.memoria import largo_plazo

        largo_plazo._coleccion.cache_clear()
        yield largo_plazo
        largo_plazo._coleccion.cache_clear()


def test_guardar_y_buscar_experiencia(chroma_tmp):
    largo_plazo = chroma_tmp
    largo_plazo.guardar_experiencia("arreglar ascensor", "ascensor", "alerta", "2 alertas")

    def _embed_side(textos):
        return [[0.11, 0.19, 0.31]] * len(textos)

    with patch("src.memoria.largo_plazo.embed_textos", side_effect=_embed_side):
        experiencias = largo_plazo.buscar_experiencias("mantener ascensor", top_k=3)

    assert len(experiencias) == 1
    assert experiencias[0]["estado"] == "alerta"
    assert experiencias[0]["categoria"] == "ascensor"


def test_estado_invalido_rechazado(chroma_tmp):
    with pytest.raises(ValueError):
        chroma_tmp.guardar_experiencia("texto", "general", "estado_falso")


def test_buscar_sin_experiencias_devuelve_vacio(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma_vacio"))
    from src.memoria import largo_plazo

    largo_plazo._coleccion.cache_clear()
    resultados = largo_plazo.buscar_experiencias("lo que sea")
    assert resultados == []
    largo_plazo._coleccion.cache_clear()
