# CHANGELOG — Extremadura en Datos

## 2026-09-16 (6)

- **Documentado para retomar más adelante.** Nuevo
  `docs/ESTADO-Y-SIGUIENTES-PASOS.md`: qué hay en producción (fuentes,
  indicadores, volúmenes), modelo de datos, cómo decide cada fuente si
  descarga, lanzadores `.bat`, verificación, notas para trabajar con un
  agente de IA (red solo desde Windows, Computer Use, bloqueo de Git),
  pendientes cortos, decisiones previas a la fase 4, fases aplazadas y
  checklist para retomar. `PROJECT.md` (§1–§4, §6, §12), `README.md` y
  `docs/ampliacion-nuts2-agro.md` (nueva §8 "Siguientes pasos") actualizados
  y enlazados a él.

## 2026-09-16 (5)

- **Fase 3: precios agrarios en producción.** Tres fuentes nuevas:
  - `agrifood.py` — portal Agri-food de la Comisión Europea (DG AGRI), 7
    indicadores semanales/mensuales desde 2010: porcino, vacuno (España,
    principales productores y UE), ovino, cereales, aceite, leche,
    fertilizantes. Reintentos ante HTTP 429, "sin resultados" (404) no es
    error, precios en texto con decimal inconsistente, mercados de
    Badajoz/Cáceres a su provincia.
  - `fao.py` — índice FAO de precios de los alimentos (mensual, 1990→).
    Localiza el enlace del CSV en la página porque su URL cambia en cada
    publicación.
  - `observatorio_junta.py` — Observatorio de Precios y Mercados de la Junta
    de Extremadura: 23 productos agrícolas semanales por provincia. Sin API:
    sesión + formulario JSF + cambio de campaña por AJAX + exportación CSV.
    Muy lento (~45 s por producto) → en incremental, una vez por semana.
  - Comunes: `precios_util.py`; `Indicador.parametros_api`; periodicidad
    `semanal` (`S` + semana ISO); `db.upsert_observaciones` deduplica dentro
    del lote; esquema con las 3 fuentes, territorio `Mundo` y nivel
    `agregado` para indicadores; `ingest.py --fuente
    agrifood|fao|junta_observatorio`.
  - Tests: `tests/test_precios_agrarios.py` con muestras reales (28/28 OK) y
    prueba de integración en PostgreSQL (idempotencia, deduplicación,
    territorios, puerta semanal de la Junta).
  - **Carga histórica real** (`carga_precios.bat`, `carga_junta.bat`):
    548.731 observaciones de Agri-food, 2.640 de la FAO y 1.246 de la Junta;
    total en la base 2.048.497. Verificación con
    `scripts/verificar_precios.py` (+ `.bat`): porcino clase S España 178,08 €/100 kg
    vs UE 172,88 (semana del 31-ago-2026); aceite y maíz con mercado de
    Badajoz; índice FAO 133,3 (ago-2026).
  - **Fallo encontrado en la carga real y corregido:** en la Junta, un
    producto sin campaña 2023 (13 de 23) se descartaba entero; ahora se salta
    solo esa campaña. Relanzada la carga de la Junta: 0 errores.
  - **Pendiente:** Banco Mundial (XLSX, requiere instalar `openpyxl`) y
    reglas de plausibilidad de precios.

## 2026-09-16 (4)

- **Rendimiento de `v_analisis` resuelto: de ~6,5 min a ~20 s** (resumen
  completo de `scripts/verificar_naturaleza.py` en producción, mismos
  resultados). La población de referencia se guarda ya resuelta en la vista
  materializada nueva `mv_poblacion` (una fila por territorio y fecha con la
  fuente de mejor prioridad, índice único `(territorio_id, periodo_fecha)`), y
  `v_analisis` la consulta por índice en vez de recalcular `v_poblacion` fila
  a fila. `db.refrescar_poblacion()` la recalcula al final de cada ingesta
  (`ingest.py`; un fallo al refrescar se registra pero no deshace la
  ingesta). En pruebas con 900.000 observaciones sintéticas: 3,6 s el método
  nuevo; el anterior no terminó en 100 s. Verificado en producción:
  `probar_tarea_diaria.bat` con código 0 y "Población de referencia
  (mv_poblacion) refrescada".
- Nota: si se cambia la definición de `mv_poblacion`, hay que borrarla
  (`DROP MATERIALIZED VIEW mv_poblacion CASCADE`) antes de reaplicar el
  esquema; `IF NOT EXISTS` no la redefine (comentado en el propio SQL).

## 2026-09-16 (3)

