-- =============================================================================
--  extremadura-en-datos · Esquema inicial
--  Se aplica automaticamente al arrancar (ver src/extremadura_datos/db.py,
--  funcion ensure_schema). Escrito para poder ejecutarse repetidas veces sin
--  romper nada: todo IF NOT EXISTS / ON CONFLICT DO NOTHING.
-- =============================================================================

-- Fuentes de datos (INE, y en el futuro otras: Eurostat, Junta de Extremadura...)
CREATE TABLE IF NOT EXISTS fuente (
    id SERIAL PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    url_base TEXT
);

-- Jerarquia territorial: pais -> ccaa -> provincia
CREATE TABLE IF NOT EXISTS territorio (
    id SERIAL PRIMARY KEY,
    nivel TEXT NOT NULL CHECK (nivel IN ('pais', 'ccaa', 'provincia')),
    codigo_ine TEXT,
    nombre TEXT NOT NULL,
    padre_id INTEGER REFERENCES territorio(id),
    UNIQUE (nivel, nombre)
);

-- Un "indicador" = una tabla concreta de una fuente (p.ej. tabla INE 50913,
-- el IPC por CCAA). Una tabla del INE casi siempre contiene MUCHAS series
-- (territorio x rubro x tipo de dato...), no una sola por territorio+periodo
-- — de ahi que haga falta el nivel `serie` de abajo.
CREATE TABLE IF NOT EXISTS indicador (
    id SERIAL PRIMARY KEY,
    fuente_id INTEGER NOT NULL REFERENCES fuente(id),
    tabla_id_externo TEXT NOT NULL,      -- id de tabla en la fuente (p.ej. "50913")
    codigo TEXT NOT NULL UNIQUE,          -- slug interno (p.ej. "ine_ipc_ccaa")
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,              -- 'precios' | 'turismo' | 'empleo' | ...
    -- 'pais' | 'ccaa' | 'provincia' | 'ccaa_y_provincia' (algunas tablas del
    -- INE traen ambos niveles mezclados en la misma respuesta)
    nivel_territorial TEXT NOT NULL
        CHECK (nivel_territorial IN ('pais', 'ccaa', 'provincia', 'ccaa_y_provincia')),
    periodicidad TEXT NOT NULL,           -- 'trimestral' | 'anual' | 'mensual'
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (fuente_id, tabla_id_externo)
);

-- Una "serie" = una combinacion concreta de dimensiones dentro de una tabla:
-- territorio + todo lo demas que la distinga (rubro, tipo de alojamiento,
-- sector de actividad, sexo...). El INE mete toda esa informacion en el
-- nombre de la serie (`Nombre`), asi que se guarda tal cual en
-- `nombre_origen`, y si el INE la da (casi siempre) tambien su propio
-- codigo de serie en `codigo_origen` (p.ej. "IPC256217").
--
-- ⚠️ IMPORTANTE (encontrado ejecutando esto contra datos reales, 2026-08-28,
-- tabla 2941 "Viajeros/pernoctaciones por tipo de alojamiento"): `nombre_origen`
-- NO es fiable como clave natural. Esa tabla trae dos series con `Nombre` Y
-- `MetaData` IDENTICOS ("Extremadura. Viajeros. Total.") pero `COD` y valores
-- distintos (EOT1715 vs EOT795) -- un duplicado real del propio INE. Usar
-- nombre_origen como clave (version anterior de este esquema) provoca
-- "ON CONFLICT DO UPDATE command cannot affect row a second time" al cargar
-- esta tabla (reproducido contra Postgres real). Por eso la clave natural es
-- `clave_natural` (columna generada = codigo_origen si lo hay, si no
-- nombre_origen) -- el COD de serie del INE es su propio identificador unico,
-- mucho mas fiable que el nombre.
--
-- `atributos` (JSONB): el resto de dimensiones de la serie tal y como las da
-- el array MetaData de la respuesta real del INE una vez quitado el
-- territorio -- p.ej. {"Tipo de dato": {"nombre": "Variacion mensual",
-- "codigo": "3"}, "Sexo": {...}}. Permite filtrar/agrupar por esas
-- dimensiones sin volver a parsear nombre_origen. Ver
-- src/extremadura_datos/parse.py.
CREATE TABLE IF NOT EXISTS serie (
    id BIGSERIAL PRIMARY KEY,
    indicador_id INTEGER NOT NULL REFERENCES indicador(id),
    territorio_id INTEGER NOT NULL REFERENCES territorio(id),
    codigo_origen TEXT,
    nombre_origen TEXT NOT NULL,
    atributos JSONB NOT NULL DEFAULT '{}'::jsonb,
    primera_vez_visto TIMESTAMPTZ NOT NULL DEFAULT now(),
    clave_natural TEXT GENERATED ALWAYS AS (COALESCE(codigo_origen, nombre_origen)) STORED,
    UNIQUE (indicador_id, clave_natural)
);

