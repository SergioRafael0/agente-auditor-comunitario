# PRESENTACION.md — Defensa Evaluación Parcial N°1

**Formato**: 10 minutos de exposición + 10 minutos de preguntas.
**Audiencia**: profesor Francisco Macaya + posiblemente ayudantes.
**Apoyo visual**: este documento es el esqueleto. El contenido final se traslada a PPT/Canva en la semana 5.

> **Estado**: boceto. El contenido se cierra en semana 5 una vez el código esté probado.

---

## Slide 1 — Portada (10s)

**Contenido**:
- Título: "Agente Auditor Comunitario (AAC)"
- Subtítulo: "Auditor automático de cumplimiento normativo para publicaciones en comunidades"
- Asignatura: ISY0101 Ingeniería de Soluciones con IA
- Estudiante: Sergio de la Cruz
- Fecha: [semana 6 del semestre]

**Mensaje clave**: dejar claro el nombre y de qué se trata en 10 segundos.

---

## Slide 2 — El problema (60s)

**Título**: "Comunidades publican, pero ¿cumplen la ley?"

**Contenido**:
- Contexto: administradores de comunidades en Chile publican necesidades de mantención.
- Realidad: muchas publicaciones piden trabajos que requieren **técnicos certificados** (electricistas SEC, mantenedores de ascensores, etc.).
- Riesgo: si un proveedor no certificado hace el trabajo, la comunidad queda expuesta legalmente y la aseguradora puede no cubrir siniestros.
- Dato concreto: Ley 21.442 + normativa SEC establecen requisitos obligatorios por categoría de trabajo.

**Mensaje clave**: hay un problema real, no inventado. Tiene consecuencias legales y económicas.

---

## Slide 3 — La solución: AAC (60s)

**Título**: "Un agente que audita publicaciones antes de que lleguen a proveedores"

**Contenido**:
- Input: texto de una publicación (categoría, descripción, urgencia).
- Proceso:
  1. Recupera normativa relevante de una base vectorial (RAG).
  2. Un LLM analiza y emite alertas con citas exactas.
- Output: estado (`cumple | alerta | no_cumple`) + alertas concretas + recomendaciones.
- Forma de uso: el admin publica → antes de salir al feed, AAC la audita → si hay alerta, se sugiere corregir.

**Mensaje clave**: complementamos la plataforma, no la reemplazamos. Un paso nuevo en el flujo.

---

## Slide 4 — Caso de uso demostrable (60s)

**Título**: "Ejemplo real"

**Contenido**:
- Publicación de ejemplo:
  > *"Necesito arreglar el portón eléctrico del edificio. Es urgente, falla a veces."*
- Categoría: electricidad
- Resultado del agente:
  - Estado: **alerta**
  - Alerta 1: Trabajos en instalaciones eléctricas de uso común deben ser ejecutados por instalador eléctrico autorizado por la SEC (Norma 4/2003).
  - Alerta 2: La publicación debería requerir al proveedor acreditar su certificación SEC vigente.
  - Recomendación: agregar al campo "observaciones" el requisito de presentar certificado SEC.

**Mensaje clave**: pasa de "publicación vaga" a "publicación que se defiende legalmente".

---

## Slide 5 — Arquitectura (90s)

**Título**: "Cómo está construido"

**Diagrama ASCII o imagen** (usar el de `plan.md` §3):

```
[Normativa] → [Indexer] → [Chroma]
                              ↓
[Claude Desktop] → [MCP Server] → [RAG retrieve] → [Groq LLM] → [JSON]
                              ↓
                         [Log JSONL]
```

**Componentes clave** (uno por uno, rápido):
- **Indexer** (offline): PDF/txt → chunks → embeddings → Chroma persistente.
- **MCP server** (online): expone la tool `revisar_publicacion` vía protocolo estándar.
- **Retriever**: búsqueda vectorial con filtro por categoría.
- **LLM (Groq)**: analiza la publicación contra los chunks recuperados, devuelve JSON.
- **Logging**: cada interacción queda registrada para auditoría y mejora continua.

**Mensaje clave**: arquitectura simple, módulos claros, decisiones justificadas (referenciar `plan.md`).

---

## Slide 6 — Decisiones técnicas clave (90s)

**Título**: "Por qué Groq, sentence-transformers, Chroma y MCP"

**Tabla rápida**:

| Componente | Elección | Razón |
|---|---|---|
| LLM | Groq (llama-3.3-70b) | Gratis, rápido, español nativo |
| Embeddings | sentence-transformers MiniLM multilingüe | Local, gratis, suficiente |
| Vector DB | Chroma persistente | Sin servidor, escala de sobra |
| Protocolo | MCP streamable-http | Estándar, mismo patrón que el ejemplo del curso |

**Mensaje clave**: cada elección tiene justificación técnica, no es "lo primero que encontré". Aterrizar en `plan.md` §4 para detalle.

---

