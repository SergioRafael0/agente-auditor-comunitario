"""Prompts de la herramienta de redaccion (escritura)."""

SYSTEM_REDACCION = """Eres el redactor comunitario especializado de la plataforma "Proveedores & Comunidades".

Escribes textos claros y accionables para administradores de comunidades y condominios en Chile.

Recibes una eleccion de MODO:
- "informe_auditoria": redactas un informe para el administrador a partir del veredicto del auditor.
- "proponer_revision": la publicacion es vaga o insuficiente; redactas una version corregida y completa de la publicacion que cumpla buenas practicas, incorporando las alertas.
- "respuesta_consulta": redactas una respuesta fundamentada a una consulta normativa, citando los fragmentos legales entregados.

Reglas:
1. Responde SOLO el JSON pedido, sin texto adicional ni bloques de codigo markdown.
2. NUNCA inventes articulos ni normas: solo usa las citas presentes en las alertas o fragmentos entregados.
3. Espanol de Chile, tono profesional y directo.

JSON de salida estricto (mismas claves SIEMPRE):
{
  "titulo": "titulo corto del texto generado",
  "cuerpo": "texto principal generado",
  "acciones": ["accion concreta 1", "accion concreta 2"]
}"""


TEMPLATES_MODO = {
    "informe_auditoria": (
        "MODO: informe_auditoria\n\n"
        "Publicacion (categoria={categoria}): {texto}\n\n"
        "Veredicto del auditor:\n{auditoria}\n\n"
        "Experiencias similares previas del sistema:\n{experiencias}\n\n"
        "Redacta el informe para el administrador."
    ),
    "proponer_revision": (
        "MODO: proponer_revision\n\n"
        "Publicacion vaga o insuficiente (categoria={categoria}): {texto}\n\n"
        "Veredicto del auditor:\n{auditoria}\n\n"
        "Redacta una version corregida de la publicacion, con categoria,"
        " descripcion detallada del problema, urgencia y requisitos normativos aplicables."
    ),
    "respuesta_consulta": (
        "MODO: respuesta_consulta\n\n"
        "Consulta del usuario (categoria={categoria}): {texto}\n\n"
        "Fragmentos de normativa recuperados:\n{fragmentos}\n\n"
        "Redacta la respuesta fundamentada con citas a los fragmentos."
    ),
}


def user_redaccion(
    modo: str,
    texto: str,
    categoria: str,
    auditoria: dict | None = None,
    fragmentos: list[dict] | None = None,
    experiencias: list[dict] | None = None,
) -> str:
    """Arma el mensaje de usuario segun el modo de redaccion."""
    import json

    datos = {
        "auditoria": json.dumps(auditoria or {}, ensure_ascii=False, indent=2),
        "fragmentos": "\n\n".join(
            f"[{f.get('fuente', '')} - {f.get('articulo', '')}]\n{f.get('texto', '')}"
            for f in (fragmentos or [])
        )
        or "(sin fragmentos)",
        "experiencias": "\n".join(
            f"- ({e.get('categoria', '')}) {e.get('texto', '')} -> {e.get('estado', '')}"
            for e in (experiencias or [])
        )
        or "(sin experiencias previas)",
    }
    plantilla = TEMPLATES_MODO.get(modo, TEMPLATES_MODO["informe_auditoria"])
    return plantilla.format(categoria=categoria, texto=texto, **datos)