- **Población de referencia: del Padrón congelado (2021) a la Estadística
  Continua de Población (ECP) trimestral.** Investigado a petición del
  usuario: las tablas 2853/2852 (Padrón, operación DPOP) no se actualizan
  desde dic-2021; la población por CCAA/provincia se publica ahora en la ECP
  (operación 450). Decisión del usuario: usar la trimestral y actualizarla
  cada trimestre, solo como base para normalizar el resto de variables.
  - `indicadores.py`: 4 indicadores nuevos (el INE parte cada nivel en
    tabla histórica definitiva + tabla de trimestres recientes provisional):
    `ine_ecp_poblacion_ccaa_historico` (56940), `ine_ecp_poblacion_ccaa`
    (59238), `ine_ecp_poblacion_provincia_historico` (56945) y
    `ine_ecp_poblacion_provincia` (59589). Calendario INE operación 450 /
    publicación 610 → la tarea diaria solo los descarga al publicarse un
    trimestre. `ine_poblacion_ccaa/provincia` pasan a `activo=False` (sus
    datos 1996–2021 se conservan). Campo nuevo `Indicador.ine_filtros`
    (`tv=356:15668` = "Todas las edades"; en provincias además
    `tv=115:7`/`115:11` = Badajoz/Cáceres), imprescindible porque sin filtro
    las tablas pesan 5–13 MB y la histórica provincial el INE no la sirve.
  - `ine_client.fetch_tabla`: parámetros extra como lista de pares (el `tv`
    se repite). `parse.py`: `T3_Periodo` solo se usa si tiene forma de código
    (la ECP trae "1 de julio de").
  - `sql/001_schema.sql`: `v_poblacion` trimestral con prioridad por fuente
    (ECP definitivo > ECP provisional > Eurostat > Padrón) y columnas nuevas
    `periodo_fecha`, `prioridad`, `indicador`; `v_analisis` toma la
    población más reciente con fecha ≤ la del periodo de la observación
    (antes ≤ año) y añade `poblacion_fecha_referencia` y `poblacion_fuente`;
    no normaliza ningún indicador de categoría `demografia`.
  - Probado en PostgreSQL de pruebas (estructura real de la ECP, definitivo
    preferido sobre provisional en la misma fecha) y **cargado en
    producción** (`carga_poblacion_ecp.bat`): 7.020 + 360 filas CCAA, 702 +
    36 provinciales (20 territorios / 2 provincias × 3 sexos × 117 y 6
    trimestres). Verificado: Extremadura 1.055.849 (1-jul-2026, provisional),
    1.053.345 (1-ene-2025, definitivo, igual que Eurostat); Badajoz 667.584;
    Cáceres 388.265; España 49.801.559. Los conteos de Extremadura ya se
    normalizan con población de 2026 (antes con la de 2021).
- **Rendimiento (pendiente):** agregar sobre toda `v_analisis` tarda ahora
  ~6 min (el cruce con la población se calcula fila a fila). No afecta a la
  ingesta; conviene resolverlo antes de la fase 4 (p.ej. vista materializada
  de población refrescada tras cada ingesta).

## 2026-09-16 (2)

- **🔴→✅ La tarea programada diaria llevaba fallando TODOS los días desde el
  2026-08-28 sin ingerir nada.** Descubierto al revisar por qué casi todos los
  indicadores tenían `naturaleza_dato` vacío en producción: `carga_log` no
  tenía ninguna carga entre el 28-ago y hoy, `schtasks` mostraba "Último
  resultado: 1" y `E:\Lab\logs\extremadura-en-datos` estaba vacía.
  Causa: `scripts/run_ingesta.ps1` usa `$ErrorActionPreference = 'Stop'`, y
  Windows PowerShell 5.1 convierte cada línea que Python escribe en stderr
  (todo el logging) en un error terminante (`NativeCommandError`): moría en
  la primera línea de log. Corregido relajando a `Continue` solo durante la
  llamada a Python y pasando cada línea a texto antes del log. Nuevo
  `probar_tarea_diaria.bat` para lanzar exactamente lo mismo que la tarea
  (salida en `_ejecucion_claude\run_ingesta.txt`).
- **Al poder ejecutarse por fin la ingesta incremental real salieron tres
  fallos más (nunca se había ejecutado de verdad en producción):**
  - `db.upsert_fechas_calendario`: el INE repite fechas de publicación en la
    misma respuesta → `CardinalityViolation` en 10 tablas (turismo, vivienda,
    hipotecas, fincas, EPA). Ahora se deduplica por fecha.
  - `calendario.refrescar_si_hace_falta`: la "red de seguridad" capturaba el
    error pero dejaba la transacción abortada, y la ingesta de esa tabla
    fallaba después (`InFailedSqlTransaction`). Ahora hace `rollback`.
  - `parse.py`: las tablas CRE devuelven en incremental años a secas
    (`"2022"`), que no se reconocían (5.180 avisos). Añadido ese formato.
  Tests nuevos: `test_formato_nombreperiodo_anyo_sin_letra`,
  `tests/test_calendario_db.py` (19/19 OK). Probado además contra PostgreSQL
  de pruebas (fecha repetida y rollback tras error SQL).
- **✅ Ingesta incremental completa en producción (`probar_tarea_diaria.bat`,
  código de salida 0):** 11 tablas del INE con publicación pendiente
  cargadas, 13 omitidas por calendario, población (tablas 2853/2852) cargada
  por primera vez, los 9 indicadores de Eurostat omitidos correctamente por
  no haber cambiado en origen.
- **Corregido `v_analisis.naturaleza_dato_efectiva`:** ahora detecta
  variaciones/tasas en el valor de cualquier dimensión de la serie (el nombre
  de la dimensión varía por tabla: "Índices y Tasas", "Índice y tasas",
  "Tipo de dato", "magnitud"), no solo en `observacion.tipo_dato` (que en el
  INE es "Definitivo"/"Provisional"). Verificado en producción: en el IPC,
  223.956 observaciones de variación pasan a `tasa` y 74.880 de índice
  siguen como `indice`; lo mismo en IPI, IPV, ICN y CRE.
