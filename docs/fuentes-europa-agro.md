# Fuentes: Eurostat, precios agrarios, embalses y lonjas

**Última actualización:** 2026-09-15 (fase 0 cerrada; decisiones D8–D10 en `ampliacion-nuts2-agro.md` de la ampliación, ver
[`ampliacion-nuts2-agro.md`](ampliacion-nuts2-agro.md))

Cómo se verificó: las API se llamaron **desde el navegador del PC de
producción** (misma red que usará la tarea programada), ejecutando `fetch()`
dentro de la propia página y resumiendo la respuesta con JavaScript — el
método recomendado en `fuentes-ine.md` para respuestas grandes. Las fuentes
de ficheros (FAO, Banco Mundial, MITECO, Salamanca) se inspeccionaron sin
descargar nada al PC. **Nada de esto ha tocado la base de datos.**

> ⚠️ **Acceso de red:** el entorno cloud de trabajo y la máquina virtual
> Linux del PC no tienen salida a estas webs; el Python de Windows del PC
> (el que ejecuta la tarea programada) sí, igual que ya pasaba con el INE.
> Las pruebas de código en fases 1–3 se harán con JSON/CSV capturados
> (tests sin red) y la carga real en el PC.

---

## 1. Eurostat (NUTS2) — ✅ verificado

- **Endpoint:** `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset>?<filtros>`
  → JSON-stat 2.0 (`id`, `size`, `dimension`, `value` como diccionario
  índice→valor **disperso**, `status` con flags como `p` = provisional).
- **Sin autenticación.** Filtros por dimensión repitiendo parámetro
  (`geo=ES43&geo=ES`), `sinceTimePeriod`, `lastTimePeriod`.
- **Límite:** extracciones > 5.000.000 celdas devuelven **HTTP 413
  `EXTRACTION_TOO_BIG`** (visto en `ef_lsk_main` sin filtros) → el cliente
  debe pedir siempre con filtros de dimensión y trocear si hace falta.
- **Cuidado con `lastTimePeriod=1`:** devuelve el último periodo del dataset
  aunque esa región no tenga dato (p.ej. `rd_e_gerdreg` 2024 vacío para
  ES43, `nama_10r_2hhinc` 2024 vacío) → usar `sinceTimePeriod` en la carga.
- **Territorios:** la dimensión `geo` mezcla países (`ES`), agregados
  (`EU27_2020`), NUTS1 (`ES4`), NUTS2 (`ES43`) y a veces NUTS3 (`ES431`) y
  regiones de países no UE (EFTA, candidatos). Hay que clasificar por
  longitud de código + lista de países UE. Extremadura = `ES43`,
  Badajoz = `ES431`, Cáceres = `ES432`.

| Dataset | Contenido | Dimensiones clave (filtro usado) | Último periodo | ES43 | España | UE27 |
|---|---|---|---|---|---|---|
| `nama_10r_2gdp` | PIB regional | `unit=PPS_EU27_2020_HAB` (también `MIO_EUR`, `EUR_HAB`…) | 2024 | 28.100 PPS/hab | 36.400 | 39.900 |
| `nama_10r_3gva` | VAB por ramas (**NUTS3**, incluye NUTS2) | `unit=CP_MEUR`, `nace_r2` (TOTAL, A, C…, 15 ramas) | 2024 | VAB agrario 2.175,7 M€ / total 24.188 M€ | 43.892 / 1.452.583 | 290.725 / 16.199.614 |
| `lfst_r_lfu3rt` | Tasa de paro | `sex=T&age=Y15-74&isced11=TOTAL` | 2025 | 14,8 % | 10,5 % | 6,0 % |
| `lfst_r_lfe2emprt` | Tasa de empleo | `sex=T&age=Y20-64` | 2025 | 66,9 % | 72,4 % | 76,1 % |
| `lfst_r_lfe2en2` | Ocupados por rama | `nace_r2=A&sex=T&age=Y15-74`, miles | 2025 | 39,9 | 762,7 | 6.534,5 |
| `rd_e_gerdreg` | Gasto en I+D | `unit=PC_GDP&sectperf=TOTAL` | 2023 (2024 vacío) | 0,71 % PIB | 1,49 % | 2,26 % |
| `demo_r_d2jan` | Población 1 enero | `sex=T&age=TOTAL` | 2025 | 1.053.345 | 49.128.297 | 450.646.971 |
| `nama_10r_2hhinc` | Renta disponible hogares | `unit=PPS_EU27_2020_HAB&na_item=B6N&direct=BAL` | 2023 (p) | 16.900 PPS/hab (2023) | — | — |
| `ef_lsk_main` | Cabaña ganadera (encuesta estructuras) | `animals`, `unit` (LSU/HD/HLD), `farmtype`, `so_eur`, `uaarea`, `lsu`, `statinfo` | 2023 | ✅ datos (filtrar siempre) | | |
| `tgs00010` | Paro NUTS2 (tabla resumen) | — | 2025 | 14,8 % | | |

