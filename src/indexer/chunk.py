"""Chunking de texto legal por articulos/secciones."""

from __future__ import annotations

import re
from typing import Iterable


PATRON_SECCION = re.compile(
    r"^(?:Art[ií]culo\s+\d+|Art\.\s*\d+|T[ií]tulo\s+[IVXLCDM]+|Cap[ií]tulo\s+[IVXLCDM]+|P[aá]rrafo\s+\d+)",
    re.MULTILINE | re.IGNORECASE,
)

PATRON_NUMERO_NORMA = re.compile(
    r"(?:RIC|Pliego\s+T[eé]cnico\s+Normativo)\s+N[°ºo]?\s*(\d{1,3})",
    re.IGNORECASE,
)


def dividir_en_chunks(
    texto: str,
    overlap_tokens: int = 100,
    max_tokens: int = 500,
) -> list[str]:
    """Divide texto legal en chunks respetando articulos cuando es posible.

    Estrategia:
    1. Intentar partir por patron de Articulo / Art. / Titulo / Capitulo / Parrafo.
       Si el patron matchea, cada coincidencia es una fractura dura: no se fusiona
       con el chunk anterior aunque quepa en max_tokens (cada articulo merece su
       propia cita en metadata).
    2. Si una seccion resultante supera max_tokens, partirla por parrafos/oraciones.
    3. Agregar overlap entre chunks adyacentes (estimado por palabras).
    """
    secciones = _split_por_secciones(texto)
    if not secciones:
        return []

    chunks: list[str] = []

    for seccion in secciones:
        tokens_seccion = _estimar_tokens(seccion)
        if tokens_seccion <= max_tokens:
            chunks.append(seccion)
        else:
            chunks.extend(_partir_largo(seccion, max_tokens))

    if overlap_tokens > 0 and len(chunks) > 1:
        chunks = _agregar_overlap(chunks, overlap_tokens)

    return chunks


def _split_por_secciones(texto: str) -> list[str]:
    """Divide el texto en cada coincidencia de Articulo/Titulo/Capitulo al inicio de linea."""
    lineas = texto.splitlines()
    secciones: list[str] = []
    buffer: list[str] = []

    for linea in lineas:
        if PATRON_SECCION.match(linea.strip()) and buffer:
            secciones.append("\n".join(buffer).strip())
            buffer = [linea]
        else:
            buffer.append(linea)

    if buffer:
        secciones.append("\n".join(buffer).strip())

    return [s for s in secciones if s]


def _partir_largo(texto: str, max_tokens: int) -> list[str]:
    """Parte un texto largo por parrafos u oraciones respetando max_tokens."""
    if "\n\n" in texto:
        unidades = [p.strip() for p in texto.split("\n\n") if p.strip()]
    elif "\n" in texto:
        unidades = [p.strip() for p in texto.split("\n") if p.strip()]
    else:
        unidades = _partir_en_oraciones(texto)

    chunks: list[str] = []
    buffer = ""

    for unidad in unidades:
        if _estimar_tokens(buffer) + _estimar_tokens(unidad) <= max_tokens:
            buffer = f"{buffer}\n\n{unidad}".strip() if buffer else unidad
        else:
            if buffer:
                chunks.append(buffer)
            if _estimar_tokens(unidad) > max_tokens:
                chunks.extend(_partir_en_oraciones_con_limite(unidad, max_tokens))
                buffer = ""
            else:
                buffer = unidad

    if buffer:
        chunks.append(buffer)

    return chunks


def _partir_en_oraciones(texto: str) -> list[str]:
    """Parte por punto seguido de espacio, fallback agresivo."""
    partes = re.split(r"(?<=[.!?])\s+", texto)
    return [p.strip() for p in partes if p.strip()]


def _partir_en_oraciones_con_limite(texto: str, max_tokens: int) -> list[str]:
    """Parte por oraciones y luego agrupa respetando max_tokens."""
    oraciones = _partir_en_oraciones(texto)
    chunks: list[str] = []
    buffer = ""
    for oracion in oraciones:
        if _estimar_tokens(buffer) + _estimar_tokens(oracion) <= max_tokens:
            buffer = f"{buffer} {oracion}".strip() if buffer else oracion
        else:
            if buffer:
                chunks.append(buffer)
            buffer = oracion
    if buffer:
        chunks.append(buffer)
    return chunks


