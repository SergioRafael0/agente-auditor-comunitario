"""Estimacion de tokens para textos en espanol."""

from __future__ import annotations


def estimar_tokens(texto: str) -> int:
    """Estimacion grosera: 1 token ~ 0.75 palabras en espanol."""
    return max(1, int(len(texto.split()) / 0.75))