- Verificado también en producción: `naturaleza_dato` sincronizado en los 26
  indicadores del INE; `v_poblacion` devuelve datos (Extremadura 1.059.501
  en 2021) y `valor_por_1000_habitantes` se calcula para los conteos.
  **Límite detectado:** las tablas de población del INE solo llegan a 2021,
  así que la normalización de años posteriores usa la población de 2021.
- Nuevo `scripts/verificar_naturaleza.py` (+ `verificar_naturaleza.bat`):
  resumen de naturaleza por indicador, población y normalización. Scripts de
  diagnóstico puntuales de hoy movidos a `_to_delete/`.
- Nota de rendimiento: consultas agregadas sobre toda `v_analisis` (1,5 M de
  filas) tardan ~2 minutos → la capa de análisis (fase 4) no debe consultarla
  entera en cada ejecución.

## 2026-09-16

- **✅ Fase 1 (Eurostat NUTS2) confirmada en producción.** `carga_eurostat.bat`
  lanzado en el PC (Computer Use): esquema aplicado, 9/9 indicadores
  cargados sin errores en ~1 minuto — **327.403 observaciones** (PIB 20.113,
  VAB por ramas 100.714, paro 36.415, empleo 21.109, ocupados 50.906, I+D
  53.593, población 9.106, renta hogares 12.082, ganadería 23.365). Repetido
  a continuación: mismos recuentos (idempotente). Total en la base: 1.485.844
  observaciones (INE sin cambios, 1.158.441).
- Incidencia menor durante la ejecución: un doble clic mal situado lanzó
  `exportar_analisis.bat` (solo lectura de la base; regeneró
  `_ejecucion_claude/observaciones.csv` e `indicadores.csv`, carpeta de
  trabajo excluida de Git). Sin efecto en los datos.

## 2026-09-15 (3)

- **Fase 0 cerrada** con decisiones del usuario: embalses y extracción de
  PDF/OCR de la Lonja de Salamanca aplazados; Lonja de Extremadura
  descartada (requiere registro) — los precios locales vendrán del
  Observatorio de Precios de la Junta y del portal Agri-food de la Comisión.
- **Fase 1: ingesta de Eurostat (comparativa NUTS2 europea).**
  - Esquema: fuente `eurostat`, `territorio.codigo_nuts` (CCAA españolas
    enlazadas a su NUTS2, Badajoz/Cáceres a su NUTS3), niveles `nuts2` y
    `agregado` (UE-27), `indicador.origen_actualizado`.
  - Nuevos `eurostat_client.py`, `eurostat_parse.py` (JSON-stat disperso,
    flags, confidencial como secreto, selección de territorios UE-27) y
    `eurostat_ingest.py` (histórico completo / incremental por fecha
    `updated`, últimos 6 años).
  - `ingest.py`: reparto por fuente, opción `--fuente`, `rollback` tras error
    inesperado. `db.py`: indicador por fuente y alta automática de países y
    regiones NUTS2. `parse.py`: campo opcional `territorio_nombre_origen`.
    `config.py` / `.env.example`: variables `EUROSTAT_*` opcionales.
  - `indicadores.py`: campos `fuente` y `eurostat_filtros`; 9 indicadores
    Eurostat. Catálogo total: 35 indicadores (26 INE + 9 Eurostat).
  - Tests: `tests/test_eurostat_parse.py` + `tests/fixtures/` (JSON real
    capturado); 17/17 tests OK. Integración en PostgreSQL 16 de pruebas:
    esquema aplicado dos veces sobre el esquema de producción con datos INE,
    carga Eurostat idempotente, INE y Eurostat en el mismo territorio,
    modo incremental simulado.
  - `carga_eurostat.bat`: carga histórica de Eurostat + verificación con
    doble clic. **Pendiente:** ejecutarla en producción.
- **Hallazgo (sin corregir):** `v_analisis.naturaleza_dato_efectiva` no
  detecta las series de variación del INE (mira `observacion.tipo_dato`, que
  trae "Definitivo"/"Provisional"; el tipo real está en `serie.atributos`).

## 2026-09-15 (2)

- **Fase 0 de la ampliación NUTS2/agro: verificación de fuentes (sin cambios
  de código ni de base de datos).** Llamadas reales desde el navegador del PC
  de producción. Nuevo `docs/fuentes-europa-agro.md` con el detalle:
  - Eurostat JSON-stat verificado (10 datasets, valores reales de ES43/ES/UE27);
    `lfst_r_lfe2act` y `agr_r_animal` (citados en el documento de origen) dan
    404 → sustituidos; límite de extracción de 5M celdas.
  - Portal Agri-food DG AGRI verificado (`api.tech.ec.europa.eu/agrifood`):
    porcino, vacuno, ovino, cereales y aceite (con mercado **Badajoz**),
    leche y fertilizantes; precios como texto con coma/punto decimal
    inconsistente.
  - FAO (CSV) verificado; Pink Sheet y `BD-Embalses.zip` de MITECO
    localizados (formato interno pendiente).
  - Precios locales: Observatorio de Precios de la Junta de Extremadura
    (CSV por provincia), Lonja de Salamanca (datos abiertos CC-BY, incluye
    ibérico, solo últimas ~5 semanas), MAPA precios medios (XLSX). La Lonja
    de Extremadura exige usuario registrado.
  - `docs/ampliacion-nuts2-agro.md`: estado de fase 0 y registro de avances
    actualizados.

