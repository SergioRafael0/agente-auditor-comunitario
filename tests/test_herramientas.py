"""Tests de las herramientas del agente (mockeando LLM y retriever)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from src.herramientas.consulta import buscar_normativa
from src.herramientas.razonamiento import auditar

def test_buscar_normativa_devuelve_fragmentos():
    fragmentos_falsos = [
        {"texto": "Articulo 17...", "fuente": "Ley 21.442", "articulo": "Artículo 17", "score": 0.8}
    ]
    with patch("src.herramientas.consulta.buscar", return_value=fragmentos_falsos) as mock_buscar:
        resultado = buscar_normativa("requisitos ascensor", categoria="ascensor")

    assert resultado["n_fragmentos"] == 1
    assert resultado["fuentes"] == ["Ley 21.442"]
    assert resultado["fragmentos"][0]["articulo"] == "Artículo 17"
    mock_buscar.assert_called_once_with("requisitos ascensor", categoria="ascensor", top_k=5)


def test_buscar_normativa_sin_resultados():
    with patch("src.herramientas.consulta.buscar", return_value=[]):
        resultado = buscar_normativa("zzz-nada-relevante")
    assert resultado["n_fragmentos"] == 0
    assert resultado["fuentes"] == []


def test_auditar_reenvia_al_nucleo_ev1():
    respuesta_llm = json.dumps({"estado": "alerta", "alertas": [], "recomendaciones_generales": []})
    with (
        patch("src.agent.auditor.buscar", return_value=[]),
        patch("src.agent.auditor.generar", return_value=respuesta_llm),
    ):
        from src.herramientas.razonamiento import auditar

        resultado = auditar("arreglar porton", "electricidad")
    assert resultado["estado"] == "alerta"
    assert resultado["categoria"] == "electricidad"


def test_redactar_json_valido():
    llm_json = json.dumps(
        {"titulo": "Informe", "cuerpo": "Texto del informe", "acciones": ["Action 1"]}
    )
    with patch("src.herramientas.redaccion.generar", return_value=llm_json):
        from src.herramientas.redaccion import redactar

        resultado = redactar("informe_auditoria", "texto", "electricidad")
    assert resultado["modo"] == "informe_auditoria"
    assert resultado["titulo"] == "Informe"
    assert resultado["acciones"] == ["Action 1"]


def test_redactar_json_invalido_da_respaldo():
    with patch("src.herramientas.redaccion.generar", return_value="no soy json"):
        from src.herramientas.redaccion import redactar

        resultado = redactar("proponer_revision", "texto")
    assert resultado["titulo"] == ""
    assert resultado["cuerpo"] == ""
    assert resultado["acciones"] == []


def test_redactar_modo_invalido_lanza_error():
    from src.herramientas.redaccion import redactar

    with pytest.raises(ValueError):
        redactar("modo_inexistente", "texto")


def test_proponer_revision_pide_datos_no_inventa():
    from src.herramientas.prompts import user_redaccion

    mensaje = user_redaccion(
        modo="proponer_revision",
        texto="Necesito ayuda con unas cosas del edificio",
        categoria="general",
        auditoria={"estado": "no_cumple", "alertas": []},
    )
    assert "[COMPLETAR]" in mensaje
    assert "cuestionario" in mensaje.lower()
    assert "descripcion detallada del problema" not in mensaje
    assert "NO describas ni supongas el problema" in mensaje


def test_user_redaccion_no_expone_fragmentos_recuperados():
    from src.herramientas.prompts import user_redaccion

    auditoria = {
        "estado": "no_cumple",
        "alertas": [{"fuente": "Plataforma", "articulo": "-", "mensaje": "vaga"}],
        "recomendaciones_generales": [],
        "fragmentos_recuperados": [
            {"fuente": "sec_ric_01_empalmes", "articulo": "Punto 7.6", "score": 0.48}
        ],
        "latencia_ms": 1234,
    }
    mensaje = user_redaccion(
        modo="proponer_revision",
        texto="Necesito ayuda",
        categoria="general",
        auditoria=auditoria,
    )
    assert "fragmentos_recuperados" not in mensaje
    assert "empalmes" not in mensaje
    assert "score" not in mensaje
    assert "Plataforma" in mensaje


def test_system_redaccion_prohibe_inventar_hechos():
    from src.herramientas.prompts import SYSTEM_REDACCION

    assert "NUNCA inventes hechos" in SYSTEM_REDACCION
    assert "[COMPLETAR]" in SYSTEM_REDACCION