CREATE INDEX IF NOT EXISTS idx_serie_indicador  ON serie(indicador_id);
CREATE INDEX IF NOT EXISTS idx_serie_territorio ON serie(territorio_id);
CREATE INDEX IF NOT EXISTS idx_serie_atributos  ON serie USING GIN (atributos);

-- Si el esquema ya estaba aplicado de una version anterior (sin estas
-- columnas), esto las añade sin romper nada (idempotente). El ALTER de
-- clave_natural y su UNIQUE se hacen aparte porque ADD COLUMN no admite
-- GENERATED ALWAYS AS condicionalmente en una sola sentencia idempotente.
ALTER TABLE serie ADD COLUMN IF NOT EXISTS atributos JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'serie' AND column_name = 'clave_natural'
    ) THEN
        ALTER TABLE serie ADD COLUMN clave_natural TEXT
            GENERATED ALWAYS AS (COALESCE(codigo_origen, nombre_origen)) STORED;
        ALTER TABLE serie DROP CONSTRAINT IF EXISTS serie_indicador_id_nombre_origen_key;
        ALTER TABLE serie ADD CONSTRAINT serie_indicador_id_clave_natural_key
            UNIQUE (indicador_id, clave_natural);
    END IF;
END $$;

-- Tabla de hechos: un valor de una serie, en un periodo concreto
CREATE TABLE IF NOT EXISTS observacion (
    id BIGSERIAL PRIMARY KEY,
    serie_id BIGINT NOT NULL REFERENCES serie(id),
    periodo_fecha DATE NOT NULL,          -- fecha representativa del periodo (1er dia)
    anyo INTEGER NOT NULL,
    periodo_codigo TEXT,                  -- 'T1'..'T4', 'A' (anual), 'M01'..'M12'
    valor NUMERIC,
    unidad TEXT,
    escala TEXT,
    tipo_dato TEXT,
    secreto BOOLEAN NOT NULL DEFAULT FALSE,
    cargado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (serie_id, periodo_fecha)
);

CREATE INDEX IF NOT EXISTS idx_observacion_serie   ON observacion(serie_id);
CREATE INDEX IF NOT EXISTS idx_observacion_periodo ON observacion(periodo_fecha);

-- Vista de consulta comoda: una fila = un valor, con todo el contexto ya
-- resuelto (fuente, indicador, territorio, serie). Pensada para consultar
-- directamente sin tener que repetir los JOIN cada vez.
CREATE OR REPLACE VIEW v_observacion AS
SELECT
    o.id,
    f.codigo            AS fuente,
    i.codigo            AS indicador,
    i.nombre            AS indicador_nombre,
    i.categoria,
    t.nivel             AS territorio_nivel,
    t.nombre            AS territorio,
    s.nombre_origen     AS serie,
    s.atributos         AS serie_atributos,
    o.periodo_fecha,
    o.anyo,
    o.periodo_codigo,
    o.valor,
    o.unidad,
    o.escala,
    o.tipo_dato,
    o.secreto
