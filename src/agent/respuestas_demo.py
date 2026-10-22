"""Respuestas simuladas del LLM para el modo demo (sin API key).

Permite probar el agente completo (planificacion, enrutador, memoria,
herramientas y salida) sin consumir la API de Groq: solo el texto del LLM
esta simulado. Los veredictos de ejemplo provienen de corridas reales del
sistema (data/eval/v2/), no se inventa normativa nueva.
"""

from __future__ import annotations

import json
import re

PLAN_AUDITORIA = {
    "tipo_tarea": "auditoria",
    "pasos": [
        {
            "nombre": "memoria",
            "prioridad": 1,
            "justificacion": "Recuperar experiencias previas de casos similares para orientar la auditoria.",
        },
        {
            "nombre": "auditoria",
            "prioridad": 2,
            "justificacion": "Evaluar el cumplimiento de la normativa aplicable al trabajo publicado.",
        },
        {
            "nombre": "redaccion",
            "prioridad": 3,
            "justificacion": "Redactar el informe con observaciones, recomendaciones y plan de accion.",
        },
        {
            "nombre": "guardar_memoria",
            "prioridad": 4,
            "justificacion": "Persistir la experiencia para futuros casos.",
        },
    ],
}

PLAN_CONSULTA = {
    "tipo_tarea": "consulta_normativa",
    "pasos": [
        {
            "nombre": "memoria",
            "prioridad": 1,
            "justificacion": "Recuperar experiencias previas similares.",
        },
        {
            "nombre": "consulta_normativa",
            "prioridad": 2,
            "justificacion": "Buscar la normativa que responde la pregunta del usuario.",
        },
        {
            "nombre": "redaccion",
            "prioridad": 3,
            "justificacion": "Redactar la respuesta fundamentada con citas.",
        },
    ],
}

VEREDICTO_ALERTA = {
    "estado": "alerta",
    "alertas": [
        {
            "fuente": "RIC N°02",
            "articulo": "Punto 6.2.1-6.2.2",
            "mensaje": "El cableado interno del tablero debe dimensionarse segun las tablas del RIC N°04 y protegerse contra sobrecarga y cortocircuito.",
            "recomendacion": "Contratar a un instalador electrico certificado que elabore el calculo de carga y presente la Declaracion de Instalacion Electrica (TE1) con los planos de dimensionado.",
        },
        {
            "fuente": "RIC N°01",
            "articulo": "Punto 7.12.3",
            "mensaje": "El alimentador principal del tablero debe contar con proteccion contra sobrecargas y cortocircuitos ubicada en el primer recinto de empalmes.",
            "recomendacion": "Incluir en el proyecto la proteccion principal y exigir su certificacion al instalador.",
        },
    ],
    "recomendaciones_generales": [
        "Verificar que el profesional este inscrito en el Registro de Instaladores, Mantenedores y Certificadores del MINVU.",
        "Solicitar al menos dos cotizaciones de instaladores certificados.",
    ],
}

VEREDICTO_VAGO = {
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
}

REDACCION_INFORME = {
    "titulo": "Informe de auditoria de la publicacion (demostracion)",
    "cuerpo": (
        "La publicacion fue evaluada contra la normativa aplicable. "
        "Se recomienda verificar los requisitos indicados en las alertas antes de "
        "recibir cotizaciones: trabajos de este tipo suelen exigir personal "
        "autorizado por la SEC y, segun el alcance, acuerdo de la asamblea de "
        "copropietarios. Revisa las alertas citadas y ajusta la publicacion antes "
        "de publicarla."
    ),
    "acciones": [
        "Revisar las alertas con sus citas normativas.",
        "Adjuntar el alcance del trabajo y el plazo esperado.",
    ],
}

REDACCION_CUESTIONARIO = {
    "titulo": "Faltan datos en la publicacion: completa estos campos",
    "cuerpo": (
        "La publicacion no tiene informacion suficiente para describir el trabajo. "
        "No es posible redactar la solicitud sin inventar datos, asi que responde "
        "este cuestionario y publica la plantilla completa:\n\n"
        "1. Categoria del trabajo: [COMPLETAR] (electricidad, ascensor, gas, agua, otro)\n"
        "2. Descripcion del problema: [COMPLETAR] (que falla, desde cuando, donde)\n"
        "3. Ubicacion dentro del edificio: [COMPLETAR]\n"
        "4. Nivel de urgencia: [COMPLETAR] (normal, urgente)\n"
        "5. Fecha limite para recibir cotizaciones: [COMPLETAR]\n\n"
        "Plantilla de publicacion:\n"
        "Necesito [COMPLETAR tipo de trabajo] en [COMPLETAR ubicacion]. "
        "Problema: [COMPLETAR descripcion]. Urgencia: [COMPLETAR]. "
        "Recibo cotizaciones hasta [COMPLETAR fecha]."
    ),
    "acciones": [
        "Completar los campos [COMPLETAR] con la informacion real del trabajo.",
        "Volver a publicar la solicitud completa.",
    ],
}

REDACCION_CONSULTA = {
    "titulo": "Respuesta a la consulta normativa (demostracion)",
    "cuerpo": (
        "Segun la normativa recuperada, las intervenciones en areas comunes se "
        "rigen por la Ley 21.442 de Copropiedad Inmobiliaria y los Reglamentos de "
        "Instalaciones de Consumo de la SEC. Para tu caso concreto, revisa las "
        "fuentes citadas en los fragmentos recuperados; en modo demostracion no "
        "se cita un articulo especifico para no atribuir contenido que no fue "
        "verificado contra la fuente."
    ),
    "acciones": [
        "Consultar el texto completo en data/normativa/ o en bcn.cl / sec.cl.",
        "Verificar si el trabajo requiere personal autorizado por la SEC.",
    ],
}


def _parece_consulta(user: str) -> bool:
    return bool(re.search(r"\?|\b(cuales?|que|como)\b.*\b(exige|requiere|ley|norma)", user.lower()))


def _es_publicacion_vaga(user: str) -> bool:
    m = re.search(r"Publicacion(?: vaga o insuficiente)? \(categoria=[^)]*\): (.*)", user)
    texto = (m.group(1) if m else user).strip().lower()
    return len(texto) < 30 or "ayuda" in texto


def simular(system: str, user: str) -> str:
    """Devuelve el JSON simulado correspondiente al prompt recibido."""
    s = system.lower()
    if "planificador" in s:
        return json.dumps(PLAN_CONSULTA if _parece_consulta(user) else PLAN_AUDITORIA, ensure_ascii=False)
    if "redactor" in s:
        if "MODO: proponer_revision" in user:
            return json.dumps(REDACCION_CUESTIONARIO, ensure_ascii=False)
        if "MODO: respuesta_consulta" in user:
            return json.dumps(REDACCION_CONSULTA, ensure_ascii=False)
        return json.dumps(REDACCION_INFORME, ensure_ascii=False)
    return json.dumps(VEREDICTO_VAGO if _es_publicacion_vaga(user) else VEREDICTO_ALERTA, ensure_ascii=False)
