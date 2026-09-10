# Guia de aprendizaje — Agente Auditor Comunitario (AAC)

Esta guia esta dividida en dos partes. La primera es una guia operativa, pensada para leer rapido y consultar cuando necesites usar la app. La segunda es una explicacion conversacional del codigo, pensada para escuchar como si fuera un audio largo, de principio a fin, y entender de verdad como funciona todo por dentro.

Lee la primera parte ahora, rapido, para familiarizarte. La segunda parte la puedes escuchar en cualquier momento, idealmente un par de veces, hasta que te sientas comodo explicandola con tus propias palabras.

---

# PARTE 1 — Como usar la app

Esta parte es de consulta. Cuando necesites correr algo, abrir algo, o conectar la app a un cliente, vuelves aca.

## 1. Formas de usar la app

La app se puede usar de cuatro formas distintas, de mayor a menor integracion con un LLM.

### A. Conectada a Claude Desktop (la forma mas comoda para la defensa)

Claude Desktop es la aplicacion de escritorio de Anthropic. Cuando la conectas al MCP server del AAC, el propio Claude puede decidir cuando invocar la herramienta `revisar_publicacion` mientras conversan. Tu solo le pides algo en lenguaje natural y el lo hace solo.

Para configurarla, edita el archivo de configuracion de Claude Desktop. En Windows esta en `C:\Users\<tu-usuario>\AppData\Roaming\Claude\claude_desktop_config.json`. Si no existe, crealo. Pega adentro el contenido del archivo `docs/claude_desktop_config.json` que esta en este proyecto, y reemplaza la palabra `CAMBIA_ESTO_POR_TU_MCP_AUTH_TOKEN` por el valor real de tu archivo `.env` en la variable `MCP_AUTH_TOKEN`.

Luego, en otra terminal, levanta el server con el comando `python -m src.mcp_server.server` desde la carpeta del proyecto con el entorno virtual activado. Reinicia Claude Desktop para que detecte el nuevo server. Cuando le preguntes a Claude algo como "audita esta publicacion de mantención de ascensor", el deberia invocar la herramienta automaticamente y devolverte el analisis con las alertas y la normativa aplicable.

### B. Conectada a Claude Code (la forma que probablemente uso el profesor)

Claude Code es la version de Claude para terminal, la que se instala con `npm install -g @anthropic-ai/claude-code` y se invoca escribiendo `claude` en una terminal. Tiene soporte nativo para MCP servers.

Para conectar el AAC a Claude Code, ejecuta una sola vez el comando `claude mcp add --transport http aac http://localhost:8000/mcp --header "Authorization: Bearer TU_TOKEN"`, reemplazando TU_TOKEN por el valor de tu `MCP_AUTH_TOKEN`. Despues de eso, cada vez que inicies Claude Code en una terminal, el va a tener disponible la herramienta `revisar_publicacion` del AAC.

La gracia de Claude Code es que puedes hacer cosas como pedirle "agregale cobertura para normativa de gas al agente", y el va a leer el codigo, modificar el archivo correspondiente, y correr los tests, todo desde la terminal.

### C. Desde la terminal directamente (sin LLM cliente)

Esta es la forma mas rapida para probar el agente sin tener que abrir un cliente MCP. Simplemente ejecutas el comando `python -m src.agent.auditor --texto "aca va la publicacion" --categoria electricidad` desde la carpeta del proyecto con el entorno activado. El flag `--texto` recibe la descripcion de la publicacion, y `--categoria` recibe una de las categorias validas que son electricidad, ascensor, gas, agua, o general.

El output es un JSON formateado con el estado, las alertas, las recomendaciones, los chunks que se recuperaron del RAG, y la latencia. Es util para debugging o para iterar rapido sobre el corpus normativo.

### D. Desde un Jupyter notebook (lo que probablemente mostro el profesor)

Jupyter es ideal para experimentar. Crea un notebook nuevo, asegurate de que el kernel apunte al entorno virtual del proyecto, y en la primera celda importa el agente con `from src.agent.auditor import auditar_publicacion`. Despues en otra celda llamas `resultado = auditar_publicacion("Necesito arreglar el ascensor", "ascensor")` y el resultado es un diccionario Python normal al que le puedes hacer `resultado["estado"]`, `resultado["alertas"]`, y todo lo que quieras.