## 2026-09-15

- **Documentado (solo documentación, nada implementado): plan de ampliación
  con comparativa NUTS2 europea y sector agropecuario.** A partir del
  documento de investigación aportado por el usuario se acordaron alcance
  (fases 0–4, web fuera), comparación contra todas las NUTS2 de la UE,
  fuentes de mercado solo gratuitas/oficiales, lonjas con descarga diaria y
  extracción local (OCR para PDF escaneados) y comparativa europea también
  en precios agrarios. Nuevo documento vivo de seguimiento
  `docs/ampliacion-nuts2-agro.md` (decisiones, fuentes, diseño de lonjas,
  cambios de modelo previstos, estado por fase y registro de avances).
  `PROJECT.md` §4 y §17 y `README.md` enlazan a él.

## 2026-08-28 (10)

- **Documentado (solo documentación, nada implementado): plan de arquitectura
  de tres capas para la futura web.** El usuario decidió que, antes de
  construir la web, habrá un script Python (pandas) de análisis de tendencia
  que se ejecuta cada vez que se actualiza la base de datos y guarda su
  resultado en una tabla propia; la web se construirá solo sobre esa tabla,
  nunca directamente sobre `v_analisis`/`observacion`. Ver PROJECT.md §4
  (diagrama actualizado) y §17 para el detalle completo y lo que queda por
  decidir (punto de enganche al pipeline, alcance exacto del análisis,
  nombre de la tabla de salida, stack de la web). No empezar a implementarlo
  sin retomarlo explícitamente.

## 2026-08-28 (9)

- **Catálogo ampliado a 26 tablas (demografía) + naturaleza del dato +
  normalización por población + vista `v_analisis`.** Tras explicar en
  detalle qué mide cada tabla y cómo interpretarla estadísticamente, se
  implementó "todo lo necesario para tener el dato correcto":
  - Dos indicadores nuevos: `ine_poblacion_ccaa` (tabla 2853) e
    `ine_poblacion_provincia` (tabla 2852) — población por CCAA/provincia y
    sexo (serie DPOP del Padrón municipal). Localizadas vía datos.gob.es;
    **la forma exacta de la respuesta no se ha podido verificar contra la
    API real desde este entorno** (sin acceso de red) — pendiente de
    confirmar en la primera ingesta real.
  - `indicador.naturaleza_dato` (columna nueva, con CHECK): clasifica cada
    tabla por defecto como `indice` / `tasa` / `conteo` / `monetario` /
    `promedio`. Rellenada para las 26 tablas del catálogo.
  - `v_poblacion`: población de referencia por territorio y año.
  - `v_analisis`: vista nueva para consultar de aquí en adelante — excluye el
    secreto estadístico por defecto, corrige la naturaleza del dato por
    observación (no solo por tabla, para casos como el IPC que mezcla índice
    y variación), y añade `valor_por_1000_habitantes` para los conteos
    absolutos, usando la población más reciente conocida de cada territorio.
  Validado con datos sintéticos en un PostgreSQL de prueba (esquema
  idempotente, clasificación índice/tasa correcta dentro de una misma tabla,
  secreto excluido, normalización per cápita verificada con dos territorios
  de tamaño muy distinto). Se activa solo en la próxima ejecución de la tarea
  programada diaria, sin pasos manuales.

## 2026-08-28 (8)

- **El calendario oficial de publicaciones del INE gobierna ahora la ingesta
  diaria.** Sustituye a la decisión "llamar siempre, el upsert es
  idempotente" (ver §17 de PROJECT.md). Se descubrió que
  `SERIES_TABLA/{tabla_id_externo}` ya trae `FK_Operacion`/`FK_Publicacion`
  por serie (no hizo falta el rodeo por `SERIE/{id}?det=2` que se había
  planeado inicialmente, verificado que no devuelve esos campos). Con eso:
  - `indicadores.py`: `Indicador` añade `ine_operacion_id` /
    `ine_publicacion_id`, mapeados para las 24 tablas del catálogo (las 2
    tablas CRE se quedan sin `ine_publicacion_id` en el catálogo — se
    autodescubre en tiempo de ejecución).
  - `sql/001_schema.sql`: columnas nuevas en `indicador` y tabla nueva
    `calendario_publicacion` (fechas de publicación por indicador, con
    `procesada`).
  - Módulo nuevo `src/extremadura_datos/calendario.py`: `debe_ingerir_hoy()`
    / `marcar_procesado()`, con refresco cada 3 días y red de seguridad
    (nunca deja de ingerir por falta de datos de calendario o fallo de red).
  - `ingest.py` (`--modo incremental`): consulta el calendario antes de cada
    llamada real a la API y se salta las tablas sin publicación pendiente.
  Validado en un PostgreSQL de prueba en el entorno cloud: esquema idempotente
  (aplicado dos veces sin cambios) y lógica de gobernanza probada con un
  cliente HTTP simulado (fallo de red → se ingiere igual; fecha vencida sin
  procesar → se ingiere y se marca; sin fecha vencida → se salta;
  autodescubrimiento del `ine_publicacion_id` de las tablas CRE → funciona y
  persiste). Se despliega solo con los archivos actualizados en el PC — no
  hizo falta ningún script manual ni Computer Use: `ensure_schema()` reaplica
  el esquema en cada arranque de `ingest.py`, así que se activa en la
  siguiente ejecución de la tarea programada diaria.
