# Web pública extremaduraendatos.com — diseño, requisitos legales y plan de trabajo

> **Documento vivo** de la fase web (capa 3). Recoge lo decidido con el
> usuario, las condiciones de uso de cada fuente, los avisos obligatorios, los
> datos que faltan y el orden de trabajo. Actualizar el **§7 Estado** y el
> **§8 Registro** en cada avance, igual que en `ampliacion-nuts2-agro.md`.
>
> **Creado:** 2026-09-16 · **Estado:** ✅ Paso 1 hecho (web provisional publicada en Vercel). Siguiente: paso 2, diseño visual.
>
> ⚠️ La revisión de licencias del §3 es una lectura de las condiciones
> publicadas por cada organismo (septiembre 2026), no asesoramiento jurídico.

---

## 1. Decisiones tomadas (2026-09-16)

| # | Decisión |
|---|---|
| W1 | **Nombre y dominio:** `extremaduraendatos.com` ("Extremadura en Datos"). |
| W2 | **Público:** general y prensa. Web **pública**, proyecto **personal y no comercial**, que se irá ampliando poco a poco. |
| W3 | **Formato:** una sola página con scroll, dividida por temáticas con **color propio**: portada · 1 El pulso (coyuntura) · 2 Extremadura en Europa · 3 Del mercado al campo (precios agrarios) · pie (método, fuentes, descargas). |
| W4 | **Textos descriptivos, no titulares de prensa.** Solo se actualizan los datos; los textos explican qué muestra cada panel y deben seguir siendo ciertos con cualquier dato nuevo (nada de "sube", "récord"… escrito a mano). Los calificativos que dependan del dato, si los hay, se generan a partir del propio dato. |
| W5 | **Cinta de últimos datos** tipo bolsa en la parte superior: último valor, variación y fecha de cada indicador clave, para que se vea que está vivo. |
| W6 | **Mapas con datos**: el usuario elige una temática/indicador y el mapa lo representa (no mapas decorativos). |
| W7 | **Estética moderna y tecnológica** (referencia visual: worldmonitor): tema oscuro, gráficos animados, 3D y movimiento, con versión ligera en móvil y respeto a "reducir movimiento". |
| W8 | **Contenido analítico** de los tres ejes: termómetro/predicción de coyuntura, grupos y convergencia europea, transmisión de precios agrarios. |
| W9 | **Documento técnico en PDF** bajo demanda/descargable, generado con los mismos resultados y fechado. |
| W10 | **Publicación en Vercel** (plan Hobby, uso personal no comercial). |

## 2. Estructura de la página

| Bloque | Color | Contenido | Pieza visual |
|---|---|---|---|
| Cinta superior | — | Últimos datos: IPC, paro, afiliación, porcino/cereal/aceite, índice FAO… con variación y fecha | Ticker desplazable |
| Portada | Oscuro neutro | Qué es el panel, cifras clave, fecha de última actualización | Globo/mapa 3D Europa → Extremadura |
| 1. El pulso | Cian | Termómetro de actividad, predicción a corto plazo con intervalo y error histórico, alertas de cambios anómalos, comparativa con CCAA | Indicador tipo radar, series animadas |
| 2. Extremadura en Europa | Violeta | Mapa NUTS2 con selector de indicador, regiones gemelas (grupos), convergencia con la UE, posición en rankings | Mapa 3D con relieve por valor (deck.gl) |
| 3. Del mercado al campo | Verde/ámbar | Precios Badajoz vs España vs UE, velocidad y asimetría de la transmisión, cadena fertilizantes → cereal → ganado, índice FAO | Arcos animados de flujo, diagrama de cadena |
| Pie | Neutro | Método en lenguaje llano, avisos, **fuentes y atribuciones**, descarga de datos y del PDF técnico | — |

## 3. Condiciones de uso de las fuentes (revisado 2026-09-16)