La ventaja del notebook es que puedes ver los chunks recuperados uno por uno, modificar el prompt en vivo, probar variaciones de la publicacion, y dejar documentado todo el proceso para tu defensa.

### E. Desde VS Code con la extension de Jupyter

Si usas Visual Studio Code, instala la extension oficial de Jupyter. Luego abre un archivo con extension `.ipynb` y todo funciona igual que en Jupyter tradicional, pero con la comodidad de tener el codigo del proyecto al lado, autocomplete, y un solo lugar para trabajar.

## 2. Activar el entorno virtual (siempre primero)

Todos los comandos de esta guia asumen que el entorno virtual esta activado. Para activarlo, abre una terminal en la carpeta del proyecto y ejecuta `source .venv/Scripts/activate` si usas Git Bash, o `.venv\Scripts\activate` si usas PowerShell o CMD. Vas a ver que el prompt de la terminal empieza con `(.venv)`. A partir de ahi todo lo que instales o ejecutes queda dentro del entorno aislado del proyecto.

## 3. Comandos utiles del dia a dia

El comando mas importante es `python -m src.indexer.build_index` que reindexa la normativa. Solo necesitas correrlo la primera vez, o cuando agregues documentos nuevos a la carpeta `data/normativa`. Si querés regenerar todo desde cero, agregale el flag `--sobreescribir`.

Para correr la bateria de evaluacion de prompts y ver que tan bien esta funcionando el agente, ejecuta `python -m scripts.eval_prompts --version v1` o `--version v2`. La version v2 es la final, asi que esa es la que querés usar como referencia. Los resultados se guardan en `data/eval/v2/` con un archivo JSON por cada caso de prueba.

Para correr el LLM-as-judge sobre todas las interacciones acumuladas, ejecuta `python -m scripts.evaluar_con_judge`. Esto consume tokens de Groq, asi que no lo corras en bucle. Los resultados agregados quedan en `data/eval/judge_results.json`.

Para correr los tests del proyecto, ejecuta `pytest`. Los tests mockean el LLM asi que son rapidos y gratis, y te dan confianza de que el codigo no se rompio despues de cualquier cambio.

Para regenerar el PDF del informe a partir del markdown, ejecuta `python -m scripts.md_a_pdf`. Esto lee `informe.md` y produce `informe.pdf` con la misma cantidad de paginas que la ultima vez. Util si haces cambios pequenos al texto del informe.

## 4. Solucion de problemas comunes

Si el server no levanta, lo mas probable es que el puerto 8000 este ocupado por otra aplicacion. Podes cambiarlo editando la variable `MCP_PORT` en tu archivo `.env` y poniendo por ejemplo 8765. Despues actualiza tambien la URL en `docs/claude_desktop_config.json`.

Si el LLM devuelve respuestas raras o con alucinaciones, primero verifica que el corpus este indexado corriendo `python -m scripts.eval_prompts --version v2` y mirando los resultados. Si la relevancia de chunks baja de 0.4, probablemente necesitas reindexar la normativa con `python -m src.indexer.build_index --sobreescribir`.

Si los tests fallan despues de un cambio, lee el mensaje de error con atencion. Los tests mockean todo, asi que si fallan es porque tu codigo cambio la firma de una funcion o el nombre de un parametro. Revisa que el cambio sea compatible con los mocks.

Si Claude Desktop no detecta el server, asegurate de que el JSON de configuracion sea valido, que el token coincida exactamente con el del `.env`, y de que hayas reiniciado Claude Desktop completamente. En Claude Desktop, anda a Settings, Developer, y deberias ver el server `aac` listado. Si aparece con un error rojo, hace click para ver el detalle.

---

# PARTE 2 — Como funciona por dentro (para escuchar)

Esta segunda parte es una explicacion narrativa del codigo. Esta pensada para que la leas en voz alta, o la escuches con un lector de pantalla, y entiendas el sistema completo de corrido. Si algo no queda claro, vuelve a leer la parte uno, mira el archivo puntual, y despues retoma aca. No hay prisa.

