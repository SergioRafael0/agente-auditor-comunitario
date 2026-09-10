# AGENTS.md — Agente Auditor Comunitario (AAC)

Guía de trabajo para el proyecto. Léela antes de cada sesión.
El detalle de diseño técnico está en `plan.md`. Los slides están en `PRESENTACION.md`.

---

## 1. Identidad del proyecto

- **Nombre**: Agente Auditor Comunitario (AAC)
- **Tipo**: MCP server con RAG sobre normativa chilena de comunidades
- **Caso base**: "Proveedores & Comunidades" (documento del profesor, `pauta evaluación/Caso para el agente.md`)
- **Tagline**: "Auditor automático de cumplimiento normativo para publicaciones en comunidades"
- **Curso**: ISY0101 Ingeniería de Soluciones con IA — Duoc UC, 2026-2
- **Docente**: Francisco Macaya

---

## 2. Stack técnico (decidido, no cambiar sin discutir)

| Pieza | Elección | Por qué |
|---|---|---|
| Lenguaje | Python 3.11+ | Estándar en el curso |
| LLM | Groq (`llama-3.3-70b-versatile`) | Gratis, rápido, español nativo, ya usado en lab 1.1 |
| Embeddings | `sentence-transformers` + `paraphrase-multilingual-MiniLM-L12-v2` | Local, gratis, multilingüe, liviano (~120MB) |
| Vector DB | Chroma (modo persistente local) | Sin servidor, archivo en disco |
| Chunking | Por artículo/sección de la ley + overlap 100 tokens | Simple, efectivo para texto legal |
| Protocolo | MCP SDK Python + transporte `streamable-http` | Mismo patrón que `mcp-asistente-curso_ejemplo` |
| Tests | pytest | Mismo patrón que el ejemplo |
| Auth | Bearer token simple | Reutilizable del ejemplo |
| Observabilidad | Log a `data/interacciones.jsonl` + LLM-as-judge offline | Mismo patrón, sin Supabase en MVP |

---

## 3. Convenciones de código

- **Sin emojis** en archivos de código ni en mensajes de commit. Solo en este AGENTS.md y en slides.
- **Sin comentarios innecesarios** en código (el código debe ser autoexplicativo).
- **Type hints** en todas las funciones nuevas.
- **Funciones puras** cuando se pueda. Separar I/O de lógica.
- **Estructura modular** según `src/` (cada módulo hace una sola cosa).
- **Nombres en español** para dominio (publicacion, cotizacion, alerta) — el código del curso usa este idioma.
- **Nombres en inglés** para patrones genéricos (retriever, embedder, loader).
- **Variables de entorno** siempre vía `python-dotenv`, nunca hardcoded.
- **Errores**: preferir excepciones específicas (`ValueError`, `FileNotFoundError`) sobre `Exception` genérico.
- **Logging**: usar `logging` estándar, no `print()`.

---

## 4. Comandos clave

```bash
# Activar entorno virtual (SIEMPRE primero en cada sesión)
cd agente-auditor-comunitario
source .venv/Scripts/activate        # Git Bash en Windows
# o: .venv\Scripts\activate         # PowerShell/CMD en Windows

# Instalar dependencias
pip install -r requirements.txt

# Indexar la normativa (solo la primera vez o si cambia la fuente)
python -m src.indexer.build_index

# Probar el agente en CLI (sin MCP, para iterar rápido)
python -m src.agent.auditor --texto "Necesito arreglar el portón eléctrico del edificio"

# Levantar el MCP server (en otra terminal)
python -m src.mcp_server.server

# Correr todos los tests
pytest

# Correr tests con verbosidad
pytest -v

# Ver el log de interacciones
cat data/interacciones.jsonl | tail -20
```

---

## 5. Plan por semanas (5 semanas, semana 7 = entrega)