- Limpieza: se retiran de la carpeta del proyecto los scripts de
  investigación puntual usados para este descubrimiento
  (`investigar_calendario_ine.py`, `mapear_calendario_ine.py` y sus `.bat`) —
  ya cumplieron su función y su lógica quedó incorporada de forma permanente
  en `calendario.py`.

## 2026-08-28 (7)

- **Ampliación del modelo de datos: todas las CCAA + total nacional, para
  poder comparar Extremadura con el resto de España.** El usuario aclaró el
  objetivo final del proyecto: una web de análisis propia, actualizada cada
  día, que compare Extremadura con el resto de España — no solo un
  informe puntual. Eso exige tener el dato de las demás CCAA y el total
  nacional guardado en la base de datos (no pedirlo en vivo a la API cada
  vez, que es lo que se hizo para el informe exploratorio de hoy).
  Cambios:
  - `sql/001_schema.sql`: +18 filas en `territorio` (resto de CCAA y
    ciudades autónomas, `codigo_ine` oficial del INE, `padre_id` = España).
  - `parse.py`: `VARIABLES_TERRITORIALES` reconoce ahora
    `"Totales Territoriales"` y `"Total Nacional"` como dimensión
    territorial (antes esa fila se descartaba siempre, ver nota en el
    propio archivo).
  - `db.py`: `TERRITORIO_CLAVE_A_NOMBRE` ampliado (18 CCAA + "nacional"/
    "total nacional" → España).
  - `indicadores.py`: `_TODAS_CCAA` / `_TODAS_CCAA_Y_PROVINCIA` nuevas;
    los 19 indicadores de ámbito CCAA (de los 23 activos) las usan ya en
    vez de `_CCAA`/`_CCAA_Y_PROVINCIA`. Los 4 indicadores exclusivamente
    provinciales quedan igual (decisión explícita del usuario — esas tablas
    del INE no traen desglose por CCAA).
  - Validado en un PostgreSQL de prueba en el entorno cloud (esquema
    aplicado dos veces sin duplicar filas; tabla real 8027 parseada e
    insertada con upsert idempotente, capturando 17 CCAA + España). No se
    ha tocado la base de datos de producción en esta prueba.
  - **Pendiente:** relanzar `ingest.py --modo historico` en el PC real
    (con Computer Use) para descargar el histórico completo con el nuevo
    alcance (todas las CCAA) y cargarlo en `extremadura_en_datos`. El script
    (`reingesta_ccaa.bat`) ya está preparado en la raíz del proyecto; solo
    falta poder controlar el PC (estaba bloqueado en el momento de escribir
    esto).

- **✅ Confirmado en producción.** Se relanzó `ingest.py --modo historico`
  en el PC real (Computer Use, `reingesta_ccaa.bat`) tras aplicar los
  cambios anteriores. Terminó sin errores (estado 0, sin excepciones en el
  log). Resultado real en `extremadura_en_datos`: de 72.012 a **1.158.441
  observaciones** (6.729 series, 22 territorios), ningún indicador activo a
  0 filas. La fila nacional (`España`) por sí sola aporta 71.332
  observaciones. Ya se puede comparar Extremadura contra cualquier CCAA o
  contra el total nacional directamente con SQL, sin llamar a la API del
  INE en cada consulta.

## 2026-08-28 (6)

- **Informe descriptivo puntual: Extremadura vs resto de España.** El usuario
  pidió explorar los datos con foco en la comparativa regional. La base de
  datos solo guarda Extremadura/Badajoz/Cáceres (por diseño), así que para
  comparar con el resto de CCAA se añadieron dos scripts de uso puntual (no
  tocan el pipeline de producción ni el esquema):
  - `scripts/exportar_analisis.py` — vuelca `observacion`/`indicador` a CSV
    para analizarlos fuera de Postgres.
  - `scripts/fetch_comparativa_nacional.py` — consulta en vivo la API del
    INE (7 tablas insignia: IPC, paro EPA, IPI, viajeros, IPV, sociedades
    mercantiles, confianza empresarial) para tener el dato nacional y de
    todas las CCAA del último periodo, ya que eso no se guarda en la base de
    datos. Solo lectura, sin credenciales, mismo `IneClient` de producción.
  Con esos datos se generó un informe HTML de un solo archivo (gráficas de
  evolución de Extremadura + comparativa Extremadura/Nacional/ranking de
  CCAA), guardado en `_analisis/` (excluido de Git, es un artefacto
  generado, no código) y entregado al usuario. `_analisis/` añadida a
  `.gitignore`.

