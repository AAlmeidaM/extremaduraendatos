# Ampliación: comparativa NUTS2 europea y sector agropecuario

> **Documento vivo de seguimiento.** Aquí se registra el plan, las decisiones
> y **cada avance** de esta ampliación. Regla: cada vez que se avance (se
> verifique una fuente, se implemente un módulo, se cargue algo en
> producción, se descarte una idea), se actualiza el **§6 Estado por fase**
> y se añade una línea al **§7 Registro de avances**, además de la entrada
> habitual en `CHANGELOG.md` y, si es relevante, en `PROJECT.md` §17.
>
> Documento de origen (investigación aportada por el usuario el 2026-09-15):
> *"Ampliación del Monitor Económico: Comparativa NUTS2 Europea y Sector
> Agropecuario de Extremadura"*.

**Creado:** 2026-09-15 · **Última actualización:** 2026-09-15 ·
**Estado global:** ✅ Fase 1 (Eurostat) en producción (2026-09-16). Siguiente: fase 3 (precios agrarios). Fase 2 aplazada.

---

## 1. Objetivo

Ampliar *Extremadura en Datos* en dos direcciones:

1. **Comparativa europea:** situar Extremadura (NUTS2 `ES43`) frente a todas
   las regiones NUTS2 de la UE (~240) en PIB, VAB sectorial, empleo, I+D y
   estructura agraria, con datos normalizados (Z-scores, Min-Max, índices
   compuestos).
2. **Monitor agropecuario:** precios de lonjas regionales, precios agrarios
   europeos (por Estado miembro) e internacionales (FAO, Banco Mundial), y
   reservas hídricas de las cuencas del Guadiana y del Tajo — con análisis de
   transmisión de precios (correlación con desfase) y de la relación agua →
   VAB agrario.

Todo encaja en la arquitectura de tres capas ya decidida (`PROJECT.md` §4):
capa 1 ingesta → capa 2 análisis pandas (`analisis_web`) → capa 3 web.

## 2. Decisiones tomadas (2026-09-15)

| # | Decisión | Motivo |
|---|---|---|
| D1 | **Alcance: fases 0–4** (ingesta + capa de análisis). La web (fase 5) queda fuera de esta ampliación. | Consolidar datos y análisis antes de elegir stack web. |
| D2 | **Comparación contra todas las NUTS2 de la UE.** | Medias y Z-scores representativos de la UE, no de una muestra sesgada. |
| D3 | **Mercados: solo fuentes gratuitas y oficiales** (portal Agri-food DG AGRI, FAO, Banco Mundial). Sin futuros MATIF/CBOT en tiempo real. | Los datos de futuros en tiempo real requieren licencia; el raspado de Euronext es frágil y de dudoso encaje en sus condiciones de uso. |
| D4 | **Lonjas regionales sí, con descarga y procesamiento local diario** (ver §4). Formato estructurado (CSV/XLSX/HTML/PDF con texto) se automatiza directamente; PDF escaneado → OCR local. | Dato local imprescindible para medir la transmisión de precios; no hay API. |
| D5 | **Comparativa europea también en precios agrarios** (DG AGRI por Estado miembro + Eurostat agrario NUTS2). | Petición del usuario: poder comparar lonja extremeña / España / UE. |
| D6 | **No se adopta la arquitectura técnica del documento de origen** (Vercel Edge, Redis/Upstash, Ollama como motor de resúmenes, MCP, Deck.gl). | Procede del proyecto *worldmonitor* y no encaja con el Office Lab (todo local, PostgreSQL compartido, sin servicios cloud). Se revisará al diseñar la web (fase 5). Ollama sí puede usarse como apoyo de OCR (ver §4). |
| D8 | **Embalses fuera por ahora** (2026-09-15): la fase 2 queda aplazada; no se descarga `BD-Embalses.zip`. | Decisión del usuario: poco relevante de momento. |
| D9 | **Sin extracción de PDF/OCR por ahora** (2026-09-15): no se procesa el histórico en PDF de la Lonja de Salamanca. | Decisión del usuario: poco relevante de momento. |
| D10 | **Lonja de Extremadura fuera** (2026-09-15): requiere registro; los precios locales se toman del Observatorio de Precios de la Junta y del portal Agri-food de la Comisión (mercados de Badajoz). | Decisión del usuario: con esas dos fuentes basta de momento. |
| D7 | **Las afirmaciones cuantitativas del documento de origen no se dan por buenas** (p.ej. "poder predictivo sustancial" de embalses sobre VAB, plazos de transmisión de 1–2 semanas). | Son hipótesis; se contrastarán con nuestros datos en la fase 4. |