### Semana 1 — Setup + corpus normativo
- [x] Crear estructura de carpetas
- [x] Definir stack y dependencias
- [ ] Sacar GROQ_API_KEY (guía en `docs/setup-groq.md`)
- [ ] Descargar/corpus de Ley 21.442 (texto plano) → `data/normativa/`
- [ ] Descargar 1-2 normativas SEC clave (ascensores, electricidad) → `data/normativa/`
- [ ] `src/indexer/ingest.py` carga PDFs/txt → texto limpio
- [ ] `src/indexer/chunk.py` divide en chunks con overlap
- [ ] `src/indexer/embed.py` genera embeddings con sentence-transformers
- [ ] `src/indexer/build_index.py` orquesta todo → Chroma persistente
- [ ] Validar con búsqueda manual: "ascensor" debe traer normativa SEC

### Semana 2 — RAG básico + boceto de slides
- [ ] `src/retriever/search.py` busca en Chroma con filtros por categoría
- [ ] `src/agent/llm.py` cliente Groq (wrapper simple)
- [ ] `src/agent/prompts.py` system prompt del auditor
- [ ] `src/agent/auditor.py` orquesta retrieve + LLM → respuesta estructurada
- [ ] Probar con 5-10 publicaciones reales del caso
- [ ] **Boceto de `PRESENTACION.md`** con esqueleto de slides (10 slides)

### Semana 3 — MCP server + conexión a Claude Desktop
- [ ] `src/mcp_server/auth.py` bearer token + rate limit por IP
- [ ] `src/mcp_server/server.py` declara tool `revisar_publicacion`
- [ ] Probar conectando a Claude Desktop (instrucciones en `README.md`)
- [ ] Validar latencia (<2s por consulta)
- [ ] Iterar prompts con casos reales hasta que las alertas sean útiles

### Semana 4 — Tests + observabilidad
- [ ] `tests/test_indexer.py` ingest + chunk + embed + búsqueda básica
- [ ] `tests/test_retriever.py` búsqueda con filtros, sin resultados, etc.
- [ ] `tests/test_auditor.py` end-to-end con 5+ casos de prueba
- [ ] `tests/test_mcp_server.py` (mock LLM, validar schema)
- [ ] Logging a `data/interacciones.jsonl` desde el agente
- [ ] Script `src/agent/judge.py` evalúa respuestas históricas con LLM-as-judge

### Semana 5 — Informe + slides finales + dry-run
- [ ] `informe.pdf` (máx 5 páginas) con secciones IE1-IE5
- [ ] Slides finales en `PRESENTACION.md` (cerrar contenido, dejar formato para Canva/PPT)
- [ ] Dry-run de la presentación (cronometrar 10 min)
- [ ] README ejecutable para evaluadores
- [ ] Subir todo a GitHub

### Semana 6 — Presentación
- [ ] Defensa 10 min exposición + 10 min preguntas

### Semana 7 — Entrega final
- [ ] Enviar por AVA + correo del docente

---

## 6. Estado actual

**Última actualización**: sesión 4 — prompt refinado, documentado, 8/8 aciertos.

**Hecho**:
- Estructura de carpetas creada
- Stack definido y dependencias instaladas (22/22 tests pasando)
- Documentos base: `AGENTS.md`, `plan.md`, `PRESENTACION.md`, `README.md`, `.env.example`
- Esqueleto de código en `src/` (indexer, retriever, agent, mcp_server)
- Tests pytest que mockean LLM/Chroma para no gastar tokens en CI
- 18 bugs reales encontrados y arreglados (ver §9)
- **Corpus mixto indexado**: 312 chunks (Ley 21.442 + 5 RIC SEC + 1 Oficio Circular)
- **Agente funcionando end-to-end** con Groq + RAG, citando correctamente "SEC Norma RIC N°XX" y "Ley 21.442, Artículo N"
- **Batería de eval de prompts** (`scripts/eval_prompts.py`) con 8 casos representativos
- **Prompt v2 final** con 2 few-shots correctamente inyectados, documentado en `docs/prompts-decisiones.md` → cubre IE2

