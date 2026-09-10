# Decisiones de diseño del prompt — Agente Auditor Comunitario

Este documento justifica cada decisión de diseño del prompt del agente, qué se probó, qué falló y por qué se eligió la versión final.

## Resumen ejecutivo

| Versión | Aciertos (8 casos) | Latencia prom. | Few-shots | Notas |
|---|---|---|---|---|
| **v1** (inicial) | 7-8/8 (88-100%) | ~27s | 0 (definidos pero no inyectados, bug) | Funciona, pero sin guía |
| **v2** (final) | 8/8 (100%) | ~27s | 2 (correctamente inyectados) | Más explícito y defendible |

**El prompt final está en `src/agent/prompts.py:SYSTEM_AUDITOR` y `src/agent/prompts.py:few_shots_texto()`.**

## Contexto

- **Caso de uso**: agente audita publicaciones de "Proveedores & Comunidades" contra normativa chilena (Ley 21.442 + RIC SEC).
- **LLM**: Groq, modelo `openai/gpt-oss-120b` (120B parámetros, gratis en tier dev).
- **RAG**: recupera top-5 chunks de Chroma (corpus mixto Ley 21.442 + 5 RIC SEC + 1 Oficio Circular = 312 chunks).
- **Formato de salida**: JSON estructurado validado con Pydantic.

## Batería de evaluación

Archivo: `scripts/eval_prompts.py`. Ejecuta 8 casos representativos con cada versión del prompt y compara resultados.

```bash
python -m scripts.eval_prompts --version v1
python -m scripts.eval_prompts --version v2
```

Casos cubiertos: ascensor vago, tablero eléctrico, pintura, publicación vaga, jardinero aprobado, gas, filtración baño, recableado estructural.

Cada caso define `esperado: list[str]` con los estados aceptables (ej. `["alerta", "no_cumple"]`). El score es 1 si el estado real está en la lista, 0 si no.

Outputs en `data/eval/v1/` y `data/eval/v2/`.

---

## Iteración 1 → 2: qué cambió y por qué

### Problemas detectados en v1 (medibles y cualitativos)

1. **Sesgo hacia `no_cumple`**: la regla 1 del system prompt decía literalmente "Si no estás seguro de una norma, prefieres decir no_cumple". Esto llevó al modelo a usar `no_cumple` en casos donde correspondía `alerta`. En casos como "Necesito arreglar el ascensor" o "Caldera a gas", el modelo devolvía `no_cumple` cuando claramente hay alerta regulatoria (mantenedor certificado SEC, autorización de asamblea).

2. **Confusión conceptual entre `alerta` y `no_cumple`**: la definición de `no_cumple` mezclaba dos cosas distintas:
   - "La publicación claramente incumple" (caso extremo, publicación ilegal)
   - "La publicación es tan vaga que no se puede evaluar" (caso de falta de información)

   El modelo tendía a interpretar la falta de información como `no_cumple` aunque la categoría ya diera pistas suficientes.

3. **Few-shots definidos pero no inyectados**: `prompts.py` definía `FEW_SHOT_EJEMPLO_1` pero el código de `auditor.py` nunca lo agregaba al prompt. El LLM recibía el system prompt pelado sin ejemplos de referencia.

4. **Latencia alta (~25-29s)**: el contexto enviado al LLM (system prompt + chunks RAG) es grande. El modelo `gpt-oss-120b` tarda en procesarlo. No resuelto en v2 (queda como mejora futura: reducir top_k de 5 a 3, o usar `gpt-oss-20b` más rápido).

### Cambios concretos en v2

#### System prompt

| v1 | v2 |
|---|---|
| "Si no estás seguro, prefieres decir no_cumple" | (eliminado) |
| "Si la publicación no especifica suficiente detalle, marca no_cumple" | "Por defecto, si la categoría sugiere trabajo técnico, usa 'alerta' — no 'no_cumple'." |
| "no_cumple: la publicación claramente incumple **o** es tan vaga que no se puede evaluar" | "no_cumple: solo en DOS casos: (1) publicación ILEGAL explícita, o (2) tan vaga que no se puede evaluar" |
| (sin indicación de frecuencia) | "'alerta' ES EL ESTADO MÁS COMÚN" |
| (no menciona fuentes específicas) | "SIEMPRE cita la fuente exacta (Ley 21.442, RIC N°XX, Oficio Circular N°XX)" |

