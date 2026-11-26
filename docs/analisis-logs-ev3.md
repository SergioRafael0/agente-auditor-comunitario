# Analisis de logs y trazas del agente (IE3)

Generado: 2026-11-26T15:19:21Z por `scripts/analizar_logs.py`.

## Fuentes analizadas

| Registro | Lineas |
| --- | --- |
| data/eventos.jsonl | 791 |
| data/agente_ejecuciones.jsonl | 24 |
| data/interacciones.jsonl | 159 |

## Hallazgos priorizados

1. **[cuello_de_botella]** El nodo 'auditoria' concentra el 63% de la latencia del grafo
2. **[cuello_de_botella]** Las llamadas al LLM representan el 96% de la latencia medida en nodos
3. **[degradacion]** 9 llamadas al LLM degradaron a modo demo por error de la API
4. **[anomalia]** 2 corridas con latencia outlier (> media + 2 desviaciones)
5. **[anomalia]** 53 fragmentos recuperados con score < 0.35 (baja confianza del retrieval)
6. **[anomalia]** Latencia inestable en 'planificador' (coef. variacion 1.41)
7. **[anomalia]** Latencia inestable en 'memoria' (coef. variacion 5.21)
8. **[anomalia]** Latencia inestable en 'auditoria' (coef. variacion 1.22)
9. **[anomalia]** Latencia inestable en 'redaccion' (coef. variacion 1.66)
10. **[anomalia]** Latencia inestable en 'finalizador' (coef. variacion 9.49)
11. **[patron]** La categoria 'electricidad' presenta 3 corridas con error de 16

## Cuellos de botella

### Por nodo del grafo

| Nodo | Ejec. | Total ms | Promedio ms | p95 ms | % latencia |
| --- | --- | --- | --- | --- | --- |
| auditoria | 77 | 952030 | 12364.0 | 40089.0 | 63% |
| redaccion | 91 | 280212 | 3079.3 | 12876.5 | 18% |
| planificador | 91 | 242663 | 2666.6 | 9806.5 | 16% |
| memoria | 91 | 30755 | 338.0 | 158.5 | 2% |
| guardar_memoria | 77 | 8731 | 113.4 | 220.40000000000003 | 1% |
| consulta_normativa | 14 | 858 | 61.3 | 112.49999999999999 | 0% |
| finalizador | 91 | 1 | 0.0 | 0.0 | 0% |

### Por rol de llamada al LLM

| Rol | Llamadas | Total ms | Promedio ms | p95 ms | % latencia |
| --- | --- | --- | --- | --- | --- |
| auditor | 77 | 932191 | 12106.4 | 40014.4 | 64% |
| redaccion | 91 | 280076 | 3077.8 | 12873.0 | 19% |
| planificador | 91 | 242550 | 2665.4 | 9805.5 | 17% |

Las llamadas al LLM concentran el **96%** de la latencia total medida en nodos.

## Puntos de falla

- Fallos por nodo: `ninguno`
- Corridas con reintentos de pasos: **0**
- Fallbacks (degradaciones) registrados: **0**
- Llamadas al LLM degradadas a modo demo: **9**
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

`{'no_cumple': 34, 'alerta': 116, 'cumple': 9}`

Veredictos por tipo de tarea:

`{'auditoria': {'alerta': 11, 'no_cumple': 5, '(sin veredicto)': 2}, 'consulta_normativa': {'(sin veredicto)': 6}}`