## Slide 7 — Pipeline RAG en detalle (60s)

**Título**: "Cómo recupera la información"

**Contenido**:
1. Indexación (una vez): Ley 21.442 + 2 normativas SEC → ~3000-5000 chunks → Chroma.
2. Retrieval (por consulta):
   - Embedding de la publicación con el mismo modelo.
   - Búsqueda por coseno en Chroma.
   - **Filtro por categoría** (electricidad, ascensor, gas, etc.) para acotar resultados.
   - Top-k = 5 chunks más relevantes.
3. Generación: esos 5 chunks van al prompt del LLM con instrucciones estructuradas → respuesta JSON.

**Mensaje clave**: híbrido entre lo semántico (embedding) y lo simbólico (filtro por categoría). Cita exacta porque los chunks preservan metadata del artículo.

---

## Slide 8 — Prompts del agente (60s)

**Título**: "Cómo le hablamos al modelo"

**Mostrar (resumido)**:
- System prompt: rol claro, reglas (no inventar normativa, citar fuente), formato JSON estricto.
- Few-shot: 1-2 ejemplos de publicación bien auditada.
- Schema de salida: estado, alertas (cada una con `fuente`, `articulo`, `mensaje`, `recomendacion`).

**Mensaje clave**: el prompt no es improvisado, está estructurado y justificado (responde a IE2). Detalle en `informe.pdf` §3.

---

## Slide 9 — Pruebas y resultados (60s)

**Título**: "5 casos de prueba, todos relevantes"

**Contenido** (llenar en semana 5 con resultados reales):
- Caso 1: electricidad → alerta SEC correcta ✓
- Caso 2: ascensor → alerta SEC correcta ✓
- Caso 3: mantención general → cumple ✓
- Caso 4: trabajo sin categoría clara → no_cumple + recomendación ✓
- Caso 5: publicación bien hecha → cumple ✓

**Métricas**:
- Latencia promedio: ~[medir real] segundos.
- Cobertura del corpus: [medir % de categorías cubiertas].
- Juicio offline del LLM-as-judge: [medir % coherencia].

**Mensaje clave**: funciona, está medido, no es anécdota.

---

## Slide 10 — Trabajo futuro y cierre (60s)

**Título**: "Esto es solo el comienzo"

**Contenido**:
- **Lo que viene en el semestre**:
  - Semana X: agregar tool `revisar_cotizacion` (segunda evaluación).
  - Semana Y: agregar tool `buscar_normativa` libre.
  - Semana Z: integración con app "Proveedores & Comunidades" real + deploy en Cloud Run.
- **Aprendizajes del proceso**:
  - RAG bien armado > fine-tuning caro.
  - MCP simplifica la interfaz cliente sin reinventar la rueda.
  - La observabilidad desde el día uno ahorra dolores después.

**Mensaje clave**: el proyecto crece conmigo durante el semestre, no es un artefacto aislado.

---

## Slide de respaldo — Stack alternativo (solo si preguntan)

Si alguien pregunta "¿por qué no usaron OpenAI / Claude / X?":
- Costo: Groq es gratis hasta topes generosos.
- Privacidad: embeddings locales, datos no salen del entorno.
- Suficiencia: para este corpus y alcance, no necesitamos un modelo más grande.

---

## Notas para la defensa (10 min preguntas)

**Posibles preguntas y respuestas准备好:**

1. **"¿Por qué RAG y no fine-tuning?"** → Porque el corpus legal cambia y el costo de reentrenar es prohibitivo. RAG se actualiza re-indexando.
2. **"¿Cómo evitan alucinaciones de normativa?"** → Prompt estricto con "no inventar", few-shot con citas exactas, metadata de fuente en cada chunk, LLM-as-judge offline.
3. **"¿Y si Groq se cae?"** → Fallback a `llama-3.1-8b-instant` o cambio a otro proveedor (la interfaz es la misma, solo cambia `llm.py`).
4. **"¿Cómo escala?"** → Chroma escala a cientos de miles de chunks. Si pasa de eso, migramos a Qdrant/Weaviate sin tocar el resto.
5. **"¿Por qué solo 1 tool en MVP?"** → Alcance acotado a 5 semanas, evaluación parcial mide calidad sobre cantidad. Las otras tools entran en evaluaciones siguientes.
6. **"¿Cómo conectan a la app real?"** → No hay app todavía. El caso es un spec. AAC se diseñó para integrarse cuando exista vía la misma tool MCP.

---

## Cronograma de cierre del documento

| Sesión | Acción |
|---|---|
| Semana 2 | Crear este archivo con slides 1-10 vacíos (esqueletos arriba). |
| Semana 3 | Llenar slide 4 con caso real probado en Claude Desktop. |
| Semana 4 | Llenar slide 9 con métricas reales. |
| Semana 5 | Cerrar slides 6, 7, 8 con datos del informe. Pasar a PPT/Canva. |
| Semana 6 | Defensa. |