FROM observacion o
JOIN serie s      ON s.id = o.serie_id
JOIN indicador i  ON i.id = s.indicador_id
JOIN fuente f     ON f.id = i.fuente_id
JOIN territorio t ON t.id = s.territorio_id;

-- Registro de cada ejecucion de ingesta (para poder diagnosticar el cron diario)
CREATE TABLE IF NOT EXISTS carga_log (
    id BIGSERIAL PRIMARY KEY,
    indicador_id INTEGER REFERENCES indicador(id),
    iniciado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_en TIMESTAMPTZ,
    filas_leidas INTEGER,
    filas_insertadas INTEGER,
    filas_actualizadas INTEGER,
    estado TEXT NOT NULL CHECK (estado IN ('ok', 'error')),
    mensaje TEXT
);

-- Calendario oficial de publicaciones del INE (2026-08-28): gobierna qué
-- indicadores necesitan de verdad una llamada a la API cada día en modo
-- incremental. Sustituye a la decisión anterior ("llamar siempre, el upsert
-- es idempotente" -- ver PROJECT.md §17, ahora superada por esta). Cada
-- indicador conoce su "operación" y "publicación" del INE
-- (ine_operacion_id / ine_publicacion_id, ver indicadores.py);
-- calendario_publicacion guarda las fechas de publicación conocidas o
-- previstas por indicador, refrescadas periódicamente desde
-- PUBLICACIONES_OPERACION / PUBLICACIONFECHA_PUBLICACION — ver
-- src/extremadura_datos/calendario.py.
ALTER TABLE indicador ADD COLUMN IF NOT EXISTS ine_operacion_id INTEGER;
ALTER TABLE indicador ADD COLUMN IF NOT EXISTS ine_publicacion_id INTEGER;
ALTER TABLE indicador ADD COLUMN IF NOT EXISTS calendario_actualizado_en TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS calendario_publicacion (
    id BIGSERIAL PRIMARY KEY,
    indicador_id INTEGER NOT NULL REFERENCES indicador(id),
    fecha_publicacion DATE NOT NULL,
    periodo_referencia TEXT,
    procesada BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (indicador_id, fecha_publicacion)
);

CREATE INDEX IF NOT EXISTS idx_calendario_pendientes
    ON calendario_publicacion (indicador_id, procesada);

-- --- Datos semilla -----------------------------------------------------------

INSERT INTO fuente (codigo, nombre, url_base) VALUES
    ('ine', 'Instituto Nacional de Estadistica', 'https://servicios.ine.es/wstempus/js')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    VALUES ('pais', '00', 'España', NULL)
ON CONFLICT (nivel, nombre) DO NOTHING;

INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '11', 'Extremadura', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;

INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'provincia', '06', 'Badajoz', id FROM territorio
    WHERE nivel = 'ccaa' AND nombre = 'Extremadura'
ON CONFLICT (nivel, nombre) DO NOTHING;

INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'provincia', '10', 'Cáceres', id FROM territorio
    WHERE nivel = 'ccaa' AND nombre = 'Extremadura'
ON CONFLICT (nivel, nombre) DO NOTHING;

-- Resto de Comunidades y Ciudades Autonomas (2026-08-28): antes solo se
-- guardaba Extremadura/Badajoz/Caceres; para poder comparar Extremadura
-- con el resto de Espana (objetivo del proyecto: web de analisis
-- actualizada a diario) hace falta el resto de CCAA como territorio real
-- -- ver indicadores.py (_TODAS_CCAA) y db.py (TERRITORIO_CLAVE_A_NOMBRE).
-- Los 4 indicadores de ambito exclusivamente provincial (no CCAA) siguen
-- limitados a Badajoz/Caceres -- no hay comparativa nacional a nivel de
-- provincia en esta fase.
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '01', 'Andalucía', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '02', 'Aragón', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '03', 'Asturias, Principado de', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '04', 'Balears, Illes', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '05', 'Canarias', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '06', 'Cantabria', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '07', 'Castilla y León', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '08', 'Castilla - La Mancha', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '09', 'Cataluña', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '10', 'Comunitat Valenciana', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '12', 'Galicia', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '13', 'Madrid, Comunidad de', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '14', 'Murcia, Región de', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '15', 'Navarra, Comunidad Foral de', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '16', 'País Vasco', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '17', 'Rioja, La', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '18', 'Ceuta', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;
INSERT INTO territorio (nivel, codigo_ine, nombre, padre_id)
    SELECT 'ccaa', '19', 'Melilla', id FROM territorio
    WHERE nivel = 'pais' AND nombre = 'España'
ON CONFLICT (nivel, nombre) DO NOTHING;

-- =============================================================================
--  Naturaleza del dato + normalización por población + vista final de
--  análisis (2026-08-28) — ver indicadores.py (campo naturaleza_dato) y
--  PROJECT.md §17. Objetivo: que al consultar los datos no se mezclen sin
--  querer naturalezas distintas (índice/tasa/conteo/monetario/promedio) ni
--  se comparen conteos absolutos entre territorios de tamaño muy distinto
--  sin normalizar por población, y que el secreto estadístico (observacion.
--  secreto) quede excluido por defecto en vez de tratarse como un cero.
-- =============================================================================

ALTER TABLE indicador ADD COLUMN IF NOT EXISTS naturaleza_dato TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'indicador_naturaleza_dato_check'
    ) THEN
        ALTER TABLE indicador ADD CONSTRAINT indicador_naturaleza_dato_check
            CHECK (naturaleza_dato IS NULL OR naturaleza_dato IN
                ('indice', 'tasa', 'conteo', 'monetario', 'promedio'));
    END IF;
