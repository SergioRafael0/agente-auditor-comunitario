# Analisis de logs y trazas del agente (IE3)

Generado: 2026-11-26T16:43:27Z por `scripts/analizar_logs.py`.

## Fuentes analizadas

| Registro | Lineas |
| --- | --- |
| data/eventos.jsonl | 1461 |
| data/agente_ejecuciones.jsonl | 24 |
| data/interacciones.jsonl | 215 |

## Hallazgos priorizados

1. **[cuello_de_botella]** El nodo 'auditoria' concentra el 50% de la latencia del grafo
2. **[cuello_de_botella]** Las llamadas al LLM representan el 99% de la latencia medida en nodos
3. **[degradacion]** Se activaron 3 fallbacks: {'auditor': 1, 'planificador': 2}
4. **[degradacion]** 52 llamadas al LLM degradaron a modo demo por error de la API
5. **[anomalia]** 2 corridas con latencia outlier (> media + 2 desviaciones)
6. **[anomalia]** 53 fragmentos recuperados con score < 0.35 (baja confianza del retrieval)
7. **[anomalia]** Latencia inestable en 'planificador' (coef. variacion 1.74)
8. **[anomalia]** Latencia inestable en 'memoria' (coef. variacion 5.09)
9. **[anomalia]** Latencia inestable en 'auditoria' (coef. variacion 1.35)
10. **[anomalia]** Latencia inestable en 'redaccion' (coef. variacion 1.92)
11. **[anomalia]** Latencia inestable en 'finalizador' (coef. variacion 12.45)
12. **[patron]** La categoria 'electricidad' presenta 3 corridas con error de 16

## Cuellos de botella

### Por nodo del grafo

| Nodo | Ejec. | Total ms | Promedio ms | p95 ms | % latencia |
| --- | --- | --- | --- | --- | --- |
| auditoria | 132 | 2245151 | 17008.7 | 61307.05 | 50% |
| redaccion | 156 | 1864774 | 11953.7 | 61894.5 | 42% |
| planificador | 156 | 276621 | 1773.2 | 8772.5 | 6% |
| memoria | 156 | 55792 | 357.6 | 157.75 | 1% |
| guardar_memoria | 132 | 12794 | 96.9 | 188.54999999999978 | 0% |
| consulta_normativa | 24 | 1375 | 57.3 | 96.69999999999999 | 0% |
| finalizador | 156 | 1 | 0.0 | 0.0 | 0% |

### Por rol de llamada al LLM

| Rol | Llamadas | Total ms | Promedio ms | p95 ms | % latencia |
| --- | --- | --- | --- | --- | --- |
| auditor | 133 | 2285848 | 17186.8 | 61259.0 | 52% |
| redaccion | 156 | 1864547 | 11952.2 | 61894.0 | 42% |
| planificador | 156 | 276389 | 1771.7 | 8770.75 | 6% |

Las llamadas al LLM concentran el **99%** de la latencia total medida en nodos.

## Puntos de falla

- Fallos por nodo: `ninguno`
- Corridas con reintentos de pasos: **0**
- Fallbacks (degradaciones) registrados: **3**
- Llamadas al LLM degradadas a modo demo: **52**
- Corridas con errores en el estado: **3**

| trace_id | Errores |
| --- | --- |
| None | auditoria: Error code: 401 - {'error': {'message': 'Invalid API Key', 'type': 'invalid_request_error', 'code': 'expired_api_key'}}, auditoria: Error code: 401 - {'error': {'message': 'Invalid API Key', 'type': 'invalid_request_error', 'code': 'expired_api_key'}} |
| None | auditoria: Error code: 401 - {'error': {'message': 'Invalid API Key', 'type': 'invalid_request_error', 'code': 'expired_api_key'}}, auditoria: Error code: 401 - {'error': {'message': 'Invalid API Key', 'type': 'invalid_request_error', 'code': 'expired_api_key'}} |
| None | redaccion: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m24a580wehrvxqdx1q69dzyg` service tier `on_demand` on tokens per minute (TPM): Limit  |

## Anomalias

- Corridas con latencia outlier: **2**
- Fragmentos recuperados con score < 0.35: **53**
- Nodos con latencia inestable: **5**

| trace_id | Latencia ms | Umbral ms |
| --- | --- | --- |
| None | 51843 | 51237.1 |
| None | 56447 | 51237.1 |

## Patrones

| Categoria | Corridas | Con error | Latencia promedio ms |
| --- | --- | --- | --- |
| ascensor | 1 | 0 | 4280.0 |
| electricidad | 16 | 3 | 22508.8 |
| gas | 2 | 0 | 43118.5 |
| general | 5 | 0 | 11894.6 |

Distribucion de estados en interacciones:

`{'no_cumple': 45, 'alerta': 161, 'cumple': 9}`

Veredictos por tipo de tarea:

`{'auditoria': {'alerta': 11, 'no_cumple': 5, '(sin veredicto)': 2}, 'consulta_normativa': {'(sin veredicto)': 6}}`