**Pendiente inmediato** (siguiente en el plan recortado):
1. Generar 10+ interacciones reales + correr `judge.py` → IE6
2. Conectar el MCP server a Claude Desktop → demo en vivo para defensa
3. Informe de 5 páginas → IE5
4. Slides en markdown (no PPT) → IE9
5. Diagrama (al final según usuario) → IE4, IE7

---

## 7. Criterios de decisión

Cuando tengas que elegir entre opciones y no esté en este documento, aplicar:

1. **¿El ejemplo del profesor (`mcp-asistente-curso_ejemplo/`) lo hace así?** → usar igual.
2. **¿La pauta de evaluación lo evalúa explícitamente?** → optimizar para ese IE.
3. **¿Es lo más simple que funciona?** → preferirlo.
4. **¿Cuesta dinero?** → no, salvo que no haya alternativa gratuita razonable.
5. **¿Lo vamos a poder defender en 10 minutos?** → si requiere explicación de más de 2 min, simplificar.

Si dos opciones empatan, preguntar al usuario antes de avanzar.

---

## 8. Modo de trabajo

- Una fase a la vez. No saltar a la siguiente hasta que la anterior esté validada con tests.
- Después de cada sesión: actualizar sección "Estado actual" de este archivo.
- Si algo se rompe: dejarlo documentado en sección "Bugs encontrados" abajo, no borrar.
- Pedir confirmación antes de tomar decisiones que cambien el alcance.

---

## 9. Bugs encontrados y decisiones tomadas en el camino

> Esta sección crece durante el proyecto. Documentar aquí todo problema real y cómo se resolvió, para no repetirlo.

### Sesión 1 — setup + tests iniciales

- **Windows Long Path support**: `pip install` falló al instalar `torch` por nombres de archivo demasiado largos en la ruta del proyecto (`S:\1- Sergio\...\agente-auditor-comunitario\.venv\Lib\site-packages\torch\include\...`). **Resuelto** creando el venv en `C:\venvs\aac` y enlazándolo con `mklink /J .venv C:\venvs\aac`. El proyecto sigue funcionando desde la ruta original.
- **Regex sin MULTILINE**: el patrón de chunking (`PATRON_SECCION`) no usaba `re.MULTILINE`, por lo que `^` solo matcheaba al inicio del string completo, no al inicio de cada línea → artículos no se detectaban. **Resuelto** agregando `re.MULTILINE`.
- **Chunking fusionaba secciones cortas**: cuando dos artículos cabían juntos en `max_tokens`, mi código los fusionaba en un solo chunk → perdíamos la cita por artículo. **Resuelto** cambiando la lógica para que el patrón de sección sea una "fractura dura": cada artículo es su propio chunk aunque quepan varios juntos.
- **`_partir_largo` no manejaba texto sin saltos de línea**: si una sección era un solo string largo, `split("\n\n")` devolvía un solo elemento y nunca partía. **Resuelto** agregando `_partir_en_oraciones` como fallback (split por `. `).
- **SDK `mcp` v2.x cambió la API**: `streamable_http_app` ya no existe como función; ahora es método de `FastMCP` y la API lowlevel usa `StreamableHTTPServerTransport` directo. **Resuelto** fijando `mcp>=1.2.0,<2.0` en `requirements.txt` (versión 1.x que es la del ejemplo del curso y la que tiene `streamable_http_app`). Bonus: usé `FastMCP` que es la forma idiomática moderna con menos boilerplate.
- **`call_tool` API de FastMCP devuelve tupla**: en la versión instalada, `call_tool` devuelve `(lista_contenido, dict_resultado)`, no solo la lista. **Resuelto** ajustando los tests para aceptar ambos formatos.
- **`AuthMiddleware` no expuesto en `server.py`**: el test importaba `server.AuthMiddleware` pero solo estaba disponible vía `build_app()`. **Resuelto** moviendo el import al nivel del módulo.

### Sesión 2 — corpus real + RAG funcionando end-to-end

