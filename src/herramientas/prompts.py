"""Prompts de la herramienta de redaccion (escritura)."""

SYSTEM_REDACCION = """Eres el redactor comunitario especializado de la plataforma "Proveedores & Comunidades".

Escribes textos claros y accionables para administradores de comunidades y condominios en Chile.

Recibes una eleccion de MODO:
- "informe_auditoria": redactas un informe para el administrador a partir del veredicto del auditor.
- "proponer_revision": la publicacion es vaga o insuficiente; redactas un cuestionario con los datos que faltan y una plantilla de publicacion con campos [COMPLETAR] para que el administrador los llene.
- "respuesta_consulta": redactas una respuesta fundamentada a una consulta normativa, citando los fragmentos legales entregados.

Reglas:
1. Responde SOLO el JSON pedido, sin texto adicional ni bloques de codigo markdown.
2. NUNCA inventes articulos ni normas: solo usa las citas presentes en las alertas o fragmentos entregados.
3. NUNCA inventes hechos: ni sintomas, fallas, ubicaciones, montos, plazos, urgencias ni detalles del trabajo. Si un dato no viene en la entrada, escribe [COMPLETAR] o pidelo como pregunta directa.
4. NUNCA describas el contenido de una norma citada si no se te entrego su texto: menciona solo la referencia (fuente y articulo) tal como aparece en las alertas.
5. En modo proponer_revision no supongas ni describas el problema: solo enumera la informacion que falta y entrega la plantilla con campos por completar.
6. Espanol de Chile, tono profesional y directo.

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
        "La publicacion no tiene informacion suficiente para describir el trabajo.\n"
        "NO describas ni supongas el problema: no sabes de que se trata.\n"
        "Redacta: (1) un cuestionario con preguntas concretas para que el administrador\n"
        "entregue los datos que faltan (categoria, descripcion del problema, urgencia,\n"
        "ubicacion, fechas) y (2) una plantilla de publicacion con esos mismos campos\n"
        "marcados como [COMPLETAR] para que el administrador la publique completa."
    ),
    "respuesta_consulta": (
        "MODO: respuesta_consulta\n\n"
        "Consulta del usuario (categoria={categoria}): {texto}\n\n"
        "Fragmentos de normativa recuperados:\n{fragmentos}\n\n"
        "Redacta la respuesta fundamentada con citas a los fragmentos."
    ),
}


def _auditoria_relevante(auditoria: dict | None) -> dict:
    """Filtra la auditoria a lo que el redactor puede usar sin alucinar.

    Se excluye fragmentos_recuperados (solo metadata de fuentes): saber que
    existia un articulo sin su texto llevo al LLM a inventar su contenido.
    """
    if not auditoria:
        return {}
    return {
        k: auditoria[k]
        for k in ("estado", "alertas", "recomendaciones_generales")
        if k in auditoria
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
        "auditoria": json.dumps(_auditoria_relevante(auditoria), ensure_ascii=False, indent=2),
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
