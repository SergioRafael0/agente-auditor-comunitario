"""Tests de la CLI del grafo (src/grafo/cli.py)."""

from __future__ import annotations

import sys

from src.grafo import cli


def test_cli_ejecuta_y_muestra_respuesta(monkeypatch, capsys):
    estado = {
        "respuesta_final": "respuesta de prueba",
        "bitacora": [{"nodo": "enrutador", "decision": "despacho"}],
    }
    monkeypatch.setattr(cli, "invocar_agente", lambda *a, **k: estado)
    monkeypatch.setattr(sys, "argv", ["cli", "--texto", "instalar tablero", "--categoria", "electricidad"])

    cli.main()

    salida = capsys.readouterr().out
    assert "respuesta de prueba" in salida
    assert "despacho" in salida