## 2026-08-28 (5)

- **Auditoría de documentación tras la carga real: 3 huecos encontrados y
  corregidos.** El usuario pidió comprobar que todo quedaba bien
  documentado tras la carga histórica real. Se encontró: (1) `PROJECT.md`
  §1 seguía diciendo `Estado: Development` pese a tener datos reales en
  producción — corregido a `Production`; (2) los scripts nuevos
  `scripts/reporte_estructura.py` (informe de estructura y volumen de
  datos, usado para responder al usuario cuántos datos hay de cada tipo) y
  `reporte_estructura.bat` (lanzador sin interacción, mismo patrón que
  `ejecutar_todo.bat`) estaban en el PC pero sin commitear ni mencionados
  en ningún sitio — documentados en `README.md` y `PROJECT.md` §12, y
  commiteados; (3) `README.md` tenía datos obsoletos de antes de la
  verificación completa (hablaba de "4 indicadores" y de un aviso de
  "antes de fiarte de la ingesta" que ya no aplica con el catálogo 24/24
  verificado) — actualizado, y se añadió mención a `--modo historico` y a
  cómo ver los datos con DBeaver.

- **Bug crítico real encontrado y corregido: bucle infinito en
  `IneClient.fetch_tabla()`.** Al ejecutar por primera vez la ingesta real
  contra el INE (con Computer Use, tabla `ine_ipc_ccaa`/50913 en modo
  `--modo historico`), el proceso se quedó colgado varios minutos sin
  avanzar. Causa: `fetch_tabla()` tenía una "paginación" (`page=2`,
  `page=3`...) que se disparaba si la respuesta traía 500 series o más,
  asumida sin haber sido verificada nunca contra el comportamiento real de
  la API — ni una sola de las pruebas de esta ronda de verificación pasaba
  por este cliente HTTP, todas se hicieron con JSON capturado directamente
  del navegador. La API real de `DATOS_TABLA` **no reconoce el parámetro
  `page`**: lo ignora y devuelve la respuesta completa de nuevo, así que
  `page=2` traía exactamente lo mismo que `page=1` (≥500 de nuevo) y el
  bucle no terminaba nunca — cada vuelta repitiendo la descarga completa de
  la tabla. Corregido eliminando el bucle: una única petición por tabla, ya
  que toda la verificación tabla por tabla de este proyecto confirma que el
  INE siempre devuelve todas las series de golpe (se ha visto hasta 1080 en
  una sola respuesta). Detenido el proceso colgado cerrando la consola
  (Computer Use) antes de que hiciera más peticiones de más al INE.
- **Primera ejecución real de principio a fin, con Computer Use.** Con
  permiso del usuario, se activó Computer Use y se ejecutó de verdad
  `scripts\setup.ps1` (entorno virtual, base de datos `extremadura_en_datos`
  en `officelab-postgres`, esquema, tarea programada) en
  `D:\Projects\extremadura-en-datos` — completado sin errores (aparte de un
  aviso menor de Git, ver más abajo). Se preparó `ejecutar_todo.bat` (además
  de `scripts\verificar_carga.py`) para no depender de escribir en una
  terminal: Computer Use solo puede hacer clic en ventanas de terminal, no
  teclear en ellas, así que todo el trabajo real se deja en un `.bat` que se
  lanza con doble clic desde el Explorador de archivos y vuelca su progreso
  a un archivo de log leíble desde el entorno cloud.
- **Aviso menor:** `setup.ps1` da por hecho que `git commit` funciona sin
  comprobar su código de salida; en este PC, sin `user.name`/`user.email`
  configurados globalmente, el commit falló pero el script siguió como si
  hubiera ido bien (imprime "[OK] Repositorio Git creado..." de todas
  formas). No bloquea nada funcional del proyecto (Git es solo control de
  versiones del código, no de los datos), pero queda pendiente arreglarlo
  en `setup.ps1` (comprobar `$LASTEXITCODE` tras `git commit`) y configurar
  la identidad de Git en este PC.

- **✅ Confirmado en producción: carga histórica completa real, con éxito.**
  Tras el arreglo del bucle infinito, se relanzó `ejecutar_todo.bat` y
  `ingest.py --modo historico` terminó sin errores para las 23 tablas
  activas: **72.012 observaciones** en la base de datos real
  (`extremadura_en_datos` en `officelab-postgres`), todas con datos (ninguna
  de las 23 activas quedó a 0 filas), con históricos que van desde 1999
  (`ine_turismo_viajeros_pernoctaciones_ccaa`) hasta mediados de 2026 según
  la tabla. Verificado con `scripts/verificar_carga.py` (nuevo, cuenta filas
  por indicador directamente en Postgres). Primer commit de Git también
  resuelto (faltaba `user.name`/`user.email` en este PC).

## 2026-08-28 (4)

- **Verificadas las 17 tablas restantes contra la API real — catálogo
  completo (24/24) verificado.** Con esto se cierra la ronda de
  verificación empezada en (2) y (3): las 24 tablas del catálogo se han
  descargado de verdad de `servicios.ine.es` y pasado por `parsear_tabla()`.
  Tablas de esta tanda: 13913, 13923, 26061, 26002 (ya vistas antes del
  corte), y 25992, 8027, 2074, 2942, 2940, 10839, 3204, 6149, 25171, 6147,
  6062, 6063, 75803.