## 3. Fuentes previstas (pendientes de verificar en fase 0)

| Fuente | Acceso previsto | Frecuencia | Territorio | Qué aporta |
|---|---|---|---|---|
| **Eurostat** | API JSON-stat (verificada) | Anual | NUTS2 UE | PIB (`nama_10r_2gdp`), VAB por ramas (`nama_10r_3gva`), paro/empleo (`lfst_r_lfu3rt`, `lfst_r_lfe2emprt`, `lfst_r_lfe2en2`), I+D (`rd_e_gerdreg`), población (`demo_r_d2jan`), renta hogares (`nama_10r_2hhinc`), cabaña ganadera (`ef_lsk_main`) — ver `fuentes-europa-agro.md` |
| **Portal Agri-food (DG AGRI)** | API REST pública | Semanal | Estado miembro (algunas veces mercado) | Precios de cereales, porcino, vacuno, ovino, leche, aceite — España vs resto UE |
| **FAO** | Descarga CSV (Food Price Index) | Mensual | Mundial | Índices de cereales, aceites, carne, lácteos |
| **Banco Mundial (Pink Sheet)** | Descarga XLSX | Mensual | Mundial | Precios de materias primas (trigo, maíz, soja…) |
| **Embalses (MITECO / SAIH Guadiana y Tajo)** | Boletín hidrológico semanal / portales de cuenca | Semanal (a veces diaria) | Embalse / cuenca | Volumen embalsado, capacidad, % |
| **Precios locales / lonjas** | CSV/XLSX/HTML (verificado); PDF para histórico | Semanal | Provincia / lonja | Observatorio de Precios Junta de Extremadura (Badajoz/Cáceres), Lonja de Salamanca (datos abiertos, ibérico), MAPA precios medios nacionales; Lonja de Extremadura pendiente (acceso con registro) |
| INE / Banco de España | Ya integrado (INE) / REST (BdE, opcional) | — | — | Ya disponible / crédito autonómico (opcional) |

## 4. Diseño del sistema de lonjas (descarga + extracción local)

Pipeline diario, ejecutado en este PC dentro de la tarea programada existente:

