# CHANGELOG — Extremadura en Datos

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