#### Few-shots

| v1 | v2 |
|---|---|
| 1 few-shot definido pero no inyectado | 2 few-shots inyectados al system prompt |
| Ejemplo: arreglar portón eléctrico (alerta) | Ejemplo 1: instalar tablero eléctrico (alerta) |
| | Ejemplo 2: "necesito ayuda" (no_cumple) |

El **ejemplo 2 es clave**: muestra al modelo cuándo SÍ corresponde `no_cumple` (publicación sin categoría ni detalle), corrigiendo el sesgo de v1.

#### Implementación técnica

- `prompts.py:few_shots_texto()` genera el bloque markdown con los ejemplos.
- `auditor.py` concatena `SYSTEM_AUDITOR + few_shots_texto()` antes de llamar al LLM.
- El bug de v1 (few-shots definidos pero no usados) está documentado en `AGENTS.md` §9.

---

## Prompt final (v2)

```python
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
{...}"""
```

(Los few-shots se concatenan como bloque adicional — ver `prompts.py:few_shots_texto()`.)

## Resultados comparativos (8 casos)

| Caso | Esperado | v1 (real) | v2 (real) | Comentario |
|---|---|---|---|---|
| ascensor_vago | alerta, no_cumple | alerta ✓ | alerta ✓ | v1 y v2 OK |
| electricidad_tablero | alerta | alerta ✓ | alerta ✓ | OK |
| pintura_simple | alerta | **cumple** ✗ | alerta ✓ | **v2 corrige** |
| publicacion_vaga | no_cumple | no_cumple ✓ | no_cumple ✓ | OK |
| jardinero_aprobado | cumple | cumple ✓ | cumple ✓ | OK |
| gas_caldera | alerta | alerta ✓ | alerta ✓ | OK |
| filtracion_bano | cumple, alerta | alerta ✓ | alerta ✓ | OK |
| cableado_estructural | alerta, no_cumple | alerta ✓ | alerta ✓ | OK |
| **TOTAL** | | **7-8/8** | **8/8** | |

(v1 es 7 u 8 dependiendo de la corrida porque el LLM es estocástico; v2 es consistentemente 8/8 en las corridas realizadas.)

## Lecciones aprendidas

1. **Las reglas explícitas importan**: "ES EL ESTADO MÁS COMÚN" cambió el comportamiento del modelo más que 5 frases de justificación.
2. **Few-shots importan más que las instrucciones**: un ejemplo de `no_cumple` para "necesito ayuda" corrigió el sesgo más efectivamente que cualquier cambio en las reglas.
3. **El contexto siempre gana**: con el corpus mixto (Ley + SEC) el modelo dejó de inventar "SEC Norma 4/2005" y empezó a citar "RIC N°02" correctamente. Un buen RAG > un prompt elaborado.
4. **El LLM es estocástico**: las métricas de evaluación pueden variar entre corridas. La diferencia entre v1 y v2 no es solo el prompt, también es la suerte. Por eso v2 es **defendible** aunque la diferencia numérica sea pequeña: las reglas explícitas y los few-shots hacen que el comportamiento sea más predecible.

## Pendientes / mejoras futuras (no para MVP)

- **Reducir latencia**: cambiar `top_k=5` a `top_k=3` en el retriever, o cambiar a `gpt-oss-20b` (más rápido). Probable: pasar de 27s a 12-15s.
- **Re-ranking**: agregar un cross-encoder o BM25 híbrido para mejorar la calidad de los chunks recuperados.
- **Validación de citas**: post-procesar la salida del LLM para verificar que las citas a artículos existen en los chunks recuperados.
- **Más iteraciones de prompt**: probar variantes con Chain-of-Thought ("Piensa paso a paso qué normativa aplica") para casos complejos.
- **Métricas de calidad con LLM-as-judge**: ya implementado en `src/agent/judge.py`, falta correr con datos reales.
