# Web pública extremaduraendatos.com — diseño, requisitos legales y plan de trabajo

> **Documento vivo** de la fase web (capa 3). Recoge lo decidido con el
> usuario, las condiciones de uso de cada fuente, los avisos obligatorios, los
> datos que faltan y el orden de trabajo. Actualizar el **§7 Estado** y el
> **§8 Registro** en cada avance, igual que en `ampliacion-nuts2-agro.md`.
>
> **Creado:** 2026-09-16 · **Estado:** 📝 Diseño acordado; requisitos legales
> revisados; sin código de la web todavía.
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
| 1 | Infraestructura: dominio, GitHub, Vercel, página provisional "próximamente" publicada y actualización automática por `git push` probada | Usuario (cuentas/dominio) + comprobar herramientas del PC | 🔄 PC comprobado (Git 2.55, Node 24.19, npm 11.17; sin `gh` ni CLI de Vercel). Página provisional `web/index.html` + `web/vercel.json` creadas. Decidido: **un solo repositorio privado** en GitHub con la web en `web/` (Root Directory en Vercel) y dominio comprado en Vercel. Falta: cuenta de GitHub y repositorio (usuario), primer `git push`, importar en Vercel y dominio |
| 2 | Diseño visual: paleta por bloque, tipografía, componentes (cinta, tarjetas, selector de mapa), maqueta de la página completa con datos de ejemplo | 1 | ⬜ |
| 3 | Exportador de datos para la web (`exportar_web.py`): JSON por bloque + cinta de últimos datos, enganchado a la ingesta nocturna y al `git push` | 1 | ⬜ |
| 4 | **Bloque 3 – Del mercado al campo** con análisis real: precios Badajoz/España/UE, transmisión (cointegración/corrección del error, asimetría) con validación | 2, 3, fase 4 de análisis | ⬜ |
| 5 | Datos nuevos: `openpyxl`, afiliación Seguridad Social, contornos GISCO, histórico de revisiones | — (puede ir en paralelo a 4) | ⬜ |
| 6 | **Bloque 1 – El pulso**: termómetro de actividad, predicción con error histórico, alertas, comparativa CCAA | 5 (afiliación, revisiones) | ⬜ |
| 7 | **Bloque 2 – Extremadura en Europa**: mapa NUTS2 3D con selector, regiones gemelas, convergencia | 5 (GISCO) | ⬜ |
| 8 | PDF técnico generado automáticamente con los mismos resultados | 4, 6, 7 | ⬜ |
| 9 | Pulido: rendimiento en móvil, accesibilidad, imágenes para compartir, analítica sin cookies | 4–8 | ⬜ |

## 8. Registro de avances

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