Lo que vamos a recorrer es el viaje completo de una publicacion, desde que un administrador la escribe en la plataforma hasta que el agente le devuelve un analisis con alertas y citas a la normativa. Vamos a pasar por cada componente del sistema, vamos a entender por que se eligio cada tecnologia, y vamos a terminar con las preguntas que probablemente te haga el profesor y como pensarlas.

Empecemos por lo mas grande, la idea general. El Agente Auditor Comunitario es un sistema que combina un modelo de lenguaje grande con busqueda semantica sobre un corpus de normativa chilena. La razon de ser es simple, la plataforma Proveedores y Comunidades no audita si las publicaciones cumplen los requisitos legales, y eso expone a las comunidades a riesgos. El agente resuelve eso recibiendo una publicacion, buscando en la normativa los articulos que aplican, y emitiendo un veredicto estructurado con alertas concretas. Lo que hace distinto a este sistema de un simple chat con un LLM es que las respuestas siempre estan fundamentadas en la normativa real que esta en el corpus, no en lo que el modelo "cree" saber.

El viaje empieza cuando un usuario escribe una publicacion, digamos que dice "necesito arreglar el ascensor del edificio que hace ruidos raros al subir, es urgente". Esa publicacion se manda al sistema con dos datos, el texto y la categoria, que en este caso seria ascensor. A partir de ahi, el sistema hace tres cosas grandes en secuencia. Primero, convierte el texto en un vector numerico usando un modelo de embeddings. Segundo, busca en una base de datos vectorial los cinco fragmentos de normativa mas parecidos a ese vector. Tercero, le pasa al LLM el texto de la publicacion, los fragmentos recuperados, y un prompt muy estructurado, y el LLM devuelve un JSON con el veredicto. Despues el sistema valida ese JSON y lo registra en un log para trazabilidad.

Ahora vamos a detenernos en cada pieza. Lo primero que hay que entender es el corpus normativo, porque todo el sistema descansa sobre el. En la carpeta `data/normativa` hay siete archivos PDF, una copia de la Ley veintiuno punto cuatrocientos cuarenta y dos que es la ley de copropiedad inmobiliaria, cinco pliegos tecnicos normativos de la SEC que regulan instalaciones electricas, y un oficio circular que es la version vigente de las instrucciones para declarar instalaciones. Cuando arrancas el sistema por primera vez, un script lee estos PDFs, extrae el texto, lo divide en chunks, y los guarda en una base de datos vectorial. Ese script se llama `build_index.py` y esta en la carpeta `src/indexer/`. El nombre indexar viene de que estamos construyendo un indice de busqueda, igual que el indice de un libro pero para que una maquina pueda buscar por significado en vez de por palabra exacta.

La parte interesante es como se divide el texto en chunks. Si metieramos toda la ley como un solo bloque gigante, el LLM tendria que leer setenta paginas cada vez que alguien le pregunta algo, y ademas las respuestas serian vagas. La estrategia que usamos es dividir por seccion legal natural, es decir, cada articulo, cada parrafo, cada titulo o capitulo se convierte en un chunk separado. Ademas, si una seccion queda muy larga, la partimos por parrafos o por oraciones. El resultado es que cada chunk es un pedacito coherente de normativa, con su metadata de que archivo viene, que tipo de norma es, su numero, y si menciona categorias especificas como electricidad o ascensores. Eso nos da unos trescientos doce chunks en total, que es mucho menos que las paginas pero mucho mas consultable.

Los embeddings son la siguiente pieza clave. Un embedding es un vector numerico, una lista de trescientos ochenta y cuatro numeros en nuestro caso, que representa el significado de un texto de forma que textos parecidos tienen vectores parecidos. Para generarlos usamos un modelo que se llama paraphrase multilingual MiniLM, que es chico y multilingue y corre local en tu maquina sin necesitar internet. La gracia de correr embeddings local es que es barato y rapido, los puedes regenerar todas las veces que quieras sin pagar. La parte cualitativa del sistema, la que interpreta la publicacion y redacta la respuesta, si va a un LLM remoto porque ahi es donde necesitamos potencia.

