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
| D2 | Exportador v2 (`sistemas`, `relaciones`, `tiempo`) + contraste | ✅ 2026-09-29: ejecutado contra la base real; panel.json 490 KB |
| D3 | Página del gemelo en `web/gemelo/` (sala de control + estado + frescura) | ✅ 2026-09-29: publicado en /gemelo/ y revisado en navegador |
| D4 | Grafo del sistema con las relaciones medidas | ✅ 2026-09-29: 5 relaciones medidas y 4 contables |
| D5 | Línea de tiempo sincronizada | ✅ 2026-09-29: comprobada (enero 2020 devuelve el estado de entonces) |
| D6 | Revisión del usuario y sustitución de la portada actual | 🔄 pendiente de tu revisión; el panel clásico enlaza ya al gemelo |
| D7 | Fase posterior: simulador de escenarios; datos municipales (SEPE, padrón) | ⬜ |

## 7b. Criterio de normalidad (revisado 2026-09-29)

Qué se mira, exactamente, para decir si un sistema está «dentro de lo habitual»:

1. **Qué se compara.** El último dato frente al mismo periodo del año anterior
   (variación interanual). Así se neutraliza la estacionalidad sin desestacionalizar.
2. **A qué frecuencia.** La propia de cada serie: semanal en precios, mensual en
   turismo, vivienda y empresas, trimestral en paro y población, anual en economía
   y conocimiento. *(Antes se hacía sobre una rejilla mensual, lo que repetía cada
   dato trimestral 3 veces y cada anual 12: la muestra parecía de 60 cuando en
   realidad eran 20 o 5.)*
3. **Contra qué referencia.** Las variaciones interanuales del mismo indicador en
   los 5 años anteriores (10 años en las series anuales), **excluyendo** las
   comparaciones cuya base cae entre marzo de 2020 y junio de 2021: son rebotes
   mecánicos de la pandemia. Sin esa exclusión, el rango «habitual» de
   pernoctaciones llegaba a +164 %; con ella queda en +15,7 %.
4. **Dos condiciones, no una.**
   - *Posición*: percentil del dato dentro de esa referencia (con reparto de
     empates), fuera del 5 % inferior o superior.
   - *Distancia*: z robusto = (valor − mediana) / (1,4826 × desviación absoluta
     mediana), al menos 2 en valor absoluto.
   Ambas → **fuera de lo habitual**. Solo una → **en el borde**. Ninguna →
   **dentro de lo habitual**.
5. **Muestra mínima.** 104 comparaciones semanales, 36 mensuales, 12 trimestrales
   u 8 anuales. Por debajo, **sin referencia**: no se pinta un estado falso.
6. **Contexto de nivel.** Además del cambio, se guarda en qué percentil está el
   *nivel* actual dentro de sus diez últimos años (solo informativo).
7. **Frescura.** Días desde que terminó el periodo del dato (no desde su inicio),
   con plazos de 21 / 75 / 150 / 1.100 días según periodicidad.

Lo que el criterio **no** hace: no dice si el cambio es bueno o malo, no corrige
cambios metodológicos ni revisiones posteriores de las fuentes, y no detecta
anomalías de nivel (solo de cambio). El mismo criterio se usa ya en «Movimientos
a vigilar» del panel clásico.

## 8. Registro

- 2026-09-29 (revisión del criterio) — Auditados los ocho sistemas contra los
  datos reales. Problemas encontrados y corregidos: (a) la muestra estaba
  inflada por la rejilla mensual (trimestral 189 «observaciones» cuando eran 20;
  anual 189 cuando eran 5); (b) los precios semanales perdían 3 de cada 4 semanas
  al pasar por esa rejilla (percentil 0,27 frente a 0,19 real); (c) el rango
  habitual incluía los rebotes de la pandemia; (d) un percentil extremo bastaba
  para marcar alarma aunque el movimiento fuera diminuto; (e) empates tratados
  como estrictamente menores; (f) series anuales evaluadas con 5 comparaciones.
  Resultado con el criterio nuevo: 7 sistemas dentro de lo habitual y Población
  «en el borde» (crece 0,2 %, lo más alto de los últimos 5 años, pero a 1,8
  desviaciones). Hay un tercer estado, «en el borde», y un cuarto, «sin
  referencia». Pendiente: la serie de población ECP solo deja evaluar desde 2021
  (histórico corto en la base) y el panel clásico comparte ya el mismo criterio.
- 2026-09-29 (tarde) — **Gemelo publicado en `/gemelo/` con datos reales.**
  Estado actual: 7 de 8 sistemas dentro de lo habitual; Población marcada
  fuera de lo habitual porque su crecimiento interanual (+0,2 %) es el mayor
  de los últimos cinco años. Relaciones medidas que superan el umbral:
  UE→campo (0,78, sin retraso), FAO→campo (0,27 a 6 meses), turismo→empleo
  (−0,18), empleo→vivienda (−0,26) y población→vivienda (−0,27); más cuatro
  contables. Correcciones tras la primera ejecución: la población usa también
  la serie histórica de la ECP (antes no tenía referencia), la frescura se
  mide desde el **fin del periodo** y no desde su fecha de inicio (plazos:
  21/75/150/1100 días), y se corrigieron separación de unidades y miles.
  Línea de tiempo comprobada: en enero de 2020 muestra paro 23,59 % y
  1.064.970 habitantes.
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