- **PDF como fuente**: la Ley 21.442 estaba en PDF (70 páginas). `pymupdf4llm` lo procesó sin problema (ley digital, no escaneada). Generó 209 chunks.
- **Caracteres mal codificados**: algunos caracteres del PDF venían como secuencias latin-1 leídas como UTF-8 (ej. `Ã¡` en vez de `á`). **Resuelto** agregando `_normalizar_unicode()` en `ingest.py` que reemplaza los casos comunes.
- **Tipo siempre "norma_tecnica"**: la lógica original asignaba tipo según el nombre del archivo, pero solo para `.txt`, no para PDFs. **Resuelto** extrayendo `_inferir_tipo()` como función separada que se aplica a ambos formatos.
- **Modelo Groq deprecado**: `llama-3.3-70b-versatile` (elegido originalmente) devolvía 404. Groq ya no lo lista en `models.list()` (aunque la página de docs dice que existe). **Resuelto** cambiando a `openai/gpt-oss-120b` (120B params, igual o mejor capacidad, disponible y gratis en tier dev).
- **Filtro `$contains` de Chroma no funciona con metadata strings**: `where={"categoria_publicacion": {"$contains": "ascensor"}}` devolvía 0 resultados aunque había 12 chunks con esa categoría. Problema conocido de Chroma 1.5.x. **Resuelto** haciendo fallback automático a búsqueda sin filtro cuando el filtrado devuelve 0 resultados.
- **Alucinación de normativa SEC**: el modelo citaba "SEC Norma 4/2005, Artículo 3" que no existe en el corpus indexado. **Resuelto parcialmente** con el cambio de modelo (gpt-oss-120b es más preciso) y el RAG funcionando bien — ahora cita correctamente "Ley 21.442, Párrafo 3° (instalaciones de ascensores)" que SÍ existe. Para MVP es suficiente; en próximas sesiones podemos agregar las normas SEC reales al corpus.

### Sesión 4 — refinamiento y documentación del prompt (IE2)

- **Few-shots definidos pero no inyectados**: `FEW_SHOT_EJEMPLO_1` existía en `prompts.py` pero el código de `auditor.py` no lo agregaba al system prompt. Bug heredado desde v1. **Resuelto** creando `few_shots_texto()` que arma el bloque markdown, y modificando `auditor.py` para concatenarlo al system prompt.
- **Sesgo del modelo hacia `no_cumple`**: la regla 1 de v1 decía "si no estás seguro, prefiere decir no_cumple", lo cual llevó al modelo a abusar de ese estado. **Resuelto** eliminando esa regla y agregando "alerta ES EL ESTADO MÁS COMÚN" en v2.
- **Confusión alerta vs no_cumple**: la definición original de `no_cumple` mezclaba "incumple" con "es vaga". **Resuelto** restringiendo `no_cumple` a solo DOS casos (ilegal explícita o vacía absoluta) y agregando few-shot de "necesito ayuda" como ejemplo.
- **Batería de evaluación de prompts**: script `scripts/eval_prompts.py` con 8 casos representativos, scoring automático, guardado en `data/eval/v1/` y `data/eval/v2/`. **Resuelto** permitiendo medir el impacto de cada cambio de prompt con evidencia numérica.
- **Documentación IE2**: `docs/prompts-decisiones.md` con análisis completo v1→v2, problemas detectados, cambios justificados, tabla comparativa, lecciones aprendidas y mejoras futuras.

---

## 10. Aprendizaje

Usuario es **principiante en casi todo** (Python básico, Git básico, primera vez con LLMs/RAG/MCP). Por lo tanto:

- Explicar el "por qué" brevemente cuando aparezca un concepto nuevo (1-2 frases, no clases teóricas).
- No asumir que algo se entiende: si un comando tiene una sintaxis no obvia, decir qué hace.
- Si algo se traba, detener y explicar antes de continuar.
- Documentar cada herramienta nueva en `docs/` cuando se introduzca por primera vez.