La base de datos vectorial que usamos se llama Chroma, y la elegimos porque es la mas simple que cumple. Chroma te deja guardar vectores con metadata, y hacer busquedas por similitud, sin tener que levantar un servidor aparte, todo se guarda en archivos locales. Para nuestro caso, con trescientos doce chunks, Chroma funciona perfecto y no necesitamos nada mas complejo. Si el corpus creciera a millones de chunks, hariamos falta algo mas serio como Pinecone o Weaviate, pero para el MVP no se justifica.

El retriever es el componente que toma la consulta del usuario, la convierte en embedding, y busca los chunks mas parecidos en Chroma. Esta en `src/retriever/search.py`. La logica es simple, embedding de la consulta, busqueda por coseno en Chroma, devolver los top cinco. Lo interesante es que el retriever intenta filtrar por categoria primero, por ejemplo si la publicacion es de electricidad, busca chunks que tengan electricidad en su metadata. Pero hay un problema conocido con Chroma, el filtro por metadata con strings no siempre funciona, asi que implementamos un fallback automatico, si el filtro no devuelve nada, hace la busqueda sin filtro. Esa robustez es importante porque no queremos que una falla tecnica impida responder al usuario.

Ahora viene el corazon del sistema, el agente, que esta en `src/agent/auditor.py`. La funcion principal se llama `auditar_publicacion` y hace exactamente lo que describi al principio. Recibe el texto y la categoria, llama al retriever para obtener los chunks, arma el prompt completo con system, user, y los chunks como contexto, llama al LLM, parsea la respuesta con Pydantic, y devuelve el resultado junto con metadata de trazabilidad. Cada llamada queda registrada en un archivo JSONL que es como un log de auditoria, donde guardamos timestamp, los inputs, los chunks que se recuperaron, la respuesta, y la latencia. Eso es clave para dos cosas, poder debuggear despues que paso en una consulta especifica, y poder correr el LLM-as-judge offline sobre las consultas pasadas.

El prompt del agente merece una pausa porque es donde esta la inteligencia del sistema, no en la complejidad del codigo sino en que tan bien esta escrito. Esta en `src/agent/prompts.py`. El system prompt define el rol del agente como un auditor normativo experto en legislacion chilena, lista las reglas estrictas que debe seguir, define los tres estados posibles que puede devolver, y especifica el formato JSON exacto de salida. Los tres estados son cumple, alerta, y no cumple, y cada uno tiene un significado preciso. Cumple significa que la publicacion no requiere alertas regulatorias. Alerta significa que probablemente requiere cumplimiento normativo especifico, como un tecnico certificado o autorizacion de asamblea, y es el estado mas comun. No cumple es solo para dos casos extremos, una publicacion claramente ilegal, o una publicacion tan vaga que no se puede evaluar, como cuando alguien escribe "necesito ayuda" sin dar contexto. Esa tercera categoria es la que mas cuesta que el modelo entienda, y por eso usamos few-shots.

Los few-shots son ejemplos completos de input y output que le mostramos al modelo dentro del system prompt. Es como darle un examen con ejemplos resueltos para que entienda el nivel de detalle esperado. Tenemos dos, uno de un tablero electrico que da alerta con una cita al RIC numero dos, y uno de "necesito ayuda con unas cosas del edificio" que da no cumple con una recomendacion de pedir mas informacion. Sin esos ejemplos, el modelo tiende a abusar del estado no cumple por conservadurismo, y los ejemplos lo corrigen.

La eleccion del LLM es importante. Usamos el modelo openai-gpt-oss-ciento-veinte-b que corre en Groq, que es un servicio que ofrece inferencia muy rapida sobre modelos open source. Este modelo en particular tiene ciento veinte mil millones de parametros, es de los mas capaces disponibles gratis, y Groq lo sirve con latencia baja. Antes teniamos configurado un modelo de Llama que resulto estar deprecado, asi que tuvimos que cambiar. Si en el futuro Groq lo deprecia tambien, lo unico que hay que cambiar es el nombre del modelo en el archivo `.env`, el resto del codigo no se entera.