END $$;

-- Población de referencia por territorio y año (tablas 2853/2852, ver
-- indicadores.py "Demografía"). Se filtra a la serie de "ambos sexos" —
-- ILIKE defensivo porque la etiqueta exacta que usa el INE para esa
-- categoría en estas dos tablas concretas no se ha podido verificar sin
-- acceso de red desde este entorno (pendiente de confirmar en la primera
-- ingesta real; si no calzase, esta vista devolvería 0 filas sin romper
-- nada más — revisar entonces s.atributos tal cual llega).
CREATE OR REPLACE VIEW v_poblacion AS
SELECT
    s.territorio_id,
    o.anyo,
    o.valor AS poblacion
FROM observacion o
JOIN serie s      ON s.id = o.serie_id
JOIN indicador i  ON i.id = s.indicador_id
WHERE i.codigo IN ('ine_poblacion_ccaa', 'ine_poblacion_provincia')
  AND NOT o.secreto
  AND (
        s.atributos = '{}'::jsonb
        OR s.atributos->'Sexo'->>'nombre' ILIKE 'total%'
        OR s.atributos->'Sexo'->>'nombre' ILIKE 'ambos%'
      );

-- Vista final de análisis: como v_observacion, pero (a) excluye el secreto
-- estadístico por defecto, (b) expone la naturaleza efectiva de cada
-- observación (la de la tabla, salvo que su propio tipo_dato indique que es
-- en realidad una tasa/variación — p.ej. IPC trae tanto el índice como su
-- variación mensual/anual dentro de la misma tabla), y (c) cuando esa
-- naturaleza efectiva es 'conteo', añade el valor normalizado por 1.000
-- habitantes usando la población conocida más reciente (<= año de la
-- observación) para ese mismo territorio — así Extremadura y Madrid se
-- pueden comparar en un conteo absoluto sin que el tamaño de cada uno
-- distorsione la lectura.
CREATE OR REPLACE VIEW v_analisis AS
SELECT
    o.id,
    f.codigo            AS fuente,
    i.codigo            AS indicador,
    i.nombre            AS indicador_nombre,
    i.categoria,
    i.naturaleza_dato   AS naturaleza_dato_tabla,
    -- Corregido 2026-09-16: en el INE `observacion.tipo_dato` trae el estado
    -- del dato ("Definitivo"/"Provisional"), no si es índice o variación. Eso
    -- va en una dimensión de la serie (serie.atributos) cuyo NOMBRE cambia
    -- según la tabla — verificado en producción: "Índices y Tasas" (IPC, IPI,
    -- IPV), "Índice y tasas" (ICN), "Tipo de dato" (EPA, sociedades...),
    -- "magnitud" (CRE: "Tasas de variación interanuales", "Estructura
    -- porcentual"). Por eso se busca en el valor de cualquier dimensión.
    -- Antes solo se miraba tipo_dato y las variaciones salían como 'indice'.
    CASE
        WHEN o.tipo_dato ILIKE '%variaci%' OR o.tipo_dato ILIKE '%tasa%'
          OR EXISTS (
                SELECT 1 FROM jsonb_each(s.atributos) AS dim(clave, valor)
                WHERE dim.valor->>'nombre' ILIKE ANY (ARRAY['%variaci%', '%tasa%', '%porcentual%'])
             ) THEN 'tasa'
        ELSE i.naturaleza_dato
    END                 AS naturaleza_dato_efectiva,
    t.id                AS territorio_id,
    t.nivel             AS territorio_nivel,
    t.nombre            AS territorio,
    s.nombre_origen     AS serie,
    s.atributos         AS serie_atributos,
    o.periodo_fecha,
    o.anyo,
    o.periodo_codigo,
    o.valor,
    o.unidad,
    o.escala,
    o.tipo_dato,
    p.anyo              AS poblacion_anyo_referencia,
    p.poblacion,
    CASE
        WHEN i.codigo NOT IN ('ine_poblacion_ccaa', 'ine_poblacion_provincia')
             AND (CASE WHEN o.tipo_dato ILIKE '%variaci%' OR o.tipo_dato ILIKE '%tasa%'
                         OR EXISTS (
                               SELECT 1 FROM jsonb_each(s.atributos) AS dim(clave, valor)
                               WHERE dim.valor->>'nombre' ILIKE ANY (ARRAY['%variaci%', '%tasa%', '%porcentual%'])
                            )
                       THEN 'tasa' ELSE i.naturaleza_dato END) = 'conteo'
             AND p.poblacion IS NOT NULL AND p.poblacion <> 0
        THEN round((o.valor / p.poblacion) * 1000, 4)
    END                 AS valor_por_1000_habitantes
FROM observacion o
JOIN serie s      ON s.id = o.serie_id
JOIN indicador i  ON i.id = s.indicador_id
JOIN fuente f     ON f.id = i.fuente_id
JOIN territorio t ON t.id = s.territorio_id
LEFT JOIN LATERAL (
    SELECT vp.anyo, vp.poblacion
    FROM v_poblacion vp
    WHERE vp.territorio_id = t.id AND vp.anyo <= o.anyo
    ORDER BY vp.anyo DESC
    LIMIT 1
) p ON TRUE
WHERE NOT o.secreto;

-- =============================================================================
--  Ampliación Eurostat: comparativa NUTS2 europea (2026-09-15)
--  Fase 1 de docs/ampliacion-nuts2-agro.md. Idempotente como el resto.
--  - Nueva fuente 'eurostat'.
--  - territorio.codigo_nuts: código NUTS/Eurostat. Las CCAA españolas SON
--    regiones NUTS2, así que se reutilizan las filas ya existentes (INE y
--    Eurostat comparten territorio). Países UE-27 y regiones NUTS2 del resto
--    de Europa se crean solas en la primera carga (db.get_or_create_territorio_nuts).
--  - Nuevos niveles: 'nuts2' (región europea no española) y 'agregado' (UE-27).
--  - indicador.origen_actualizado: último `updated` de Eurostat ya cargado,
--    para no volver a descargar un dataset sin cambios en modo incremental.
-- =============================================================================

INSERT INTO fuente (codigo, nombre, url_base) VALUES
    ('eurostat', 'Eurostat', 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0')
ON CONFLICT (codigo) DO NOTHING;

ALTER TABLE territorio ADD COLUMN IF NOT EXISTS codigo_nuts TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_territorio_codigo_nuts
    ON territorio (codigo_nuts) WHERE codigo_nuts IS NOT NULL;

ALTER TABLE indicador ADD COLUMN IF NOT EXISTS origen_actualizado TEXT;

-- Ampliar los CHECK de nivel. Solo se tocan si todavía no admiten 'nuts2'
-- (así reaplicar el esquema cada día no reescribe restricciones).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'territorio_nivel_check'
          AND pg_get_constraintdef(oid) LIKE '%nuts2%'
    ) THEN
        ALTER TABLE territorio DROP CONSTRAINT IF EXISTS territorio_nivel_check;
        ALTER TABLE territorio ADD CONSTRAINT territorio_nivel_check
            CHECK (nivel IN ('pais', 'ccaa', 'provincia', 'nuts2', 'agregado'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'indicador_nivel_territorial_check'
          AND pg_get_constraintdef(oid) LIKE '%nuts2%'
    ) THEN
        ALTER TABLE indicador DROP CONSTRAINT IF EXISTS indicador_nivel_territorial_check;
        ALTER TABLE indicador ADD CONSTRAINT indicador_nivel_territorial_check
            CHECK (nivel_territorial IN ('pais', 'ccaa', 'provincia', 'ccaa_y_provincia', 'nuts2'));
    END IF;
END $$;

-- Agregado UE-27 (referencia de comparación).
INSERT INTO territorio (nivel, codigo_nuts, nombre, padre_id)
    VALUES ('agregado', 'EU27_2020', 'Unión Europea (27)', NULL)
ON CONFLICT (nivel, nombre) DO NOTHING;

-- Códigos NUTS de los territorios españoles ya existentes (NUTS 2021/2024,
-- iguales para España). Solo rellena si está vacío.
UPDATE territorio t SET codigo_nuts = v.codigo_nuts
FROM (VALUES
    ('pais', 'España', 'ES'),
    ('ccaa', 'Galicia', 'ES11'),
    ('ccaa', 'Asturias, Principado de', 'ES12'),
    ('ccaa', 'Cantabria', 'ES13'),
    ('ccaa', 'País Vasco', 'ES21'),
    ('ccaa', 'Navarra, Comunidad Foral de', 'ES22'),
    ('ccaa', 'Rioja, La', 'ES23'),
    ('ccaa', 'Aragón', 'ES24'),
    ('ccaa', 'Madrid, Comunidad de', 'ES30'),
    ('ccaa', 'Castilla y León', 'ES41'),
    ('ccaa', 'Castilla - La Mancha', 'ES42'),
    ('ccaa', 'Extremadura', 'ES43'),
    ('ccaa', 'Cataluña', 'ES51'),
    ('ccaa', 'Comunitat Valenciana', 'ES52'),
    ('ccaa', 'Balears, Illes', 'ES53'),
    ('ccaa', 'Andalucía', 'ES61'),
    ('ccaa', 'Murcia, Región de', 'ES62'),
    ('ccaa', 'Ceuta', 'ES63'),
    ('ccaa', 'Melilla', 'ES64'),
    ('ccaa', 'Canarias', 'ES70'),
    ('provincia', 'Badajoz', 'ES431'),
    ('provincia', 'Cáceres', 'ES432')
) AS v(nivel, nombre, codigo_nuts)
WHERE t.nivel = v.nivel AND t.nombre = v.nombre AND t.codigo_nuts IS NULL;

-- España conserva padre_id NULL (raíz de la jerarquía INE); el resto de
-- países UE-27 cuelgan de la UE-27.