- **Prueba consolidada de carga real:** las 23 tablas activas (ver más
  abajo) se han cargado juntas, dos veces seguidas, en un PostgreSQL 16 de
  prueba limpio (esquema recién aplicado) con el código real (`db.py`) —
  382 filas de observación tras la primera pasada, 382 tras la segunda
  (idempotencia confirmada: mismo recuento, mismos valores, ninguna fila
  duplicada). Es la prueba de extremo a extremo más completa hasta ahora.
- **Hallazgo real (no un bug de código): la tabla 10839 (Gasto de los
  turistas internacionales, EGATUR) no desglosa Extremadura.** Solo publica
  por CCAA las seis con más turismo internacional (Andalucía, Baleares,
  Canarias, Cataluña, C. Valenciana, Madrid); el resto va agregado en
  "Otras Comunidades Autónomas", sin desglose propio — verificado
  descargando la tabla completa y comprobando qué CCAA aparecen en
  `MetaData`. `ine_turismo_gasto_turistas_ccaa` se marca `activo=False` en
  `indicadores.py` (con el porqué en un comentario) para no reintentarla en
  vano cada día. Catálogo: 24 indicadores, 23 activos.
- **Confirmado, sin necesidad de cambios:** varias tablas nuevas usan
  etiquetas de `T3_Variable` territoriales distintas a las ya conocidas
  para el desglose nacional (`"Totales Territoriales"`, `"Total Nacional"`)
  — no afectan al filtrado porque esas etiquetas no están en
  `VARIABLES_TERRITORIALES` y la fila "Total Nacional" nunca coincide con
  el filtro por subcadena de respaldo; las CCAA/provincias reales de estas
  mismas tablas sí usan las etiquetas ya soportadas
  (`"Comunidades y Ciudades Autónomas"`, `"Provincias"`). Tampoco es un bug
  que una tabla traiga alguna serie con `"Data": []` (tabla 2942): significa
  que esa combinación concreta no tiene dato publicado para el periodo
  pedido, y simplemente no genera fila — es el comportamiento correcto.
- **Mejora de método (no de código): filtrar por JavaScript en la propia
  página del navegador antes de extraer texto.** Para tablas grandes,
  `get_page_text` con `max_chars` alto resultó poco fiable (el resultado
  variaba entre llamadas idénticas, probablemente por el árbol JSON
  colapsable de Chrome) y truncaba antes de llegar a Extremadura en el
  orden alfabético (tabla 6063). Solución: ejecutar
  `JSON.parse(document.body.innerText)` y filtrar por territorio dentro de
  la propia página (`javascript_tool`), devolviendo solo las series
  relevantes — pequeño, fiable y determinista. Recomendado para cualquier
  tabla nueva grande en el futuro, en vez de aumentar `max_chars` a ciegas.

## 2026-08-28 (3)

- **Verificadas 4 tablas más contra la API real** (13912, 2941, 77196,
  76926) — total 7 de 24. Esta vez, además de ejecutar `parsear_tabla()`,
  se cargaron de verdad en un PostgreSQL 16 de prueba con el código real
  (`db.get_or_create_indicador`, `db.upsert_observaciones`), repitiendo la
  carga para comprobar idempotencia (criterio de éxito de `PROJECT.md` §3).
  Las 7 tablas cargan y son idempotentes.
- **Bug real encontrado y corregido: `nombre_origen` no es clave fiable**
  (tabla 2941, turismo): dos series con `Nombre` y `MetaData` idénticos pero
  `COD` y valores distintos rompían la carga contra Postgres de verdad
  (`CardinalityViolation: ON CONFLICT DO UPDATE command cannot affect row a
  second time`). Arreglado con `serie.clave_natural` (columna generada =
  `codigo_origen` si existe, si no `nombre_origen`) como clave real en el
  `UNIQUE` y en el `ON CONFLICT`; la caché de `upsert_observaciones` usa la
  misma lógica. `sql/001_schema.sql` y `db.py` actualizados (con `ALTER
  TABLE`/migración idempotente para el esquema anterior).
- **Segundo formato de respuesta del INE, encontrado en las tablas CRE**
  (77196, 76926): sin `COD` ni `T3_Unidad`/`T3_Escala`/`T3_TipoDato`, y cada
  punto de `Data` trae `NombrePeriodo` (p.ej. `"2024(A)"`, `"2023(P)"`) en
  vez de `Fecha`/`Anyo`/`T3_Periodo`. `parse.py` ahora reconoce ambos
  formatos por punto (`_fecha_desde_nombre_periodo()`).
- **Corregido el id de tabla de `ine_cre_provincia`:** tenía `72946`
  (tomado del "identificador-api" de datos.gob.es), que da 404 en
  `DATOS_TABLA`. Localizado el id real (`76926`) navegando la operación de
  Contabilidad Regional de España en ine.es, y verificado contra la API.
- Tests nuevos para el formato `NombrePeriodo` (con y sin la letra "A").
  Catálogo total sigue en 24 indicadores (solo cambió el id de uno).

