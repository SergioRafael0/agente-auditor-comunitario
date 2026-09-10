"""Tests del agente auditor (mockeando LLM y retriever)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.agent import auditor


@pytest.fixture(autouse=True)
def _entorno_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "interacciones.jsonl"))


def test_auditar_publicacion_alerta():
    respuesta_llm = json.dumps(
        {
            "estado": "alerta",
            "alertas": [
                {
                    "fuente": "SEC",
                    "articulo": "Reglamento Electrico",
                    "mensaje": "Requiere tecnico certificado",
                    "recomendacion": "Pedir licencia SEC",
                }
            ],
            "recomendaciones_generales": ["Solicitar 2 cotizaciones"],
        }
    )
    with (
        patch.object(auditor, "buscar", return_value=[]),
        patch.object(auditor, "generar", return_value=respuesta_llm),
    ):
        resultado = auditor.auditar_publicacion("arreglar porton electrico", "electricidad")

    assert resultado["estado"] == "alerta"
    assert len(resultado["alertas"]) == 1
    assert resultado["alertas"][0]["fuente"] == "SEC"
    assert "interaccion_id" in resultado
    assert "latencia_ms" in resultado


def test_auditar_publicacion_cumple():
    respuesta_llm = json.dumps({"estado": "cumple", "alertas": [], "recomendaciones_generales": []})
    with (
        patch.object(auditor, "buscar", return_value=[]),
        patch.object(auditor, "generar", return_value=respuesta_llm),
    ):
        resultado = auditor.auditar_publicacion("pintar el hall", "general")

    assert resultado["estado"] == "cumple"
    assert resultado["alertas"] == []


def test_auditar_publicacion_maneja_json_invalido():
    with (
        patch.object(auditor, "buscar", return_value=[]),
        patch.object(auditor, "generar", return_value="esto no es json"),
    ):
        resultado = auditor.auditar_publicacion("algo", "general")

    assert resultado["estado"] == "no_cumple"
    assert len(resultado["alertas"]) == 1


def test_auditar_registra_log(tmp_path, monkeypatch):
    log_file = tmp_path / "interacciones.jsonl"
    monkeypatch.setenv("LOG_FILE", str(log_file))
    respuesta_llm = json.dumps({"estado": "cumple", "alertas": [], "recomendaciones_generales": []})
    with (
        patch.object(auditor, "buscar", return_value=[]),
        patch.object(auditor, "generar", return_value=respuesta_llm),
    ):
        auditor.auditar_publicacion("pintar", "general")

    contenido = log_file.read_text(encoding="utf-8")
    assert contenido.strip()
    registro = json.loads(contenido.strip().splitlines()[0])
    assert registro["tool"] == "revisar_publicacion"
    assert registro["input"]["categoria"] == "general"
