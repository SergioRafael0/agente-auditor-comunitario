# Resultados LLM-as-Judge — Coherencia datos↔respuestas (IE6)

Evaluación cuantitativa de la calidad del agente usando un LLM como juez externo.

## Resumen ejecutivo

| Métrica | v1 (prompt original) | v2 (prompt refinado) | Mejora |
|---|---|---|---|
| **Relevancia de chunks** | 0.425 | **0.512** | +20% |
| **Fundamentación** | 0.338 | 0.338 | sin cambio |
| **Completitud** | 0.325 | **0.475** | +46% |

**Interpretación**: el prompt v2 recupera chunks más relevantes y entrega respuestas más completas. La fundamentación (que la respuesta se base en los chunks) se mantiene en 0.34, lo que indica que es un área de mejora prioritaria (probablemente requiera validación post-procesamiento o re-ranking).

## Metodología

- **Juez**: `openai/gpt-oss-120b` (mismo LLM que el agente, pero con system prompt diferente)
- **Set evaluado**: 16 interacciones reales generadas por `scripts/eval_prompts.py` (8 casos × 2 versiones de prompt)
- **Casos cubiertos**: ascensor, tablero eléctrico, pintura, publicación vaga, jardinero, gas, filtración, recableado
- **Métricas** (escala 0.0-1.0):
  - **relevancia_chunks**: ¿los chunks recuperados son relevantes a la publicación?
  - **fundamentacion**: ¿la respuesta se basa en los chunks o inventa?
  - **completitud**: ¿falta normativa importante que debería haberse mencionado?

## Resultados detallados

### Por versión de prompt

#### v1 (n=8)
| Métrica | Promedio | Min | Max |
|---|---|---|---|
| relevancia_chunks | 0.425 | 0.0 | 0.8 |
| fundamentacion | 0.338 | 0.0 | 0.9 |
| completitud | 0.325 | 0.0 | 0.6 |

#### v2 (n=8)
| Métrica | Promedio | Min | Max |
|---|---|---|---|
| relevancia_chunks | 0.512 | 0.0 | 0.8 |
| fundamentacion | 0.338 | 0.0 | 1.0 |
| completitud | 0.475 | 0.2 | 1.0 |

## Análisis

### Lo que funciona bien

- **Chunks relevantes** (v2): 0.512 es un score moderado. Cuando el corpus tiene contenido directamente aplicable (ej. RIC N°02 para tableros eléctricos), el retrieval lo encuentra.
- **Mejora v1→v2 en completitud (+46%)**: el prompt v2 instruye más explícitamente a citar fuentes y considerar todas las alertas relevantes. Se nota en los resultados.

### Áreas de mejora (más allá del MVP)

1. **Fundamentación baja (0.338)**: el LLM-as-judge detecta que la respuesta del agente a veces no se ancla bien en los chunks. Tres posibles causas:
   - El agente recibe los chunks pero los parafrasea libremente en vez de citarlos literalmente
   - El LLM mezcla información de los chunks con conocimiento previo (alucinación parcial)
   - El system prompt no es lo suficientemente estricto con "basar la respuesta en los chunks entregados"
   
   **Mejora futura**: agregar un post-procesador que valide que cada alerta cita un chunk de los entregados.

2. **Relevancia mejorable (0.512)**: el retrieval vectorial a veces devuelve chunks tangenciales.
   
   **Mejora futura**: implementar hybrid search (BM25 + vectorial) o re-ranking con cross-encoder.

3. **Completitud mejorable (0.475)**: el corpus no cubre toda la normativa posible.
   
   **Mejora futura**: agregar más RIC (especialmente N°04 Conductores y N°07-N°15 si existen) + normativa SEC de ascensores, gas, eficiencia energética.

## Cómo reproducir

```bash
# 1. Generar las 16 interacciones
python -m scripts.eval_prompts --version v1
python -m scripts.eval_prompts --version v2

# 2. Evaluar con LLM-as-judge
python -m scripts.evaluar_con_judge

# 3. Ver resultados
cat data/eval/judge_results.json | python -m json.tool
```

Outputs:
- `data/eval/v1/*.json` y `data/eval/v2/*.json`: outputs del agente
- `data/judge_input.jsonl`: registros en formato que espera `judge.py`
- `data/eval/judge_results.json`: resultados del juez con promedios

## Limitaciones del método

- **Mismo modelo como juez y como agente** puede introducir sesgo (el juez puede favorecer el estilo del prompt v2 porque comparte el mismo modelo base).
- **Solo 8 casos** por versión — una muestra pequeña. Para el MVP es suficiente; para producción se necesitarían 50+ casos.
- **El juez no es perfecto**: scores bajos pueden reflejar problemas del juez, no del agente. Es una heurística, no una verdad absoluta.
- **No evalúa latencia ni costo**: solo calidad. Para esos hay otras métricas (en `data/eval/v*/_resumen.json`).