**Descartado / corregido respecto al documento de origen:**
`lfst_r_lfe2act` y `agr_r_animal` → **HTTP 404** (no existen o fueron
sustituidos). Alternativas: `lfst_r_lfe2emprt` / `lfst_r_lfe2en2` y
`ef_lsk_main`.

Pendiente para fase 1: fijar la versión NUTS (2021 vs 2024) que usa cada
dataset y elegir la lista final de indicadores.

## 2. Portal Agri-food de la Comisión Europea (DG AGRI) — ✅ verificado

- **Base:** `https://api.tech.ec.europa.eu/agrifood` (la documentación está en
  `agridata.ec.europa.eu`; las rutas `agridata.ec.europa.eu/api/...` dan 404).
  OpenAPI: `https://api.tech.ec.europa.eu/agrifood/v3/api-docs`.
- **Sin autenticación**, con límite de peticiones (HTTP 429 con
  `nextAccessTime`) → pausa entre peticiones, como con el INE.
- **Fechas** en formato `dd/MM/yyyy` (parámetros `beginDate`/`endDate`).
- **Precios como texto con símbolo y formato decimal inconsistente:**
  `"€699.95"` (vacuno, porcino) pero `"€233,00"` (cereales, 3.093/3.093
  filas con coma) → normalizar en el parser.
- **Histórico largo:** porcino España disponible al menos desde 2000.
- `memberStateCodes=EU` devuelve la media de la UE.

| Endpoint | Datos | Campos | Ejemplo verificado (semana 31/08–06/09/2026) |
|---|---|---|---|
| `/api/pigmeat/prices` | Canal porcino clases S/E/R + lechón, semanal | `memberStateCode, beginDate, endDate, price, unit, weekNumber, pigClass` | ES clase E 172,12 €/100 kg; UE clase S 172,88 |
| `/api/beef/prices` | Vacuno por categoría (novillas, añojos, vacas…) | `+ category, productCode` | ES novillas 699,95 €/100 kg |
| `/api/sheepAndGoat/prices` | Cordero pesado / ligero | `+ category, marketName, marketingYear` | ES cordero pesado 1.008 €/100 kg |
| `/api/cereal/prices` | Cereales por **mercado** | `+ productName, marketName, stageName, referencePeriod` | Mercados ES incluyen **Badajoz** |
| `/api/oliveOil/prices` | Aceite por mercado | `+ product, market, marketingYear` | Mercados ES incluyen **Badajoz (ES431)** |
| `/api/rawMilk/prices` | Leche cruda mensual | `+ month, year, product` | ES agosto 45,05 €/100 kg |
| `/api/fertiliser/prices` | Fertilizantes N/P/K, UE, mensual | `year, quarter, month, product, price, unit` | K 364 €/t (ago-2026) |
| también: `/api/pigmeat/cuts/prices`, `/api/dairy/prices`, `/api/oilseeds/prices` | | | no probados aún |

**Relevante:** Badajoz aparece como mercado propio en cereales y aceite, así
que hay dato extremeño oficial sin raspar nada.

## 3. Referencias mundiales — ✅ localizadas (formato de fichero)