Toda la comunicacion entre el cliente, que puede ser Claude Desktop o cualquier otro, y el agente, pasa por un MCP server. MCP significa Model Context Protocol, y es un protocolo que invento Anthropic para que los modelos de lenguaje puedan llamar herramientas externas de forma estandar. La gracia es que cualquier cliente que entienda MCP puede usar nuestro server sin que nosotros escribamos una API custom. El server esta en `src/mcp_server/server.py` y expone una sola herramienta que se llama `revisar_publicacion`, con la descripcion, los parametros, y el esquema de validacion. Cuando Claude Desktop se conecta, le manda al modelo de Claude la descripcion de la herramienta, y Claude decide cuando usarla segun lo que el usuario le pregunte. Esa logica de decision la maneja el LLM del cliente, no nuestro server, asi que nuestro server solo se preocupa de ejecutar bien la herramienta cuando la llaman.

El server usa el SDK oficial de MCP, que se llama FastMCP, y se expone por HTTP usando el transporte streamable-http. Eso significa que el server es una aplicacion web normal, con Starlette como framework ASGI, y uvicorn como servidor. Le pusimos autenticacion con bearer token, asi cualquiera que conozca el token puede conectarse, pero nadie mas. Tambien pusimos un rate limit basico por IP, que no es perfecto pero al menos evita que un abuso tire el server. El endpoint exacto es `http://localhost:8000/mcp`, y ahi es donde los clientes mandan las peticiones JSON-RPC.

Para validar las respuestas del LLM usamos una libreria que se llama Pydantic, que es la misma que usa FastAPI. Definimos un modelo de datos que dice que la respuesta tiene que tener un campo estado que solo puede ser cumple, alerta, o no cumple, una lista de alertas donde cada una tiene fuente, articulo, mensaje, y recomendacion, y una lista de recomendaciones generales. Si el LLM devuelve algo que no encaja en ese esquema, Pydantic tira un error y nosotros devolvemos un no cumple con una alerta generica. Esa es la red de seguridad que evita que una respuesta malformada del modelo rompa el sistema.

El sistema completo tiene metricas que recogemos automaticamente. Cada llamada registra su latencia, y el log de interacciones se puede analizar despues. Para la defensa teniamos que demostrar que el sistema responde bien, y para eso escribimos dos scripts adicionales. El primero, `scripts/eval_prompts.py`, corre una bateria de ocho casos de prueba representativos, como ascensor, tablero electrico, pintura, gas, jardinero, publicacion vaga, y mide si el estado devuelto coincide con el esperado. El segundo, `scripts/evaluar_con_judge.py`, toma todas las respuestas acumuladas y las pasa por un LLM externo que actua como juez, evaluando tres cosas en escala de cero a uno, que tan relevantes son los chunks recuperados, que tan bien la respuesta se fundamenta en esos chunks, y que tan completa es la respuesta en terminos de normativa aplicable. Los resultados muestran que el sistema tiene una relevancia de chunks de alrededor de cero punto cinco, una fundamentacion de cero punto tres, y una completitud de cero punto cinco, lo que sugiere que el sistema es util pero tiene areas de mejora claras.

Ahora vamos a hablar de las preguntas que probablemente te haga el profesor en la defensa, y como pensarlas. La primera pregunta obvia es por que RAG y no fine-tuning. La respuesta es que la normativa cambia con frecuencia, y re-entrenar un modelo es prohibitivo en costo, mientras que re-indexar el corpus es trivial y toma minutos. La segunda pregunta es como evitamos que el modelo alucine normativa falsa. La respuesta tiene tres partes, el prompt es muy estricto con la instruccion de no inventar, los chunks que se le pasan al modelo llevan metadata con la fuente exacta, y tenemos un LLM-as-judge que detecta cuando la respuesta no se fundamenta en los chunks. La tercera pregunta probable es por que Groq y no OpenAI o Claude directamente. La respuesta es costo y dependencia, Groq nos da acceso a modelos de frontera gratis en tier de desarrollo, y si un dia cambia, solo hay que cambiar el nombre del modelo en el archivo de configuracion. La cuarta pregunta es por que Chroma y no Pinecone. La respuesta es que para trescientos doce chunks no se justifica una base de datos gestionada, y Chroma persistente local funciona perfecto, ademas la migracion a Pinecone seria solo cambiar el archivo de busqueda. La quinta pregunta es como escala el sistema. La respuesta honesta es que para este MVP escala hasta donde escala Chroma local, que es del orden de cientos de miles de chunks. Mas alla de eso, hariamos falta migrar Chroma a Qdrant o Pinecone, y el resto del codigo no se entera.

