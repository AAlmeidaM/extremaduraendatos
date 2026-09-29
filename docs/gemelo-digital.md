# Gemelo digital de Extremadura — diseño de la web (2026-09-29)

Replanteamiento de extremaduraendatos.com: de panel por bloques temáticos a
**gemelo digital**: una representación del estado de la economía y la sociedad
extremeña que se sincroniza cada día con las fuentes oficiales, muestra cómo se
conectan sus partes y se puede recorrer hacia atrás en el tiempo.

## 1. Decisiones (usuario, 2026-09-29)

| # | Decisión |
|---|---|
| G1 | Concepto = **sala de control por sistemas** + **grafo de flujos** + **línea de tiempo** |
| G2 | Honestidad por encima del efecto: cada sistema muestra la **fecha y la antigüedad** de su dato y se marca cuando una serie está parada. Nada de simular tiempo real |
| G3 | Sin datos municipales por ahora: territorio = Extremadura, Badajoz, Cáceres y las regiones NUTS 2 de la UE |
| G4 | El simulador de escenarios (what-if) queda para una fase posterior, cuando las relaciones estén medidas y validadas |

## 2. Qué significa aquí "gemelo digital"

No es una maqueta física ni tiempo real: es un **modelo vivo del estado** de la
región, con tres propiedades que sí podemos sostener con datos oficiales:

1. **Sincronización**: cada sistema se actualiza cuando su fuente publica, y la
   web dice cuándo fue (13:00 diarias, ver `run_ingesta.ps1`).
2. **Estado**: cada sistema tiene una lectura (normal / fuera de lo habitual)
   calculada contra su propio comportamiento de los últimos cinco años.
3. **Estructura**: las partes están conectadas entre sí por relaciones medidas
   (transmisión de precios, correlaciones con desfase) o contables
   (VAB → PIB), y se ve cuál es cuál.

## 3. Sistemas vitales (8)

Cada uno con: valor principal, estado, antigüedad del dato, serie histórica,
comparación con España y/o UE, y las series secundarias al desplegar.

| Sistema | Indicador principal | Secundarios | Frecuencia |
|---|---|---|---|
| Empleo | Tasa de paro EPA | paro por sexo y edad, coste laboral, horas trabajadas, ocupados por ramas (Eurostat) | trimestral |
| Población | Población ECP | por sexo, Badajoz/Cáceres, crecimiento 10 años, comparación UE | trimestral |
| Turismo | Pernoctaciones | viajeros, extranjeros, estancia media, plazas y establecimientos | mensual |
| Vivienda | Compraventas | hipotecas (número e importe), IPV, fincas rústicas | mensual/trimestral |
| Empresas | Sociedades creadas | disueltas, capital, confianza empresarial | mensual/trimestral |
| Campo | Precio del cerdo y del aceite | cereales, cordero, añojo, leche, índice FAO, ganadería (Eurostat) | semanal/mensual |
| Economía | PIB por habitante (PPA) | VAB por ramas, renta de los hogares, convergencia con la UE | anual |
| Conocimiento | Gasto en I+D (% PIB) | por sectores de ejecución, comparación UE | anual |

**Estado de un sistema**: percentil de la variación interanual del indicador
principal frente a las de los cinco años anteriores. Dentro del 5–95 % =
normal; fuera = atención. Se muestra siempre el número, no solo el color, y el
color va acompañado de icono y texto.

**Frescura**: días desde el último dato, con umbral por frecuencia
(semanal 30, mensual 100, trimestral 200, anual 900). Por encima, ⚠ "serie sin
actualizar" — el mismo criterio que los avisos de Telegram.

## 4. Grafo del sistema (pieza central)

Nodos: Mercados UE · Campo extremeño · Empresas · Empleo · Hogares · Turismo ·
Vivienda · Europa (posición relativa).

Aristas, solo las que podamos justificar, con etiqueta de tipo:
- **medida**: precio UE → precio España (correlación por desfase, ya calculada);
  turismo → empleo; empleo → compraventa de viviendas (correlación con desfase
  a estimar, con su intervalo).
- **contable**: VAB por ramas → PIB; población → PIB por habitante.
- **de contexto**: índice FAO y fertilizantes → precios agrarios.

Cada arista muestra fuerza y desfase al pasarle el cursor, y enlaza al gráfico
que lo demuestra. Las relaciones no medidas no se dibujan.

## 5. Línea de tiempo

Barra única (2010 → hoy) que fija una fecha de referencia: los sistemas muestran
el dato vigente en ese momento y el grafo su estado. Con reproducción
automática y botón "ahora". Para que el estado pasado tenga sentido, el
exportador calcula una **serie mensual de estado por sistema** (tipificación de
su indicador principal), no solo el último valor.

## 6. Cambios en los datos exportados

`scripts/exportar_web.py` v2 añade a `panel.json`:
- `sistemas`: por sistema, indicador principal y secundarios, serie completa,
  estado actual, serie mensual de estado, frescura, fuente y periodicidad.
- `relaciones`: aristas del grafo con tipo, fuerza, desfase, intervalo y
  gráfico de apoyo.
- `tiempo`: rejilla mensual común 2010→hoy para la línea de tiempo.
Se mantienen `cinta`, `kpis` y el bloque europeo (mapa, gemelas, convergencia).

## 7. Orden de trabajo

| Paso | Qué | Estado |
|---|---|---|
| D1 | Este documento | ✅ 2026-09-29 |
| D2 | Exportador v2 (`sistemas`, `relaciones`, `tiempo`) + contraste | 🔄 2026-09-29: `scripts/gemelo.py` escrito y probado con datos simulados (8 sistemas, 5 relaciones medidas + 4 contables, ~217 KB añadidos a panel.json); pendiente la primera ejecución real |
| D3 | Página del gemelo en `web/gemelo/` (sala de control + estado + frescura) | 🔄 2026-09-29: escrita; pendiente de ver con datos reales |
| D4 | Grafo del sistema con las relaciones medidas | 🔄 2026-09-29: incluido en la página (ECharts graph, posiciones fijas, aristas medidas y contables) |
| D5 | Línea de tiempo sincronizada | 🔄 2026-09-29: barra mensual 2010→hoy con reproducción; mueve tarjetas, detalle y grafo |
| D6 | Revisión del usuario y sustitución de la portada actual | ⬜ |
| D7 | Fase posterior: simulador de escenarios; datos municipales (SEPE, padrón) | ⬜ |

## 8. Registro

- 2026-09-29 — Implementación D2-D5. `scripts/gemelo.py` (nuevo) construye la
  sección `gemelo` de `panel.json`: 8 sistemas con indicador principal,
  secundarios, estado (percentil de la variación interanual), estado mes a mes
  para la línea de tiempo y frescura; relaciones del grafo (correlación con
  desfase de 0 a 12 meses, solo si supera 1,96/√n) y nodos con posición fija.
  `web/gemelo/index.html`: tarjetas con anillo de estado, detalle con
  comparación España/UE, grafo interactivo y barra de tiempo con reproducción.
  Probado con datos simulados; **pendiente de ejecutar contra la base real**
  (el PC estaba bloqueado): la tarea de las 13:00 regenera `panel.json` y lo
  sube sola.
- 2026-09-29 — Decisiones G1–G4 y diseño inicial. Sin código todavía.