- **FAO Food Price Index:** página
  `https://www.fao.org/worldfoodsituation/foodpricesindex/en/`. CSV mensual
  desde 1990 (`Date, Food Price Index, Meat, Dairy, Cereals, Oils, Sugar`,
  2014-2016=100; 3 filas de cabecera antes de los datos; ago-2026 = 133,3).
  **La URL del fichero lleva un parámetro de versión (`?sfvrsn=...`) que
  cambia en cada publicación** → el cliente debe leer la página y extraer el
  enlace, no fijar la URL. Publicación mensual (próxima: 2026-10-02).
- **Banco Mundial Pink Sheet:** `CMO-Historical-Data-Monthly.xlsx`, enlazado
  desde `https://www.worldbank.org/en/research/commodity-markets`. La ruta
  incluye un identificador de publicación (`...-0050012026/`) → igual,
  descubrir el enlace desde la página. Estructura interna del XLSX pendiente
  de inspeccionar al implementarlo (fase 3).

## 4. Embalses (MITECO) — ✅ fuente localizada, ⏳ formato interno pendiente

- **Histórico completo:** `BD-Embalses.zip` —
  `https://www.miteco.gob.es/content/dam/miteco/es/agua/temas/evaluacion-de-los-recursos-hidricos/boletin-hidrologico/Historico-de-embalses/BD-Embalses.zip`
  — capacidad y reserva **semanal de cada embalse peninsular > 5 hm³ desde
  1988**, actualizado cada semana (el boletín sale los martes). Modelo de
  datos en PDF enlazado desde la página del Boletín Hidrológico.
- Semanal en PDF: `https://sede.miteco.gob.es/BoleHWeb/`.
- Datos provisionales según MITECO ("sujetos a revisión y validación").
- **Pendiente:** descargar el ZIP (requiere permiso del usuario) y ver el
  formato interno — probablemente base de datos Access (`.mdb`), que en
  Windows se leería con el driver ODBC de Access o con una librería Python.
- SAIH Guadiana / Tajo (tiempo real) quedan como complemento opcional; el
  boletín semanal es la fuente oficial homogénea para toda España.

## 5. Precios locales y lonjas

| Fuente | Acceso | Formato | Contenido | Estado |
|---|---|---|---|---|
| **Observatorio de Precios y Mercados (Junta de Extremadura)** — `observatoriopreciosymercados.juntaex.es/precios` | Público | HTML (Liferay/PrimeFaces) con botón **"Exportar a CSV"** por producto; campañas 2023–2026 | Precios semanales **por provincia (Badajoz/Cáceres)**: aceites, cereales (cebada, trigo, maíz, avena, triticale, arroz), fruta, almendra, uva, vino, tomate industria | ✅ verificado. Solo sector **agricultura**; la pestaña ganadería no tiene registros. La exportación CSV es un *postback* JSF (hará falta sesión + `ViewState`, o un navegador automatizado) |
| **Lonja Agropecuaria de Extremadura** (Mérida) — `lonjaextremadura.es` | **Solo con usuario** en `intranet.lonjaextremadura.es` (registro) | Desconocido tras el login | 8 mesas: cereales, aceite, vino, caza, vacuno, **porcino ibérico**, leche oveja/cabra, ovino | ❌ descartada por el usuario (2026-09-15): requiere alta; se usan en su lugar la Junta y el portal Agri-food |
| **Lonja Agropecuaria de Salamanca** — datos abiertos de la Diputación: `datosabiertossalamanca.es/dataset/cotizaciones-semanales-de-la-lonja-de-salamanca` | Público, **CC-BY 4.0**, portal CKAN | **CSV** (`;`, coma decimal), XLSX, XML | Cereales, ovino, bovino vida/carne, **porcino blanco e ibérico (bellota, cebo de campo, cebo)**, despiece ibérico | ✅ verificado. Columnas `ID;FECHA;MESA;PRODUCTO;CATEGORIA;VALOR1;VALOR2`. **El fichero solo trae las últimas ~5 semanas** → hay que capturarlo cada semana para acumular histórico; el histórico anterior existe en PDF (difundido por ASAJA) → candidato a extracción PDF/OCR |
| **MAPA — Precios Medios Nacionales** | Público | **XLSX** anual por semanas, 2019–2026 (`precios_medios_nacionales_<año>-s<semana>.xlsx`, el nombre cambia cada semana) | Precios medios nacionales ponderados de productos agrícolas y ganaderos | ✅ localizado; estructura interna pendiente |
| **MAPA — Precios coyunturales ganaderos** | Público | PDF semanal (vacuno, ovino) | Precios en mercados representativos | Localizado; PDF → extracción de texto |