| Fuente | Licencia / condiciones | Atribución exigida | Riesgo para la web |
|---|---|---|---|
| **INE** | Reutilización permitida, también comercial, con condiciones propias: no desnaturalizar la información, indicar fecha de actualización, no sugerir patrocinio del INE | Datos transformados: **"Elaboración propia con datos extraídos del sitio web del INE: www.ine.es"** (sin tratar: "Fuente: Sitio web del INE: www.ine.es") | Bajo |
| **Eurostat** (datos) | **CC BY 4.0**; excepciones para datos de terceros países (fuera UE/EFTA) — no aplica, solo usamos UE | "Fuente: Eurostat" + indicar que hay cambios/tratamiento | Bajo |
| **GISCO – contornos NUTS** (para el mapa, aún no descargados) | Uso permitido **solo no comercial**; uso comercial requiere acuerdo con EuroGeographics | **"© EuroGeographics para los límites administrativos"** en la leyenda del mapa y en la página | Bajo mientras el proyecto sea no comercial (coherente con Vercel Hobby) |
| **Portal Agri-food (Comisión Europea)** | Contenido de la Comisión: **CC BY 4.0** (aviso legal general de la Comisión; el portal no publica términos propios) | "Fuente: Comisión Europea, Agri-food data portal" + indicar cambios | Bajo |
| **FAO – Food Price Index** | **CC BY 4.0** (salvo indicación en metadatos); no dar a entender respaldo de la FAO | "FAO. [año]. FAO Food Price Index. Consultado el [fecha]. [URL]. Licencia: CC-BY-4.0." | Bajo |
| **Observatorio de Precios y Mercados (Junta de Extremadura)** | **Contradictorio**: el aviso legal reserva los contenidos y limita la licencia a "descarga y uso privado" salvo autorización expresa; a la vez recoge las condiciones de reutilización de información pública de la Ley 37/2007 (no alterar, no desnaturalizar, citar fuente, fecha de actualización) | "Fuente: Observatorio de Precios y Mercados, Junta de Extremadura" + fecha de actualización | **Medio** → pedir autorización por escrito antes de publicar sus datos |
| **Seguridad Social – afiliación** (aún no incorporada) | Información del sector público; aplicar las condiciones de la Ley 37/2007 (citar fuente y fecha, no alterar) — confirmar al incorporarla | "Fuente: Seguridad Social" + fecha | Bajo |

**Consecuencias prácticas:**

1. La web tendrá una sección **"Fuentes y licencias"** con cada atribución
   literal y la fecha de última actualización de cada serie.
2. Todo lo que publiquemos es **tratado** (medias, predicciones, grupos):
   usar siempre las fórmulas de "elaboración propia con datos de…".
3. Nada de logos de INE/Eurostat/FAO/Comisión/Junta (marcas excluidas de las
   licencias).
4. **Proyecto no comercial** mientras usemos contornos GISCO y Vercel Hobby:
   sin anuncios ni patrocinios. Si cambia, revisar ambos.
5. **Observatorio de la Junta:** enviar una solicitud de autorización al
   Observatorio (correo o registro) explicando el uso (web personal no
   comercial, con cita y fecha). Hasta tener respuesta, el panel de precios
   usa las series del portal Agri-food (que incluyen los mercados de Badajoz)
   y las de la Junta quedan preparadas pero **sin publicar**.

## 4. Avisos que debe llevar la web

- **Aviso de estimaciones:** las predicciones, grupos y relaciones entre
  series son estimaciones estadísticas propias, con incertidumbre; se
  muestran siempre con su intervalo y su **error histórico medido** (qué
  habría predicho el modelo en el pasado frente a lo que ocurrió).
- **Independencia:** proyecto personal; no está respaldado ni patrocinado por
  ninguno de los organismos citados.
- **Datos provisionales y revisiones:** las fuentes revisan cifras ya
  publicadas; el panel muestra la última versión disponible y su fecha.
- **Sin garantía:** los datos se ofrecen tal cual, sin garantía de exactitud
  ni responsabilidad por el uso que se haga de ellos.
