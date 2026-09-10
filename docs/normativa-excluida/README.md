# Normativa excluida del corpus

Documentos descargados de sec.cl que se excluyeron del RAG por decisión de alcance.

## RIC N°04 — Conductores, materiales y sistemas de canalización

- **Archivo original**: `RIC-N04-Conductores-y-Canalizaciones.pdf`
- **Ubicación actual**: `docs/normativa-excluida/RIC-N04-Conductores-y-Canalizaciones.pdf`
- **Tamaño**: 4.3 MB
- **Páginas**: 93
- **Palabras**: ~31.000
- **Chunks estimados si se indexara**: ~250-400

### Razón de exclusión

El RIC N°04 es **específico sobre conductores y canalizaciones** (materiales, calibres, tipos de cable, métodos de instalación). Útil para publicaciones muy técnicas de cableado, pero:

1. **Desbalance del corpus**: solo este PDF representa ~30% del total de tokens potenciales. Los otros 5 PDFs de SEC + la Ley 21.442 caben en el 70% restante.
2. **Casos de uso poco probables**: la mayoría de las publicaciones de administradores de comunidad no serán sobre cambio de conductores específicos, sino sobre "reparación eléctrica general", "corto circuito", "cambio de tablero", etc., que están cubiertas por los RIC N°01, N°02, N°05 y N°06.
3. **Velocidad del MVP**: para el MVP es más importante tener cobertura amplia con menos profundidad, que profundidad alta con poca cobertura.

### Si en el futuro se quiere incluir

- Re-mover el archivo a `data/normativa/`
- Correr `python -m src.indexer.build_index --sobreescribir`
- Esperar ~5-10 minutos extra de indexación
- Validar que las búsquedas siguen retornando resultados relevantes (re-ranking podría ser necesario)