## 6. Extracción de documentos / OCR

- **Resultado clave:** con las fuentes encontradas, **la mayoría de los datos
  no necesitan OCR** (JSON, CSV, XLSX o HTML). La extracción de PDF queda
  para: histórico de la Lonja de Salamanca, fichas del MAPA y, si se
  habilita, la Lonja de Extremadura.
- Entorno de ejecución real: **Python 3.12 de Windows** (`.venv`, hoy solo
  con `requests`, `psycopg2-binary`, `python-dotenv`). Habrá que añadir
  `pandas`, `openpyxl`, `pdfplumber` (PDF con texto) y, solo si aparece un PDF
  escaneado, Tesseract para Windows + `pytesseract`.
- La máquina virtual Linux de Cowork en el PC ya tiene `tesseract` y
  `pdftotext`, útil para pruebas, pero **no** es donde corre la tarea
  programada.
- Pendiente: probar `pdfplumber` con un boletín PDF real de Salamanca
  (requiere descargar un PDF de prueba).

## 7. Catálogo Eurostat implementado (fase 1, 2026-09-15)

9 indicadores en `src/extremadura_datos/indicadores.py` (`fuente="eurostat"`).
Tamaño de cada descarga histórica medido contra la API real (sin `geo`, con
los filtros del catálogo):

| Código interno | Dataset | Filtros | Años | Descarga |
|---|---|---|---|---|
| `eurostat_pib_nuts2` | `nama_10r_2gdp` | unit = MIO_EUR, EUR_HAB, PPS_EU27_2020_HAB | 2000–2024 | 0,5 MB |
| `eurostat_vab_ramas_nuts2` | `nama_10r_3gva` | unit = CP_MEUR (15 ramas NACE) | 2000–2024 | 8,8 MB |
| `eurostat_paro_nuts2` | `lfst_r_lfu3rt` | isced11 = TOTAL; sex = T, M, F; age = Y15-74, Y15-24 | 1999–2025 | 1,2 MB |
| `eurostat_empleo_nuts2` | `lfst_r_lfe2emprt` | sex = T, M, F; age = Y20-64 | 1999–2025 | 0,6 MB |
| `eurostat_ocupados_ramas_nuts2` | `lfst_r_lfe2en2` | sex = T; age = Y15-74 (12 ramas) | 2008–2025 | 1,6 MB |
| `eurostat_id_nuts2` | `rd_e_gerdreg` | unit = PC_GDP, EUR_HAB (5 sectores) | 1980–2024 | 1,4 MB |
| `eurostat_poblacion_nuts2` | `demo_r_d2jan` | sex = T; age = TOTAL | 1990–2025 | 0,3 MB |
| `eurostat_renta_hogares_nuts2` | `nama_10r_2hhinc` | unit = PPS_EU27_2020_HAB, EUR_HAB; na_item = B6N; direct = BAL | 2000–2024 | 0,3 MB |
| `eurostat_ganaderia_nuts2` | `ef_lsk_main` | farmtype, so_eur, uaarea, lsu, statinfo = TOTAL; unit = LSU, HD (8 especies) | 2005–2023 | 0,4 MB |

**Qué territorios se guardan** (`eurostat_parse.clasificar_geo`): UE-27
(`EU27_2020`), los 27 países, todas sus NUTS2 y Badajoz/Cáceres (`ES431`,
`ES432`). Se descartan NUTS1, el resto de NUTS3, "Extra-Regio" (`xxZZ`),
otros agregados y regiones de fuera de la UE-27.

