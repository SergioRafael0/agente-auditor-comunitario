"""Tests del retriever (mockeando Chroma para no requerir indice real)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.retriever import search


def test_buscar_retorna_lista_vacia_sin_indice():
    with patch.object(search, "_coleccion") as mock_col:
        mock_col.return_value.count.return_value = 0
        resultado = search.buscar("cualquier cosa")
        assert resultado == []


def test_buscar_usa_filtro_de_categoria():
    with patch.object(search, "_coleccion") as mock_col, patch.object(search, "embed_textos") as mock_embed:
        mock_col.return_value.count.return_value = 10
        mock_embed.return_value = [[0.1] * 384]
        mock_col.return_value.query.return_value = {
            "documents": [["texto recuperado"]],
            "metadatas": [[{"fuente": "ley_21442", "articulo": "Articulo 1", "tipo_norma": "ley"}]],
            "distances": [[0.1]],
        }

        resultado = search.buscar("arreglar porton", categoria="electricidad", top_k=3)

        assert len(resultado) == 1
        assert resultado[0]["fuente"] == "ley_21442"
        assert resultado[0]["score"] == pytest.approx(0.9, abs=1e-3)
        mock_col.return_value.query.assert_called_once()
        kwargs = mock_col.return_value.query.call_args.kwargs
        assert kwargs["where"]["categoria_publicacion"]["$contains"] == "electricidad"
