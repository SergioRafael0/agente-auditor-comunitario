"""Tests del extractor robusto de JSON de respuestas LLM."""

from __future__ import annotations

import json

import pytest

from src.util.json_utils import extraer_json


def test_json_limpio():
    assert extraer_json('{"a": 1}') == {"a": 1}


def test_json_en_fences():
    raw = '```json\n{"estado": "alerta", "n": 2}\n```'
    assert extraer_json(raw) == {"estado": "alerta", "n": 2}


def test_json_con_texto_alrededor():
    raw = 'Aca va mi respuesta:\n{"plan": ["memoria", "auditoria"]}\nEspero te sirva.'
    assert extraer_json(raw) == {"plan": ["memoria", "auditoria"]}


def test_json_con_llaves_anidadas():
    raw = '{"a": {"b": "c}"}, "d": 1}'
    assert extraer_json(raw) == {"a": {"b": "c}"}, "d": 1}


def test_sin_json_lanza_error():
    with pytest.raises(json.JSONDecodeError):
        extraer_json("no hay json aqui")


def test_respuesta_vacia_lanza_error():
    with pytest.raises(json.JSONDecodeError):
        extraer_json("")