- **Privacidad y cookies:** web estática sin cookies propias. Si se añade
  analítica, usar una sin cookies (p.ej. Vercel Web Analytics) y
  mencionarlo.
- **Contacto** para correcciones (buzón genérico, no personal).

## 5. Datos que faltan para la web

| Dato | Para qué | Fuente localizada | Formato / requisito |
|---|---|---|---|
| **Afiliación a la Seguridad Social** (mensual, CCAA y provincia) | Termómetro de coyuntura (mejor indicador adelantado de actividad) | Estadísticas de la Seguridad Social (seg-social.es: afiliados medios y a último día del mes, también por municipio; publicación ~12-15 días tras el mes) | XLSX → requiere `openpyxl` en el `.venv` |
| **Contornos NUTS2** (GISCO) | Mapa europeo | Eurostat GISCO, unidades estadísticas | GeoJSON/TopoJSON, simplificado para web; atribución EuroGeographics |
| **Banco Mundial (Pink Sheet)** | Referencias mundiales de materias primas (opcional) | worldbank.org commodity markets | XLSX → requiere `openpyxl` |
| **Versiones publicadas ("vintages")** | Medir con honestidad el error de las predicciones | Guardar cada valor con su fecha de publicación en vez de sobrescribir | Cambio de modelo en la base (tabla de histórico de revisiones) |

## 6. Publicación: arquitectura y pasos

```
PC (cada noche)                                   Internet
────────────────────────────────                  ─────────────────────────────
ingest.py  →  PostgreSQL                          GitHub (repo de la web)
analisis (fase 4) → tablas de resultados   git push  │
exportar_web.py → web/data/*.json  ───────────────→   │  Vercel detecta el push,
(solo agregados; nunca la base)                       └→ construye y publica
                                                         extremaduraendatos.com
```

- **Repositorio (decidido 2026-09-16):** un único repositorio **privado** en
  GitHub (el actual `extremadura-en-datos`), con la web en `web/`. En Vercel,
  *Root Directory* = `web`; `web/vercel.json` usa `ignoreCommand` para que
  solo se reconstruya cuando cambia `web/`. `.env` y `_ejecucion_claude/`
  están en `.gitignore` (comprobado: nunca se han versionado).
- **Tecnología prevista:** Astro (sitio estático) · deck.gl + MapLibre
  (mapas 3D con datos) · three.js/globe.gl (portada) · Apache ECharts
  (gráficos) · GSAP ScrollTrigger (animación con scroll).
- **Pasos que tiene que hacer el usuario** (cuentas, pagos y contraseñas no
  los puede hacer un agente):
  1. Registrar el dominio `extremaduraendatos.com` (en Vercel Domains o en
     un registrador; si es externo, apuntar los DNS a Vercel).
  2. Crear (o usar) una cuenta de **GitHub** y crear el repositorio vacío.
  3. Crear la cuenta de **Vercel** entrando con GitHub e importar el
     repositorio (Vercel detecta Astro y construye solo).
  4. En Vercel: añadir el dominio al proyecto.
  5. En el PC: iniciar sesión en Git/GitHub una vez (Git Credential Manager o
     `gh auth login`) para que el PC pueda hacer `git push` sin intervención.
- **Comprobar en el PC:** `git`, `node`/`npm` (para construir y probar la web
  en local) y, opcional, `gh` y `vercel` CLI.

## 7. Orden de trabajo

