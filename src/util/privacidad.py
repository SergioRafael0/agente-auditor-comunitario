"""Privacidad de datos en los registros de observabilidad.

Los logs guardan el texto de las publicaciones para poder analizar fallas,
pero ese texto puede contener datos personales (telefonos, correos, RUT).
`texto_para_log` los reemplaza por marcadores antes de persistir, y
`hash_texto` permite correlacionar entradas repetidas sin conservar el
contenido (usado como huella digital en evidencias anonimas).

Normativa de referencia: Ley 19.628 sobre proteccion de datos personales
y Ley 21.719 de proteccion de datos personales (Chile).
"""

from __future__ import annotations

import hashlib
import os
import re

_PATRONES = (
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[CORREO]"),
    (re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b"), "[RUT]"),
    (re.compile(r"\b(?:\+?56[\s-]?)?(?:9[\s-]?)?\d{4}[\s-]?\d{4}\b"), "[TELEFONO]"),
)


def anonimizar_texto(texto: str) -> str:
    """Reemplaza correos, RUTs y telefonos por marcadores."""
    resultado = texto
    for patron, marcador in _PATRONES:
        resultado = patron.sub(marcador, resultado)
    return resultado


def hash_texto(texto: str) -> str:
    """Huella digital (SHA-256, 16 hex) que correlaciona sin exponer el texto."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def texto_para_log(texto: str) -> str:
    """Texto seguro para persistir: anonimizado salvo que LOG_ANONIMIZAR=0."""
    if os.getenv("LOG_ANONIMIZAR", "1").strip().lower() in ("0", "false", "no"):
        return texto
    return anonimizar_texto(texto)