1. **Descarga.** Un "adaptador" por lonja (`src/extremadura_datos/lonjas/<lonja>.py`)
   sabe dónde publica y cómo localizar el boletín nuevo. Cada documento se
   guarda tal cual en `E:\Lab\datasets\extremadura-en-datos\lonjas\raw\<lonja>\`
   y se registra con su hash (SHA-256): si ya se procesó, no se repite.
2. **Extracción por formato** (de más a menos fiable):
   - CSV/XLSX → pandas directo.
   - HTML → parseo de la tabla.
   - PDF con capa de texto → extracción de tablas (pdfplumber / camelot).
   - PDF escaneado o imagen → **OCR local** (Tesseract o PaddleOCR; como
     apoyo opcional, modelo de visión local vía Ollama para tablas difíciles).
     Qué motor usar se decide en fase 0 según calidad y hardware del PC.
3. **Normalización.** Tabla de equivalencias producto-lonja → producto de
   catálogo (p.ej. "Cebo de campo 50% ibérico" → `porcino_iberico_cebo_campo_50`),
   con unidad homogénea (€/kg vivo, €/t, €/cabeza) y precio mín/máx/medio.
4. **Validación antes de cargar** (crítico con OCR): rango plausible por
   producto, salto máximo frente a la semana anterior, mín ≤ medio ≤ máx,
   fecha coherente. Lo que falla va a una tabla de **cuarentena/revisión** y
   no se carga hasta revisarlo.
5. **Carga** con `db.upsert_observaciones` (idempotente). Cada observación
   queda trazada al documento de origen (hash). Un fallo de una lonja no
   afecta al resto de la ingesta.

## 5. Cambios de modelo de datos previstos

- `territorio.nivel`: añadir `nuts2` (y los que hagan falta, p.ej. `pais_ue`,
  `mundo`), columna `codigo_nuts` (Extremadura = `ES43`, Badajoz/Cáceres
  NUTS3 `ES431`/`ES432`) y país.
- Series sin territorio geográfico (FAO, Banco Mundial) → territorio
  `Mundo`.
- Periodicidad **semanal y diaria** (embalses, precios) — revisar `periodo`,
  `calendario.py` y el modo incremental.
- Embalses: una serie por embalse; cuenca y capacidad en `serie.atributos`.
- Tablas nuevas para lonjas: `documento_fuente` (hash, url, formato, fecha,
  estado) y `extraccion_revision` (cuarentena). Nombres definitivos en fase 3.
- Catálogo con campo `fuente` (hoy todo es INE).

Todo con cambios idempotentes en `sql/` (mismo patrón que hasta ahora:
`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`), sin romper lo ya cargado.

## 6. Estado por fase

Leyenda: ⬜ pendiente · 🔄 en curso · ✅ hecho · ⛔ bloqueado · ❌ descartado

### Fase 0 — Verificación de fuentes (sin tocar producción)

| Tarea | Estado | Notas |
|---|---|---|
| Eurostat: probar API y tablas NUTS2 (PIB, VAB, empleo, I+D, agrario) | ✅ | 10 datasets probados; `lfst_r_lfe2act` y `agr_r_animal` no existen (404) → sustituidos. Límite 5M celdas (413). Ver `fuentes-europa-agro.md` §1 |
| Portal Agri-food DG AGRI: endpoints y cobertura de precios España/UE | ✅ | Base `api.tech.ec.europa.eu/agrifood`, sin clave. Porcino, vacuno, ovino, cereales, aceite, leche, fertilizantes. **Badajoz** es mercado propio en cereales y aceite. §2 |
| FAO Food Price Index: formato de descarga | ✅ | CSV mensual desde 1990; URL cambia en cada publicación → descubrir enlace. §3 |
| Banco Mundial Pink Sheet: formato de descarga | ✅ | Localizado XLSX mensual (URL versionada); estructura interna se mira al implementarlo (fase 3). §3 |
| Embalses: fuente oficial reutilizable (MITECO / SAIH) y formato | ✅ | `BD-Embalses.zip` MITECO: semanal por embalse desde 1988. Formato interno sin mirar: fase 2 aplazada (D8). §4 |
| Lonjas: identificar lonjas relevantes, formato, frecuencia e histórico de cada una | 🔄 | Observatorio Junta (CSV por provincia, agricultura) ✅; Lonja de Salamanca (CSV abierto CC-BY con ibérico, solo últimas ~5 semanas) ✅; MAPA precios medios (XLSX) ✅; **Lonja de Extremadura ❌ descartada (D10). §5 |
| OCR local: probar Tesseract / PaddleOCR (y Ollama visión) en este PC con un boletín real | ❌ | No necesario de momento (D9).  La mayoría de fuentes no necesitan OCR. Falta probar `pdfplumber` con un PDF real de Salamanca (descarga de prueba). §6 |
| Documentar resultados en `docs/fuentes-*.md` | ✅ | `docs/fuentes-europa-agro.md` |

### Fase 1 — Eurostat NUTS2

| Tarea | Estado | Notas |
|---|---|---|
| Esquema: nivel `nuts2`, `codigo_nuts`, país, campo `fuente` en catálogo | ✅ | `sql/001_schema.sql` (sección 2026-09-15): fuente `eurostat`, `territorio.codigo_nuts` (CCAA españolas reutilizadas: ES43 = Extremadura), niveles `nuts2`/`agregado`, `indicador.origen_actualizado` |
| `eurostat_client.py` + parser JSON-stat | ✅ | `eurostat_client.py`, `eurostat_parse.py` (valores dispersos, flags, confidencial → secreto, selección de territorios), `eurostat_ingest.py` (incremental por fecha `updated`) |
| Catálogo de indicadores Eurostat | ✅ | 9 indicadores en `indicadores.py`: PIB, VAB por ramas, paro, empleo, ocupados por rama, I+D, población, renta de hogares, cabaña ganadera |
| Tests sin red con JSON real capturado | ✅ | `tests/test_eurostat_parse.py` + `tests/fixtures/` (17/17 tests OK). Prueba de integración en PostgreSQL 16 de pruebas: esquema nuevo sobre el esquema de producción con datos INE, aplicado 2 veces sin cambios; 2 cargas Eurostat idénticas (43 obs, idempotente); INE y Eurostat comparten territorio Extremadura; países y NUTS2 europeos creados con su padre; modo incremental (omitir si `updated` no cambia, descargar si cambia o si falla la sonda, error 413 registrado) |
| Carga histórica en producción + verificación de idempotencia | ✅ | 2026-09-16, `carga_eurostat.bat` lanzado dos veces seguidas en el PC: **327.403 observaciones** de Eurostat (9/9 indicadores con datos, 1990–2025 según tabla), ~1 min por pasada, sin errores. Segunda pasada: mismos recuentos (idempotente). Total en la base: 1.485.844 (INE sin cambios: 1.158.441) |

### Fase 2 — Agua (embalses) — ⏸️ aplazada (D8)

| Tarea | Estado | Notas |
|---|---|---|
| Cliente/adaptador de reservas hídricas | ⬜ | |
| Series por embalse y cuenca (Guadiana, Tajo) con capacidad | ⬜ | |
| Periodicidad semanal en ingesta incremental | ⬜ | |
| Carga histórica + verificación | ⬜ | |

### Fase 3 — Precios agrarios

| Tarea | Estado | Notas |
|---|---|---|
| DG AGRI: cliente + catálogo (España y resto UE) | ⬜ | |
| FAO y Banco Mundial | ⬜ | |
| Observatorio de Precios Junta de Extremadura (CSV por provincia) | ⬜ | Sustituye a las lonjas (D10) |
| Lonjas: tablas `documento_fuente` / cuarentena | ❌ | Sin PDF/OCR por ahora (D9) |
| Lonjas: descargador con hash | ⏸️ | Solo si se retoman lonjas con PDF (D9/D10); la validación sí aplicará a los CSV |
| Lonjas: extractores por formato (CSV/XLSX, HTML, PDF texto, OCR) | ⏸️ | Solo si se retoman lonjas con PDF (D9/D10); la validación sí aplicará a los CSV |
| Lonjas: equivalencias de productos y unidades | ⏸️ | Solo si se retoman lonjas con PDF (D9/D10); la validación sí aplicará a los CSV |
| Lonjas: reglas de validación | ⏸️ | Solo si se retoman lonjas con PDF (D9/D10); la validación sí aplicará a los CSV |
| Integración en la tarea diaria + verificación en producción | ⬜ | |

### Fase 4 — Capa de análisis (pandas → `analisis_web`)

| Tarea | Estado | Notas |
|---|---|---|
| Decidir punto de enganche al pipeline y esquema de `analisis_web` | ⬜ | Pendiente de `PROJECT.md` §17 |
| Z-scores y Min-Max NUTS2 (con criterio de outliers) | ⬜ | |
| Índices compuestos (pesos iguales; después PCA) | ⬜ | |
| Correlación cruzada con desfase: precios UE/mundo ↔ lonjas | ⬜ | |
| Relación reservas hídricas ↔ VAB agrario | ⬜ | |
| Validación de resultados y documentación de hallazgos | ⬜ | |

## 7. Registro de avances

Una línea por avance, la más reciente arriba. Formato:
`AAAA-MM-DD — Fase N — qué se hizo — resultado / enlace a CHANGELOG`.

- 2026-09-16 — Mantenimiento — Descubierto y corregido que la tarea diaria
  fallaba desde el 28-ago (PowerShell); corregidos también el calendario del
  INE, el formato de año CRE y `v_analisis`. Ingesta incremental real OK.
- 2026-09-16 — Fase 1 — ✅ Carga histórica real en producción: 327.403
  observaciones de Eurostat, dos pasadas idénticas (idempotente), INE intacto.
- 2026-09-15 — Fase 1 — Implementada la ingesta de Eurostat (9 indicadores
  NUTS2) y probada en un PostgreSQL de pruebas: tests con JSON real, esquema
  idempotente sobre el de producción, carga idempotente, INE y Eurostat en
  el mismo territorio. Archivos copiados al PC. Pendiente: carga histórica
  real (`carga_eurostat.bat`). Hallazgo aparte: `v_analisis` clasifica mal
  las variaciones del IPC (ver §8).
- 2026-09-15 — Fase 0 — Cerrada con decisiones del usuario: embalses y PDF
  de Salamanca fuera por ahora (D8, D9); Lonja de Extremadura fuera, precios
  locales desde la Junta y la Comisión Europea (D10).
- 2026-09-15 — Fase 0 — Verificación de fuentes desde el navegador del PC
  de producción. Eurostat, DG AGRI y FAO verificados; embalses (MITECO) y
  Pink Sheet localizados; fuentes de precios locales identificadas
  (Observatorio Junta, Lonja de Salamanca abierta, MAPA). Hallazgos: dos
  datasets del documento de origen no existen; Lonja de Extremadura requiere
  registro; casi todo el precio local llega en CSV/XLSX, el OCR queda para
  histórico en PDF. Detalle en `docs/fuentes-europa-agro.md`. Sin cambios en
  código ni base de datos.
- 2026-09-15 — Plan — Plan de ampliación acordado con el usuario y
  documentado (este archivo, `PROJECT.md` §4 y §17, `CHANGELOG.md`). Sin
  código ni cambios en la base de datos.

## 8. Riesgos y preguntas abiertas

- **Fragilidad de las lonjas:** cambian formato o URL sin avisar → adaptador
  aislado por lonja, alertas en el log y cuarentena.
- **Errores de OCR en números** → validación estricta; preferir siempre la
  capa de texto del PDF antes que OCR.
- **Histórico de lonjas:** puede no estar disponible hacia atrás; limita la
  correlación con desfase hasta acumular datos.
- **Revisiones de NUTS** (versiones 2016/2021/2024) → fijar la versión de
  NUTS usada y documentarla.
- **Condiciones de uso** de cada web raspada → revisar en fase 0.
- ~~Bug previo en `v_analisis`~~ **corregido 2026-09-16** (ver CHANGELOG).
- **Población del INE solo hasta 2021:** para normalizar por habitante en la
  fase 4 conviene usar `eurostat_poblacion_nuts2` (hasta 2025).
- **Rendimiento:** agregar toda `v_analisis` tarda ~2 min; la fase 4 debe
  trabajar por indicador/periodo, no sobre la vista entera.
- **Nombres de regiones europeas en inglés/idioma original** (etiqueta de
  Eurostat, p.ej. "Attiki", "Ile de France"); los 27 países sí en castellano.
- **Salamanca solo publica las últimas ~5 semanas en abierto** → empezar a
  capturar cuanto antes; el histórico anterior, desde PDF.
- **Red:** solo el Python de Windows del PC llega a estas webs (ni el
  entorno cloud ni la VM de Cowork) → tests con ficheros capturados.
- Abierto: motor OCR (probablemente innecesario salvo histórico); esquema de
  `analisis_web`.