| Paso | Qué | Depende de | Estado |
|---|---|---|---|
| 0 | Requisitos legales y avisos (este documento §3-§4) | — | ✅ |
| 0b | Solicitar autorización al Observatorio de la Junta | Usuario | ⬜ |
| 1 | Infraestructura: dominio, GitHub, Vercel, página provisional "próximamente" publicada y actualización automática por `git push` probada | Usuario (cuentas/dominio) | ✅ 2026-09-16: repositorio privado `AAlmeidaM/extremaduraendatos` (rama `main`), proyecto de Vercel con Root Directory `web`, página provisional **publicada** en la dirección `.vercel.app` del proyecto; subida con `subir_a_github.bat`. Pendiente del usuario: añadir `extremaduraendatos.com` en Settings → Domains |
| 2 | Diseño visual: paleta por bloque, tipografía, componentes (cinta, tarjetas, selector de mapa), maqueta de la página completa con datos de ejemplo | 1 | ✅ 2026-09-16: maqueta `web/maqueta/` aprobada por el usuario ("excelente diseño") |
| 3 | Exportador de datos para la web (`exportar_web.py`): JSON por bloque + cinta de últimos datos, enganchado a la ingesta nocturna y al `git push` | 1 | ✅ 2026-09-16: `scripts/exportar_web.py` → `web/datos/panel.json` + `nuts2.geojson`; `web/index.html` ya muestra datos reales; `run_ingesta.ps1` exporta y sube a GitHub si cambian los datos (pendiente de ver la primera ejecución nocturna) |
| 4 | **Bloque 3 – Del mercado al campo** con análisis real: precios Badajoz/España/UE, transmisión (cointegración/corrección del error, asimetría) con validación | 2, 3, fase 4 de análisis | ⬜ |
| 5 | Datos nuevos: `openpyxl`, afiliación Seguridad Social, contornos GISCO, histórico de revisiones | — (puede ir en paralelo a 4) | ⬜ |
| 6 | **Bloque 1 – El pulso**: termómetro de actividad, predicción con error histórico, alertas, comparativa CCAA | 5 (afiliación, revisiones) | ⬜ |
| 7 | **Bloque 2 – Extremadura en Europa**: mapa NUTS2 3D con selector, regiones gemelas, convergencia | 5 (GISCO) | ⬜ |
| 8 | PDF técnico generado automáticamente con los mismos resultados | 4, 6, 7 | ⬜ |
| 9 | Pulido: rendimiento en móvil, accesibilidad, imágenes para compartir, analítica sin cookies | 4–8 | ⬜ |

## 8. Registro de avances