El mapa mental que te recomiendo tener claro para la defensa es asi. El usuario publica algo, eso va al MCP server, el MCP server valida el token y llama al agente, el agente hace retrieve de los chunks relevantes, los pasa al LLM junto con un prompt muy estructurado, el LLM devuelve un JSON, el sistema lo valida con Pydantic, y todo queda logueado. Las tres areas donde podes profundizar si te preguntan son la eleccion del modelo, el diseno del prompt, y la calidad del corpus. Cualquiera de las tres tiene material para una respuesta de dos minutos que demuestra que pensaste en el problema.

Lo que aprendi yo construyendo esto, y lo que vale la pena que repitas en tus propias palabras, es que la distancia entre un LLM generico y un sistema util con LLM esta casi toda en tres cosas, en tener un buen corpus que de contexto relevante, en escribir un prompt que restrinja el formato y la honestidad del modelo, y en medir la calidad con algo cuantitativo. Cualquiera de las tres que descuides, el sistema se cae. Las tres juntas, tienes algo que funciona, que escala, y que podes defender con datos. Eso es todo. Buena suerte con la defensa.

---

# Mapa del codigo (referencia rapida)

Para cuando necesites encontrar algo puntual, esta es la guia de donde esta cada cosa.

La estructura del proyecto es la siguiente. En la raiz estan los documentos principales, que son `AGENTS.md` que es la guia de trabajo, `README.md` que es lo que lee alguien que recien llega al proyecto, `plan.md` que tiene las decisiones tecnicas justificadas, `informe.md` y `informe.pdf` que son el informe de la evaluacion, y `PRESENTACION.md` que es el esqueleto de la presentacion. En la carpeta `data/normativa/` estan los PDFs fuente, y la subcarpeta `docs/normativa-excluida/` tiene los que excluimos del corpus con la justificacion. En `data/chroma/` se guarda la base de datos vectorial, y en `data/eval/` estan todos los outputs de las evaluaciones.

En la carpeta `src/` vive todo el codigo de la aplicacion. La subcarpeta `src/indexer/` tiene el codigo de indexacion, con `ingest.py` que carga PDFs, `chunk.py` que los divide, `embed.py` que genera embeddings, y `build_index.py` que orquesta todo. La subcarpeta `src/retriever/` tiene `search.py` que es el codigo de busqueda. La subcarpeta `src/agent/` tiene `auditor.py` que es la logica del agente, `llm.py` que es el wrapper del LLM, `prompts.py` que tiene los prompts, y `judge.py` que es el LLM-as-judge. La subcarpeta `src/mcp_server/` tiene `server.py` que es el servidor MCP, y `auth.py` que es el middleware de autenticacion.

En la carpeta `tests/` estan los tests pytest, que mockean todo y son rapidos. En la carpeta `scripts/` estan los scripts auxiliares, como `eval_prompts.py` para correr la bateria, `evaluar_con_judge.py` para el LLM-as-judge, `md_a_pdf.py` para generar el PDF, y `test_mcp_endpoint.py` para validar el endpoint HTTP. En la carpeta `docs/` estan las documentaciones adicionales, como `prompts-decisiones.md`, `judge-results.md`, `casos-prueba.md`, `setup-groq.md`, `conexion-mcp.md`, y `prompt-diagrama.md`. En `data/eval/` estan los resultados de las evaluaciones, en `v1/` y `v2/` los outputs por caso, y `mcp_endpoint_demo.json` la salida real del endpoint MCP para usar como evidencia.