**Cómo se modela:** cada combinación de dimensiones (unidad, rama, sexo,
edad…) + territorio es una `serie` con `codigo_origen` estable
`dataset|dim=COD.dim=COD|GEO` y las dimensiones en `serie.atributos`
(`{"unit": {"nombre": ..., "codigo": ...}}`). Los flags de Eurostat van a
`observacion.tipo_dato` con su etiqueta ("provisional", "estimated", "break
in time series"…); el confidencial (`C`) se guarda como `secreto`.

**Modo incremental:** petición mínima (`geo=ES43&lastTimePeriod=1`) para leer
`updated`; si no cambió desde la última carga, no se descarga. Si cambió, o
no se pudo leer, se piden los últimos 6 años.

## 8. Precios agrarios implementados (fase 3, 2026-09-16)

| Código interno | Fuente / endpoint | Periodicidad | Cobertura cargada | Territorios | Observaciones |
|---|---|---|---|---|---|
| `agrifood_porcino` | Agri-food `pigmeat/prices` (clases S, E, R, media S+E, lechón) | Semanal | 2010 → sep-2026 | 27 países + UE | 59.195 |
| `agrifood_vacuno` | Agri-food `beef/prices` (categoría × clasificación) | Semanal | 2010 → sep-2026 | ES, PT, FR, IT, DE, IE, NL, PL + UE | 226.308 |
| `agrifood_ovino` | Agri-food `sheepAndGoat/prices` (cordero pesado/ligero) | Semanal | 2015 → sep-2026 (inicio de la API) | 24 países + UE | 17.541 |
| `agrifood_cereales` | Agri-food `cereal/prices` (producto × mercado × fase) | Semanal | nov-2015 → sep-2026 | 26 países + UE + **Badajoz** | 178.237 |
| `agrifood_aceite` | Agri-food `oliveOil/prices` (categoría × mercado) | Semanal | 2010 → sep-2026 | ES, IT, EL, PT, HR... + **Badajoz** | 60.297 |
| `agrifood_leche` | Agri-food `rawMilk/prices` | Mensual | 2010 → sep-2026 | 27 países + UE | 6.877 |
| `agrifood_fertilizantes` | Agri-food `fertiliser/prices` (N, P, K) | Mensual | 2019 → ago-2026 | UE | 276 |
| `fao_indice_precios_alimentos` | FAO, CSV del Food Price Index (general + 5 grupos) | Mensual | 1990 → ago-2026 | Mundo | 2.640 |
| `junta_precios_agricolas` | Observatorio de Precios de la Junta (23 productos agrícolas, en origen) | Semanal | 2023 → sep-2026 | Badajoz, Cáceres | 1.246 |

Detalles de modelado:

- **Semanas:** `periodo_fecha` = lunes de la semana, `periodo_codigo` = `S` +
  semana ISO, `anyo` = año ISO (la semana del 29-dic-2025 es `S01` de 2026).
- **Unidades normalizadas:** `€/100 kg`, `€/t`, `€/cabeza` (lechón); la
  unidad original va en `serie.atributos.unidad_origen`. En la Junta se
  guarda tal cual la da la fuente (`€/100 kg`, `€/t`, `€/kg de pepita`,
  `€/100 kilogrado`, `€/hl`).
- **Territorios:** `Mundo` (nuevo, `codigo_nuts` `WORLD`), `Unión Europea
  (27)` para la media UE (`EU`), países por su código; mercados de Badajoz y
  Cáceres a su provincia; resto de mercados cuelgan del país con el mercado
  en `serie.atributos`.
- **Deduplicación:** `db.upsert_observaciones` deja una fila por serie y
  periodo dentro de cada lote (el portal Agri-food repite semanas en el
  cambio de campaña).
- **Observatorio de la Junta — hallazgos al cargarlo:** la campaña elegida se
  guarda en la sesión del servidor (hay que cambiarla con la llamada AJAX
  antes de exportar); 13 de 23 productos no tienen campaña 2023 y el servidor
  devuelve HTML en vez de CSV (se salta esa campaña); los datos son
  dispersos (semanas sueltas en cereales, campañas en fruta). Solo hay sector
  agricultura (ganadería vacía).
- **Pendiente:** Banco Mundial (Pink Sheet en XLSX; hace falta `openpyxl` en
  el `.venv` del PC) y reglas de plausibilidad de precios.
