"""Ingesta de normativa: PDF/txt -> texto limpio."""

from __future__ import annotations

from pathlib import Path


def cargar_txt(ruta: Path) -> str:
    """Lee un archivo de texto plano y devuelve su contenido."""
    return ruta.read_text(encoding="utf-8")


def cargar_pdf(ruta: Path) -> str:
    """Lee un PDF y devuelve su texto. Usa pymupdf4llm si está disponible, pypdf como fallback."""
    try:
        import pymupdf4llm

        texto = pymupdf4llm.to_markdown(str(ruta))
    except ImportError:
        from pypdf import PdfReader

        reader = PdfReader(str(ruta))
        texto = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return _normalizar_unicode(texto)


def _normalizar_unicode(texto: str) -> str:
    """Reemplaza caracteres mal decodificados (latin-1 leido como utf-8) por su version correcta."""
    reemplazos = {
        "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú",
        "Ã\x81": "Á", "Ã\x89": "É", "Ã\x8d": "Í", "Ã\x93": "Ó", "Ã\x9a": "Ú",
        "Ã±": "ñ", "Ã\x91": "Ñ",
        "Â°": "°", "Â\xa0": " ", "Ãº": "ú", "Ã\x9a": "Ú",
        "ï¿½": "—", "¿": "¿", "â€™": "'", "â€œ": '"', "â€\x9d": '"',
    }
    for mal, bien in reemplazos.items():
        texto = texto.replace(mal, bien)
    try:
        texto.encode("utf-8")
    except UnicodeEncodeError:
        pass
    return texto


def cargar_normativa(carpeta: Path) -> list[dict]:
    """Carga todos los archivos de normativa de una carpeta.

    Devuelve lista de dicts con keys: ruta, nombre, tipo, texto, metadata.
    """
    documentos: list[dict] = []
    for ruta in sorted(carpeta.iterdir()):
        if ruta.name.startswith("."):
            continue
        if ruta.suffix.lower() == ".txt":
            texto = cargar_txt(ruta)
        elif ruta.suffix.lower() == ".pdf":
            texto = cargar_pdf(ruta)
        else:
            continue
        tipo = _inferir_tipo(ruta.name)
        documentos.append(
            {
                "ruta": str(ruta),
                "nombre": ruta.stem,
                "tipo": tipo,
                "texto": texto,
                "metadata": _inferir_metadata(ruta.stem),
            }
        )
    return documentos


def _inferir_tipo(nombre: str) -> str:
    """Heuristica para inferir el tipo de documento desde el nombre del archivo."""
    nombre_lower = nombre.lower()
    if nombre_lower.startswith("ley_") or "ley_" in nombre_lower or "dfl_" in nombre_lower:
        return "ley"
    if "decreto" in nombre_lower or nombre_lower.startswith("ds_"):
        return "decreto"
    if "oficio" in nombre_lower:
        return "oficio"
    if "ric_" in nombre_lower or "norma" in nombre_lower or "nch" in nombre_lower:
        return "norma_tecnica"
    return "norma_tecnica"


def _inferir_metadata(nombre: str) -> dict:
    """Heurística simple para extraer numero y tipo de un nombre de archivo."""
    metadata: dict = {}
    partes = nombre.lower().replace("-", "_").split("_")
    for parte in partes:
        if parte.isdigit():
            metadata["numero"] = parte
        elif parte in {"ley", "decreto", "norma", "ds", "sec"}:
            metadata["tipo_documento"] = parte
    return metadata
