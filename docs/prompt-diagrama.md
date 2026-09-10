# Prompt para generar el diagrama de arquitectura del AAC

## Prompt principal (ingles, recomendado para la mayoria de IAs de imagen)

```
Architecture diagram, clean technical schematic style, white background, no decorative elements, no people, no 3D, flat design, modern minimalist style inspired by AWS architecture diagrams and Excalidraw. The diagram shows a flow of 4 main layers from top to bottom:

LAYER 1 (top): A single rounded rectangle labeled "MCP Client: Claude Desktop or Claude Code" with an icon representing a chat interface. A note "Sends JSON-RPC + Bearer token" on the right with an arrow pointing down.

LAYER 2: A rounded rectangle labeled "MCP Server" containing two sub-boxes side by side: left box labeled "Auth Middleware (Bearer Token)" and right box labeled "FastMCP Framework". An arrow points from Layer 1 to this layer.

LAYER 3 (most important, wider): A large rounded rectangle labeled "AI Agent (src/agent/auditor.py)" containing 5 numbered steps in a vertical list:
  1. "Retrieve top-5 relevant chunks from RAG"
  2. "Build system prompt + few-shots + user prompt with context"
  3. "Call Groq LLM API"
  4. "Parse JSON response with Pydantic"
  5. "Log interaction to data/interacciones.jsonl"

LAYER 4 (bottom): Two rounded rectangles side by side. Left: "Retriever (Chroma + Sentence-Transformers) -> data/chroma/ with 312 legal chunks (Ley 21.442 + 5 RIC SEC + 1 Oficio Circular)". Right: "LLM API: openai/gpt-oss-120b via Groq Cloud". An arrow from Layer 3 points to each.

Connecting arrows in dark blue, labels in small sans-serif text. Use a color palette of: navy blue (#1a3a5c) for main components, light blue (#e8eef5) for backgrounds, orange (#ff7f50) for the LLM, green (#4caf50) for the database, gray (#666) for text. Width 1200px, height 800px, landscape orientation, no watermark, no logo, no border, transparent background outside the diagram.
```

## Prompt alternativo mas corto (si la IA tiene limite de tokens)

```
Clean technical architecture diagram, flat design, white background, schematic style similar to AWS diagrams. Four horizontal layers from top to bottom:

Top: "MCP Client (Claude Desktop)" icon
Second: "MCP Server" with two sub-boxes: "Auth Middleware" and "FastMCP"
Third (widest): "AI Agent" with 5 numbered steps: retrieve chunks, build prompt, call LLM, parse JSON, log
Bottom: Two side-by-side boxes: "Chroma Vector DB (312 chunks of Chilean legal norms)" and "Groq LLM API (gpt-oss-120b)"

Arrows showing data flow. Color palette: navy blue, light blue, orange (LLM), green (DB). 1200x800px landscape, no decorations, no people, minimalist.
```

## Prompt para Canva / Google Slides (si prefieres armarlo a mano)

Si no quieres usar una IA de imagen, puedes armarlo en Canva o PowerPoint con esta estructura:

```
1. Abre Canva, elige "Presentacion" o "Diseno" 1200x800px
2. Background blanco
3. Usa la herramienta "Cuadro de texto" + "Formas" (rectangulos redondeados)
4. Crea 4 capas horizontales como muestra el ASCII
5. Colores sugeridos:
   - Componentes principales: relleno #1a3a5c, texto blanco
   - Fondo de capa: #e8eef5
   - LLM: #ff7f50 (naranja) para destacar
   - Base de datos: #4caf50 (verde)
   - Texto: #333333
   - Flechas: linea solida #1a3a5c, grosor 2pt
6. Tipografia: sans-serif (Inter, Roboto o Arial), tamano:
   - Titulos de capa: 18pt bold
   - Sub-componentes: 14pt medium
   - Texto dentro de componentes: 11pt regular
   - Etiquetas de flechas: 9pt italic
7. Exporta como PNG a 300dpi para el informe
```

## Donde usar el diagrama

- **Informe**: reemplazar el ASCII art de la seccion 4.1 (actualmente en `informe.md` lineas del diagrama de arquitectura)
- **Slides**: slide 5 (Arquitectura) en `PRESENTACION.md`
- **README**: si quieres agregarlo en la documentacion

## Archivos del proyecto

- `informe.md` (markdown del informe, contiene el ASCII actual)
- `PRESENTACION.md` (slides en markdown)
- `plan.md` seccion 3 (diagrama del pipeline RAG, otro diagrama diferente que tambien puedes convertir a imagen)

## Que NO incluir en el prompt

- El logo de Duoc UC (no es publico)
- Tu nombre personal (no va en el diagrama)
- Colores exactos que no son necesarios (las IAs los interpretan bien)
- Texto que no quepa (las IAs distorsionan si el texto es muy largo)