def _agregar_overlap(chunks: list[str], overlap_tokens: int) -> list[str]:
    """Antepone los ultimos overlap_tokens del chunk anterior al siguiente."""
    resultado = [chunks[0]]
    for i in range(1, len(chunks)):
        anterior = chunks[i - 1]
        palabras = anterior.split()
        overlap_words = palabras[-overlap_tokens:] if len(palabras) > overlap_tokens else palabras
        overlap = " ".join(overlap_words)
        resultado.append(f"{overlap}\n\n{chunks[i]}")
    return resultado


def _estimar_tokens(texto: str) -> int:
    """Estimacion grosera: 1 token ~ 0.75 palabras en espanol."""
    return max(1, int(len(texto.split()) / 0.75))


def adjuntar_metadata(
    chunks: Iterable[str],
    fuente: str,
    tipo: str,
    metadata_base: dict,
) -> list[dict]:
    """Genera dicts con metadata por chunk para Chroma."""
    resultado: list[dict] = []
    for i, texto in enumerate(chunks):
        articulo = _extraer_articulo(texto)
        numero_norma = _extraer_numero_norma(texto, fuente)
        categorias = _inferir_categoria(texto)
        resultado.append(
            {
                "texto": texto,
                "fuente": fuente,
                "tipo_norma": tipo,
                "numero": metadata_base.get("numero", ""),
                "numero_norma": numero_norma,
                "articulo": articulo,
                "categoria_publicacion": ",".join(categorias),
                "chunk_id": f"{fuente}::{i}",
            }
        )
    return resultado


def _extraer_articulo(texto: str) -> str:
    patrones = [
        (r"Art[ií]culo\s+(\d+(?:\.\d+)*)", lambda m: f"Artículo {m.group(1)}"),
        (r"Cap[ií]tulo\s+([IVXLCDM]+|\d+)", lambda m: f"Capítulo {m.group(1)}"),
        (r"T[ií]tulo\s+([IVXLCDM]+|\d+)", lambda m: f"Título {m.group(1)}"),
        (r"P[aá]rrafo\s+(\d+)", lambda m: f"Párrafo {m.group(1)}"),
        (r"(?:punto|secci[oó]n|n[°º]?)\s+(\d+(?:\.\d+)*)", lambda m: f"Punto {m.group(1)}"),
    ]
    for patron, fmt in patrones:
        m = re.search(patron, texto, re.IGNORECASE)
        if m:
            return fmt(m)
    return ""


def _extraer_numero_norma(texto: str, fuente: str) -> str:
    """Detecta el numero de la norma desde el nombre del archivo fuente (no del texto).

    Esto evita confusion cuando un chunk referencia a otras normas (ej. RIC N°03
    cita a RIC N°10): el numero_norma siempre refleja el archivo de origen.
    """
    fuente_lower = fuente.lower()
    if fuente_lower.startswith("ric_") or "ric" in fuente_lower:
        m = re.search(r"ric_(\d{1,3})", fuente_lower)
        if m:
            return f"RIC N°{m.group(1).zfill(2)}"
    if "oficio" in fuente_lower:
        nums = re.findall(r"\d+", fuente)
        return f"Oficio Circular N°{nums[-1]}" if nums else "Oficio Circular"
    if "ley_21442" in fuente_lower or "ley 21442" in fuente_lower:
        return "Ley 21.442"
    return fuente


_CATEGORIAS_KEYWORDS = {
    "electricidad": ["eléctric", "electric", "instalación eléctrica", "sec"],
    "ascensor": ["ascensor", "elevador", "montacarga"],
    "gas": ["gas", "caldera", "calefón"],
    "agua": ["agua", "sanitari", "gasfiter", "filtración"],
    "general": ["comunidad", "edificio", "copropiedad", "gasto común"],
}


def _inferir_categoria(texto: str) -> list[str]:
    texto_lower = texto.lower()
    encontradas = []
    for cat, keywords in _CATEGORIAS_KEYWORDS.items():
        if any(kw in texto_lower for kw in keywords):
            encontradas.append(cat)
    return encontradas or ["general"]