- 2026-09-16 — Paso 3 (revisión) — Petición del usuario: mapa más legible y
  con dato por región, contraste de cifras, textos para público general y autoría.
  - **Mapa**: se sustituye el 3D (echarts-gl, retirado) por un mapa 2D de
    ECharts con zoom y arrastre. Colores por tramos: para indicadores con media
    UE, 4 cuartiles a cada lado de la media (azul por encima, rojo por debajo;
    en paro, al revés), pálidos junto a la media e intensos lejos de ella; sin
    media UE, 6 sextiles en azul. Al pasar el cursor: aviso con el dato y ficha
    (valor, puesto, media UE, Extremadura); al hacer clic o tocar, la región
    queda seleccionada con borde cian. Extremadura con borde blanco.
  - **Contraste de datos**: `scripts/contrastar_web.py` (+ `contrastar_web.bat`)
    vuelve a pedir cada cifra no analítica a la fuente original y la compara con
    `panel.json`: INE serie a serie por código (paro EPA Extremadura y España,
    las 20 comunidades del ranking, población ECP, pernoctaciones, compraventa,
    sociedades, hipotecas Badajoz+Cáceres), Eurostat con filtros escritos a mano
    (PIB pc frente al índice oficial PPS_HAB_EU27_2020, paro, empleo, I+D, renta,
    empleo agrario, y dos regiones de control del mapa), Agri-food (cerdo España y
    UE, cordero, aceite) y CSV de la FAO. Resultado 2026-09-16: **49 de 49
    coinciden**. Paro de España 9,87 % confirmado además con la nota de prensa
    del INE (EPA 2T 2026). Observación: el PIB pc UE=100 se calcula con PPS
    absolutos redondeados (70,4) y coincide con el índice oficial (70) al
    mostrarse sin decimales.
  - **Textos**: explicaciones reescritas en lenguaje sencillo; bajo cada
    análisis, línea "Técnica:" con el nombre del método (modelo estacional
    ingenuo con tendencia y backtesting, percentiles, distancia euclídea sobre
    puntuaciones z, convergencia beta, correlación cruzada, MCO). Textos de
    alertas del exportador simplificados ("Cae un 13,4 % respecto al año
    anterior, un cambio normal…").
  - **Autoría**: pie con "Autor: Alejandro Almeida · alejandroalmeida.es" y
    meta `author`.
- 2026-09-16 — Paso 3 — **Panel con datos reales publicado** en la raíz del
  proyecto de Vercel (`web/index.html`, aún `noindex` hasta poner el dominio).
  - `scripts/exportar_web.py` (solo lectura, sin dependencias nuevas) genera
    `web/datos/panel.json` (~210 KB) y descarga una vez los contornos GISCO
    NUTS 2 2021 1:20M a `web/datos/nuts2.geojson` (234 regiones UE27, sin
    ultraperiféricas). Carpeta `datos/` y no `data/` porque `.gitignore`
    excluye `data/`. Lanzador `exportar_web.bat`; inventario de series con
    `inventario_web.bat` → `_ejecucion_claude/inventario_web.tsv`.
  - Selección de series por las partes del nombre de origen (separadas por
    ". "), escogiendo la de más observaciones. No se exporta nada de la Junta.
  - Contenido real: cinta (11 datos), 4 KPIs, bloque 1 (pernoctaciones,
    compraventa, hipotecas —suma Badajoz+Cáceres—, sociedades; paro EPA
    Extremadura y España desde 2008; ranking CCAA; movimientos a vigilar),
    bloque 2 (6 capas del mapa: PIB pc y renta UE=100, paro, empleo, empleo
    agrario, I+D; regiones de perfil parecido; convergencia 2012–último año;
    PIB pc histórico), bloque 3 (7 productos con líneas frescas <150 días:
    cerdo, lechón, cordero, aceite virgen —con Badajoz—, AOVE, leche, añojo;
    correlación por desfases UE→España en porcino; asimetría; cadena de costes).
  - Métodos: previsión del paro = mismo trimestre del año anterior + variación
    interanual media de 4 trimestres, intervalo 80 % con errores empíricos de
    43 pruebas (error medio 1 trimestre ±1,4 p.p.); alertas = variación
    interanual fuera del 5–95 % de los 5 años previos; perfil parecido =
    distancia euclídea sobre 7 variables tipificadas (similitud 0–100 respecto
    a la distancia mediana); transmisión = correlación de cambios log semanales
    con desfase 0–8 semanas, banda 1,96/√n; asimetría = MCO sin constante de
    cambios a 4 semanas separados por signo del cambio UE.
  - Cambios de diseño frente a la maqueta por lo que hay de verdad: el porcino
    no tiene mercado de Badajoz (solo España/UE) → la línea Badajoz solo aparece
    en aceite; el IPC no se muestra (ver problemas); "población de 65+" sustituida
    por renta, empleo e I+D; transmisión mostrada como correlación por semanas;
    se añade el gráfico de PIB pc histórico frente a la UE.
  - **Actualización automática**: `run_ingesta.ps1` ejecuta el exportador tras
    la ingesta y, si `web/datos` cambia, hace commit solo de esa carpeta y
    `git push` (credenciales de Git Credential Manager del usuario). Un fallo del
    exportador no cambia el código de salida de la ingesta.
  - **Problemas de datos detectados** (a revisar en la ingesta): IPC por CCAA
    parado en dic-2025 (probable cambio de base 2025 del INE en enero de 2026 →
    tablas nuevas); IPI e ICN (industria y comercio) parados en dic-2023; EPA
    por provincia parada en 4T-2023; precios de cereales de Badajoz en Agri-food
    sin datos desde ene-2025; IPV en 4T-2025.
- 2026-09-16 — Paso 2 — Maqueta publicada en `<proyecto>.vercel.app/maqueta/`
  y revisada en navegador a 1440×900: contornos GISCO cargan sin problemas de
  CORS; corregidos solape de la cinta, serie de paro de ejemplo, encuadre de
  mapas, dispersión de convergencia (codificación x/y) y solape de etiquetas.
  Pendiente: revisión estética del usuario y prueba en móvil.
- 2026-09-16 — Paso 2 — Maqueta visual `web/maqueta/index.html` (una sola
  página, sin compilación, librerías desde jsDelivr: ECharts 5.5, echarts-gl
  2.0 para el mapa 3D, GSAP 3.12 ScrollTrigger). Contiene: cinta de últimos
  datos (pausa al pasar el ratón), portada con KPIs y mapa de Europa con arcos
  animados a las regiones gemelas, bloque 1 (tiles con minigráfica, paro con
  estimación e intervalo 80 %, alertas con icono+texto, ranking CCAA), bloque
  2 (mapa NUTS 2 en 3D con selector de 4 indicadores, gemelas, dispersión de
  convergencia), bloque 3 (precios Badajoz/España/UE con selector de producto
  y zoom, transmisión por semanas con intervalo, asimetría, cadena de costes
  animada) y pie con método, fuentes/licencias literales del §3 y avisos del §4.
  Decisiones de diseño: acentos de bloque (#22d3ee, #a78bfa, #a3e635) solo
  como identidad de sección; series de datos con paleta validada por
  `validate_palette.js` en modo oscuro sobre #0b1016 — Extremadura #dd6b20,
  España #1c9fbf, UE #9b72f0, resto #4a5a6e; mapa con rampa secuencial de un
  solo tono (violeta, más valor = más claro). Estados reservados
  (ok/atención) siempre con icono y texto. Cada gráfico tiene tooltip y botón
  "Ver tabla"; `prefers-reduced-motion` desactiva animaciones. Contornos NUTS 2
  2021 (1:20M) de GISCO leídos en tiempo de ejecución solo en la maqueta; en la
  versión final irán dentro de la web (paso 5).
- 2026-09-16 — Paso 1 — ✅ Despliegue correcto en Vercel confirmado por el
  usuario: la página provisional está publicada.
- 2026-09-16 — Paso 1 — Repositorio privado `AAlmeidaM/extremaduraendatos`
  (rama `main`) conectado y subido desde el PC (`subir_a_github.bat`, sesión de
  GitHub guardada en Git Credential Manager). Proyecto de Vercel importado con
  Root Directory `web`, sin dominio (lo añade el usuario). El primer despliegue
  se canceló por el Ignored Build Step (`HEAD^` sin cambios en `web/`);
  corregido para comparar con el último despliegue (`VERCEL_GIT_PREVIOUS_SHA`).
- 2026-09-16 — Paso 1 — Herramientas del PC comprobadas; página provisional
  y configuración de Vercel en `web/`; esperando cuenta de GitHub.
- 2026-09-16 — Diseño — Acordados nombre/dominio, público, estructura,
  estilo y alojamiento (W1–W10). Revisadas las condiciones de uso de las 7
  fuentes; definidos avisos, datos que faltan y orden de trabajo. Sin código.

## Fuentes consultadas para el §3

- INE, aviso legal y condiciones de reutilización: https://www.ine.es (Ayuda → Aviso legal)
- Eurostat, copyright notice: https://ec.europa.eu/eurostat/help/copyright-notice
- GISCO, unidades estadísticas: https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units
- Comisión Europea, aviso legal: https://commission.europa.eu/legal-notice_en
- FAO, Statistical Database Terms of Use: https://www.fao.org/contact-us/terms/db-terms-of-use/en/
- Observatorio de Precios y Mercados, aviso legal: https://observatoriopreciosymercados.juntaex.es/aviso-legal
- Seguridad Social, estadísticas de afiliación: https://www.seg-social.es
- Vercel, plan Hobby: https://vercel.com/docs/plans/hobby
