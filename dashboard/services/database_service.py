"""Database infrastructure extracted in Fase 11.

Keeps PostgreSQL connection, queries, commits and schema initialization out
of the Streamlit entry point while preserving the existing application contract.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text


class DatabaseService:
    """Infrastructure service for the PostgreSQL database."""

    def __init__(self, conn, machine_configs):
        self.conn = conn
        self.machine_configs = machine_configs
        self.last_error = None

    def query_db(self, sql_string, params=None):
        try:
            with self.conn.session as session:
                result = session.execute(text(sql_string), params or {})
                rows = result.fetchall()
                if not rows:
                    return pd.DataFrame()
                df = pd.DataFrame(rows)
                df.columns = result.keys()
                df.columns = [c.lower() for c in df.columns]
                return df
        except Exception:
            return pd.DataFrame()

    def commit_db(self, sql_string, params=None):
        self.last_error = None
        try:
            with self.conn.session as session:
                session.execute(text(sql_string), params or {})
                session.commit()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def inicializar_base_de_datos(self):
        tablas = [
            """CREATE TABLE IF NOT EXISTS test_results (
                id SERIAL PRIMARY KEY,
                machine_name VARCHAR(100),
                health_score FLOAT,
                missing_nodes INTEGER,
                health_map TEXT,
                evidence_path TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE,
                password TEXT,
                role VARCHAR(20)
            );""",
            """CREATE TABLE IF NOT EXISTS estados_maquinas (
                machine_name VARCHAR(50) PRIMARY KEY,
                estado VARCHAR(50) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""", # <-- ¡Aquí faltaba la coma!
    
            """CREATE TABLE IF NOT EXISTS bitacora_mantenimiento (
                id SERIAL PRIMARY KEY,
                machine_name VARCHAR(100) NOT NULL,
                tipo_mantenimiento VARCHAR(50) NOT NULL,
                piezas_cambiadas TEXT,
                notas TEXT,
                fecha_ejecucion DATE NOT NULL,
                proximo_mantenimiento DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            
            """CREATE TABLE IF NOT EXISTS odps (
                id SERIAL PRIMARY KEY,
                numero_odp VARCHAR(50) UNIQUE NOT NULL,
                cliente VARCHAR(150) NOT NULL,
                estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
                maquina_asignada VARCHAR(100),
                fecha_asignacion TIMESTAMP,
                usuario_asignacion VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            
            """CREATE TABLE IF NOT EXISTS historial_odps (
                id SERIAL PRIMARY KEY,
                numero_odp VARCHAR(50) NOT NULL,
                cliente VARCHAR(150),
                estado_anterior VARCHAR(30),
                estado_nuevo VARCHAR(30),
                maquina_anterior VARCHAR(100),
                maquina_nueva VARCHAR(100),
                usuario VARCHAR(100),
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""",
            """CREATE TABLE IF NOT EXISTS odp_asignaciones (
                id SERIAL PRIMARY KEY,
                odp_id INTEGER REFERENCES odps(id) ON DELETE CASCADE,
                numero_odp VARCHAR(50) NOT NULL,
                cliente VARCHAR(150),
                material VARCHAR(30) NOT NULL DEFAULT 'GENERAL',
                maquina_asignada VARCHAR(100),
                requiere_corte BOOLEAN NOT NULL DEFAULT FALSE,
                tipo_proceso VARCHAR(30) NOT NULL DEFAULT 'IMPRESION',
                cantidad_m2 FLOAT NOT NULL DEFAULT 0,
                cantidad_laminas INTEGER NOT NULL DEFAULT 0,
                pasadas INTEGER,
                tinta_blanca BOOLEAN NOT NULL DEFAULT FALSE,
                day_night BOOLEAN NOT NULL DEFAULT FALSE,
                tipo_corte VARCHAR(50),
                cantidad_cortes INTEGER NOT NULL DEFAULT 0,
                tiempo_produccion_min FLOAT NOT NULL DEFAULT 0,
                tiempo_corte_min FLOAT NOT NULL DEFAULT 0,
                tiempo_estimado_min FLOAT NOT NULL DEFAULT 0,
                fecha_estimada_finalizacion TIMESTAMP,
                estado VARCHAR(30) NOT NULL DEFAULT 'EN PROCESO',
                fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_asignacion VARCHAR(100),
                fecha_impresion TIMESTAMP,
                fecha_router TIMESTAMP,
                fecha_finalizacion TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    
            );""",
            
            """CREATE TABLE IF NOT EXISTS historial_estados (
                id SERIAL PRIMARY KEY,
                machine_name VARCHAR(100) NOT NULL,
                estado VARCHAR(50) NOT NULL,
                fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_fin TIMESTAMP,
                duracion_horas FLOAT
            );"""
            
        ]
    
        self.commit_db("ALTER TABLE bitacora_mantenimiento ADD COLUMN IF NOT EXISTS foto_tag TEXT;")
    
        for t in tablas:
            self.commit_db(t)
    
        self.commit_db("ALTER TABLE odp_asignaciones ADD COLUMN IF NOT EXISTS maquina_router VARCHAR(100);")
        self.commit_db("ALTER TABLE odps ADD COLUMN IF NOT EXISTS prioridad VARCHAR(20) NOT NULL DEFAULT 'NORMAL';")
        # Permitir ODPs que van directamente a Router sin pasar por impresión.
        self.commit_db("ALTER TABLE odp_asignaciones ALTER COLUMN maquina_asignada DROP NOT NULL;")
        # Campos de planeación de producción (compatibles con instalaciones existentes).
        for _col, _tipo in {
            "tipo_proceso": "VARCHAR(30) NOT NULL DEFAULT 'IMPRESION'",
            "cantidad_m2": "FLOAT NOT NULL DEFAULT 0",
            "cantidad_laminas": "INTEGER NOT NULL DEFAULT 0",
            "pasadas": "INTEGER",
            "tinta_blanca": "BOOLEAN NOT NULL DEFAULT FALSE",
            "day_night": "BOOLEAN NOT NULL DEFAULT FALSE",
            "tipo_corte": "VARCHAR(50)",
            "cantidad_cortes": "INTEGER NOT NULL DEFAULT 0",
            "tiempo_produccion_min": "FLOAT NOT NULL DEFAULT 0",
            "tiempo_corte_min": "FLOAT NOT NULL DEFAULT 0",
            "tiempo_estimado_min": "FLOAT NOT NULL DEFAULT 0",
            "fecha_estimada_finalizacion": "TIMESTAMP",
            "metros_lineales": "FLOAT NOT NULL DEFAULT 0",
            "ancho_material_m": "FLOAT NOT NULL DEFAULT 1.52",
            "cantidad_copias": "INTEGER NOT NULL DEFAULT 1",
            "modo_velocidad": "VARCHAR(20) NOT NULL DEFAULT 'MAXIMA'",
            "doble_saturacion": "BOOLEAN NOT NULL DEFAULT FALSE",
            "prioridad": "VARCHAR(20) NOT NULL DEFAULT 'NORMAL'"
        }.items():
            self.commit_db(f"ALTER TABLE odp_asignaciones ADD COLUMN IF NOT EXISTS {_col} {_tipo};")
    
        # Migración de estados de ODP de versiones anteriores.
        # ASIGNADO pasa a EN PROCESO porque ahora la asignación inicia directamente la producción.
        self.commit_db("""
            UPDATE odps
            SET estado = 'EN PROCESO', updated_at = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City')
            WHERE estado = 'ASIGNADO'
        """)
    
        # Crear una asignación histórica para ODPs existentes que ya tenían máquina.
        # Esto permite que la nueva arquitectura soporte varias máquinas por una misma ODP
        # sin perder los registros anteriores.
        self.commit_db("""
            INSERT INTO odp_asignaciones (
                odp_id, numero_odp, cliente, material, maquina_asignada,
                requiere_corte, estado, fecha_asignacion, usuario_asignacion,
                created_at, updated_at
            )
            SELECT
                o.id, o.numero_odp, o.cliente, 'GENERAL', o.maquina_asignada,
                FALSE, o.estado, COALESCE(o.fecha_asignacion, o.created_at),
                o.usuario_asignacion, o.created_at, o.updated_at
            FROM odps o
            WHERE o.maquina_asignada IS NOT NULL
              AND TRIM(o.maquina_asignada) <> ''
              AND NOT EXISTS (
                  SELECT 1 FROM odp_asignaciones a
                  WHERE a.odp_id = o.id
              );
        """)
        
        # Sincronizar automáticamente todas las máquinas de tu config
        for maq_nombre in self.machine_configs.keys():
            self.commit_db("""
                INSERT INTO estados_maquinas (machine_name, estado) 
                VALUES (:m, 'Operativa') 
                ON CONFLICT (machine_name) DO NOTHING;
            """, {"m": maq_nombre})
    
        columnas = {
            "health_map": "TEXT",
            "missing_nodes": "INTEGER",
            "evidence_path": "TEXT",
            "comments": "TEXT"
        }
        for nombre_col, tipo_col in columnas.items():
            try:
                with self.conn.session as session:
                    session.execute(text(f"ALTER TABLE test_results ADD COLUMN IF NOT EXISTS {nombre_col} {tipo_col};"))
                    session.commit()
            except Exception as e: 
                print(f"Error en parche: {e}")
        # ------------------------------------------------------------
        # MIGRACIÓN ÚNICA: timestamps históricos UTC -> hora México
        # ------------------------------------------------------------
        # La versión anterior guardaba CURRENT_TIMESTAMP en columnas
        # TIMESTAMP WITHOUT TIME ZONE. Los registros existentes quedan
        # 6 horas adelantados respecto a la operación local.
        self.commit_db("""
            CREATE TABLE IF NOT EXISTS sistema_config (
                clave VARCHAR(100) PRIMARY KEY,
                valor TEXT,
                updated_at TIMESTAMP
            );
        """)
    
        migracion = self.query_db("""
            SELECT valor FROM sistema_config
            WHERE clave = 'timestamps_produccion_migrados_mexico_v1'
            LIMIT 1
        """)
    
        if migracion.empty:
            for tabla, columnas in {
                "odp_asignaciones": ["fecha_asignacion", "fecha_impresion", "fecha_router", "fecha_finalizacion"],
                "odps": ["fecha_asignacion"],
                "historial_odps": ["fecha"],
                "historial_estados": ["fecha_inicio", "fecha_fin"],
                "test_results": ["timestamp"]
            }.items():
                for columna in columnas:
                    self.commit_db(f"""
                        UPDATE {tabla}
                        SET {columna} = {columna} - INTERVAL '6 hours'
                        WHERE {columna} IS NOT NULL;
                    """)
    
            self.commit_db("""
                INSERT INTO sistema_config (clave, valor, updated_at)
                VALUES (
                    'timestamps_produccion_migrados_mexico_v1',
                    'UTC a America/Mexico_City; ejecutado una sola vez',
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (clave) DO NOTHING;
            """)
    
        return True

    def obtener_ultimo_estado(self, nombre_maquina):
        sql = """
            SELECT health_score, timestamp, missing_nodes 
            FROM test_results 
            WHERE machine_name = :name 
            ORDER BY timestamp DESC LIMIT 1
        """
        df = self.query_db(sql, {"name": nombre_maquina})
        if not df.empty:
            return df.iloc[0]
        return None