## 2026-08-28 (2)

- **Parseo verificado y corregido contra la API real del INE** (no solo
  documentación): se descargó JSON real de 3 tablas — 50913 (IPC, CCAA),
  3996 (EPA paro, provincia) y 6150 (Compraventa vivienda, CCAA y provincia
  mezclados) — y se ejecutó `parsear_tabla()` contra ellas. Esto reveló
  varios campos mal asumidos:
  - `Fecha` es un string ISO 8601 con offset, no epoch en milisegundos
    (`datetime.fromtimestamp` habría petado). Ahora se usa
    `datetime.fromisoformat`.
  - Unidad/escala/tipo de dato van en `T3_Unidad`/`T3_Escala`/`T3_TipoDato`
    (strings simples), no en `Unidad`/`Escala`/`TipoDato` ni como
    `{"Nombre": ...}`.
  - El territorio se resuelve ahora primero vía el array `MetaData` de cada
    serie (`T3_Variable: "Comunidades y Ciudades Autónomas"` / `"Provincias"`),
    mucho más fiable que la subcadena en `Nombre` (que se mantiene como
    respaldo si una tabla no trae MetaData reconocible).
  - `T3_Periodo` (p.ej. "M12", "T4") se usa tal cual si el INE lo da, en vez
    de derivarlo siempre de la fecha.
  - Se eliminó `FIELD_MAP` (ya no hacía falta con nombres de campo reales
    confirmados); el punto único de ajuste sigue siendo `parse.py`.
- **Nuevo:** `serie.atributos` (JSONB, con índice GIN) — guarda el resto de
  dimensiones de cada serie (rubro, sexo, tipo/régimen de vivienda...) tal y
  como las da `MetaData`, ya separadas del territorio. Permite filtrar/agrupar
  por esas dimensiones sin volver a parsear `nombre_origen`. `db.py` y
  `sql/001_schema.sql` actualizados; la columna se añade también con
  `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` por si el esquema ya estaba
  aplicado.
- **Nuevo modo de carga histórica:** `ingest.py --modo historico` pide TODO
  el histórico de cada tabla (`nult` sin límite) en vez de los últimos
  periodos; pensado para la carga inicial de cada fuente. El modo por
  defecto (`incremental`, el que usa la tarea diaria) no cambia.
- Tests (`tests/test_parse.py`) reescritos con fixtures que reproducen la
  estructura real (antes eran inventados con nombres de campo equivocados);
  añadidas pruebas para el respaldo por subcadena, para `serie.atributos`, y
  para el caso "sin match" en tablas provinciales.
- Documentación (`docs/fuentes-ine.md`, `PROJECT.md`) actualizada: ya no dice
  "no verificado contra la API real" — documenta qué se verificó, cómo, y qué
  queda pendiente (verificar las 21 tablas restantes una por una si dan
  problemas).

## 2026-08-28

- El usuario aportó `Datos_Extremadura_Mensual.xlsx` con 21 fuentes del INE
  (Precios, Industria y Empresa, Turismo, Vivienda, Empleo). Añadidas al
  catálogo (`src\extremadura_datos\indicadores.py`), sustituyendo la tabla
  72989 (EPA por provincia, provisional) por la 3996 del Excel.
- **Cambio de modelo de datos:** añadida la tabla `serie` entre `indicador` y
  `observacion` (ver `sql/001_schema.sql` y `docs\fuentes-ine.md`). Motivo:
  varias de las tablas nuevas (IPC, turismo, industria) tienen muchas series
  por territorio y periodo (por rubro, tipo de alojamiento, sector...), y el
  modelo anterior las hubiera colapsado en una sola fila. Cambio hecho
  reescribiendo el esquema directamente (el proyecto aún no se había
  desplegado, sin datos que migrar).
- Añadida vista `v_observacion` para consultar todo unido en una fila.
- `db.py`: `get_or_create_serie`, `upsert_observaciones` ahora resuelve
  serie antes de volcar. `parse.py`: captura también el código de serie del
  INE (`COD`) cuando está presente.
- Test nuevo (`test_varias_series_mismo_territorio_y_periodo_no_se_pierden`)
  que fija en la suite el caso que motivó el cambio.
- Catálogo total: 24 indicadores (antes 4).

## 2026-08-26

- Creación del proyecto. Fase 1: ingesta + base de datos (sin API todavía).
- Esquema inicial en PostgreSQL (`fuente`, `territorio`, `indicador`,
  `observacion`, `carga_log`), pensado para admitir varias fuentes.
- Ingesta de 4 tablas del INE (EPA y Contabilidad Regional de España, a nivel
  CCAA y provincial), filtradas a Extremadura/Badajoz/Cáceres.
- `scripts\setup.ps1` (entorno, base de datos, esquema, Git, tarea programada
  diaria) y `scripts\run_ingesta.ps1` (ejecución + log).
- Pendiente: el usuario ejecute `scripts\setup.ps1` en el PC y verifique con
  `inspect_table.py` que el parseo del JSON del INE coincide con la
  respuesta real (no se pudo probar en el entorno donde se generó este
  proyecto — ver `PROJECT.md` §17).
