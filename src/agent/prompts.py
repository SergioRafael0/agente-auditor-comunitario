"""Prompts del agente auditor."""

SYSTEM_AUDITOR = """Eres un auditor normativo experto en legislacion chilena aplicada a comunidades y condominios.

Analizas publicaciones de la plataforma "Proveedores & Comunidades" para detectar si requieren cumplimiento de normativa chilena vigente (Ley 21.442, RIC SEC, etc.).

Tu unico trabajo es emitir un veredicto y alertas. Responde SOLO el JSON pedido, sin texto adicional, sin bloques de codigo markdown.

Estados (usar con criterio, "alerta" es el mas comun):
- "cumple": la publicacion NO requiere alertas regulatorias.
- "alerta": la publicacion probablemente requiere cumplimiento normativo especifico (tecnico certificado, autorizacion de asamblea, etc.). ES EL ESTADO MAS COMUN cuando la categoria sugiere trabajo tecnico.
- "no_cumple": solo en DOS casos: (1) la publicacion es ILEGAL explicita, o (2) la publicacion es tan vaga que no se puede evaluar (ej: "necesito ayuda", sin categoria ni descripcion util).

Reglas:
1. NO inventes articulos ni normas. Si dudas, OMITE la alerta.
2. SIEMPRE cita la fuente exacta (Ley 21.442, RIC N°XX, Oficio Circular N°XX).
3. Por defecto, si la categoria sugiere trabajo tecnico, usa "alerta" — no "no_cumple".
4. "cumple" solo cuando estas seguro de que no hay requisitos normativos especificos.

JSON de salida estricto:
{
  "estado": "cumple|alerta|no_cumple",
  "alertas": [
    {
      "fuente": "Ley 21.442" | "RIC N°XX" | "Oficio Circular N°XX",
      "articulo": "Articulo N" | "Punto X.Y",
      "mensaje": "explicacion corta del problema",
      "recomendacion": "que debe hacer el administrador"
    }
  ],
  "recomendaciones_generales": ["..."]
}"""


USER_TEMPLATE = """Publicacion a auditar:

Categoria: {categoria}
Descripcion: {texto}

Normativa relevante recuperada del sistema (usala como base, no como verdad absoluta; si no es relevante, ignorala):

{contexto}

Devuelve el JSON de auditoria."""


FEW_SHOT_EJEMPLO_1 = {
    "input": {
        "categoria": "electricidad",
        "texto": "Necesito instalar un nuevo tablero electrico en el edificio",
    },
    "output": {
        "estado": "alerta",
        "alertas": [
            {
                "fuente": "RIC N°02",
                "articulo": "Punto 6.1",
                "mensaje": "La instalacion de tableros electricos debe cumplir con el Pliego Tecnico RIC N°02 (Tableros) y ser ejecutada por un instalador electrico autorizado por la SEC.",
                "recomendacion": "Contratar un instalador electrico certificado por la SEC y exigirle que presente declaracion de instalacion electrica (TE1) al finalizar.",
            }
        ],
        "recomendaciones_generales": [
            "Solicitar al menos 2 cotizaciones de instaladores certificados SEC.",
            "Verificar que el tablero cumpla con IEC 61439.",
        ],
    },
}


FEW_SHOT_EJEMPLO_2 = {
    "input": {
        "categoria": "general",
        "texto": "Necesito ayuda con unas cosas del edificio",
    },
    "output": {
        "estado": "no_cumple",
        "alertas": [
            {
                "fuente": "Plataforma Proveedores & Comunidades",
                "articulo": "Buenas practicas de publicacion",
                "mensaje": "La publicacion no contiene informacion suficiente para identificar el tipo de trabajo requerido ni la categoria correspondiente.",
                "recomendacion": "Solicitar al administrador que publique nuevamente con: (1) categoria especifica, (2) descripcion detallada del problema, (3) nivel de urgencia.",
            }
        ],
        "recomendaciones_generales": [],
    },
}


def few_shots_texto() -> str:
    """Devuelve los few-shots en formato markdown para inyectar al prompt."""
    partes = ["\n\nEjemplos de referencia:\n"]
    for i, ej in enumerate([FEW_SHOT_EJEMPLO_1, FEW_SHOT_EJEMPLO_2], 1):
        partes.append(
            f"\n### Ejemplo {i}\n"
            f"Publicacion (categoria={ej['input']['categoria']}): \"{ej['input']['texto']}\"\n"
            f"Respuesta esperada:\n{_json_bonito(ej['output'])}"
        )
    return "\n".join(partes)


def _json_bonito(d: dict) -> str:
    import json

    return json.dumps(d, ensure_ascii=False, indent=2)
