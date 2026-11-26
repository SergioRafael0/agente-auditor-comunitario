"""Tests del LLM-as-judge (evaluacion de calidad de respuestas)."""

from __future__ import annotations

import json
from unittest.mock import patch

from src.agent import judge


def _registro() -> dict:
    return {
        "interaccion_id": "i1",
        "input": {"texto": "instalar tablero", "categoria": "electricidad"},
        "fragmentos_recuperados": [{"fuente": "RIC N°02", "articulo": "Punto 6.1"}],
        "respuesta": {"estado": "alerta", "n_alertas": 1},
    }


def test_evaluar_registro_devuelve_scores():
    respuesta = json.dumps({"relevancia_chunks": 0.9, "fundamentacion": 0.8, "completitud": 0.7})
    with patch.object(judge, "generar", return_value=respuesta) as mock_gen:
        scores = judge.evaluar_registro(_registro())
    assert scores == {"relevancia_chunks": 0.9, "fundamentacion": 0.8, "completitud": 0.7}
    assert mock_gen.call_args.kwargs["rol"] == "judge"
    assert mock_gen.call_args.kwargs["temperatura"] == 0.0


def test_evaluar_registro_json_invalido_devuelve_nulos():
    with patch.object(judge, "generar", return_value="no es json"):
        scores = judge.evaluar_registro(_registro())
    assert scores["relevancia_chunks"] is None
    assert scores["fundamentacion"] is None
    assert scores["completitud"] is None


def test_evaluar_todos_lee_el_log(monkeypatch, tmp_path):
    ruta = tmp_path / "interacciones.jsonl"
    ruta.write_text(json.dumps(_registro()) + "\n", encoding="utf-8")
    monkeypatch.setenv("LOG_FILE", str(ruta))
    respuesta = json.dumps({"relevancia_chunks": 1.0, "fundamentacion": 1.0, "completitud": 1.0})
    with patch.object(judge, "generar", return_value=respuesta):
        resultados = judge.evaluar_todos(limite=10)
    assert len(resultados) == 1
    assert resultados[0]["interaccion_id"] == "i1"
    assert resultados[0]["scores"]["relevancia_chunks"] == 1.0
