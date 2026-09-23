"""Consultas y preparación de datos de ODP para las vistas del dashboard."""

import pandas as pd


class ODPQueryService:
    """Encapsula las consultas de lectura relacionadas con ODP."""

    def __init__(self, query_db, es_maquina_router, normalizar_prioridad_odp):
        self.query_db = query_db
        self.es_maquina_router = es_maquina_router
        self.normalizar_prioridad_odp = normalizar_prioridad_odp

    def obtener_odps_en_proceso(self, maquina=None):
        params = {}
        filtro = ""

        if maquina and maquina != "Todas":
            params["maquina"] = maquina
            if self.es_maquina_router(maquina):
                filtro = """
                    AND a.maquina_router = :maquina
                    AND a.estado = 'EN ROUTER'
                """
            else:
                filtro = """
                    AND a.maquina_asignada = :maquina
                    AND a.estado = 'EN PROCESO'
                """

        return self.query_db(
            f"""
            SELECT
                a.id AS asignacion_id,
                a.numero_odp,
                a.cliente,
                a.material,
                a.estado,
                a.maquina_asignada,
                a.maquina_router,
                a.requiere_corte,
                a.tipo_proceso,
                a.cantidad_m2,
                a.cantidad_laminas,
                a.pasadas,
                a.modo_velocidad,
                a.tinta_blanca,
                a.day_night,
                a.prioridad,
                a.tipo_corte,
                a.cantidad_cortes,
                a.tiempo_produccion_min,
                a.tiempo_corte_min,
                a.tiempo_estimado_min,
                a.fecha_estimada_finalizacion,
                a.fecha_asignacion,
                a.usuario_asignacion,
                a.fecha_impresion,
                a.fecha_router
            FROM odp_asignaciones a
            WHERE a.estado IN ('EN PROCESO', 'EN ROUTER')
            {filtro}
            ORDER BY
                CASE UPPER(COALESCE(a.prioridad, 'NORMAL'))
                    WHEN 'BOMBERAZO' THEN 1
                    WHEN 'URGENTE' THEN 2
                    ELSE 3
                END,
                a.fecha_asignacion ASC,
                a.numero_odp ASC,
                a.id ASC
            """,
            params,
        )

    def obtener_odps_finalizadas(self, maquina=None, fecha_inicio=None, fecha_fin=None):
        params = {}
        filtro = ""

        if maquina and maquina != "Todas":
            filtro += " AND (a.maquina_asignada=:maquina OR a.maquina_router=:maquina) "
            params["maquina"] = maquina

        if fecha_inicio and fecha_fin:
            filtro += " AND a.fecha_finalizacion::date BETWEEN :fecha_inicio AND :fecha_fin "
            params["fecha_inicio"] = fecha_inicio
            params["fecha_fin"] = fecha_fin

        query = f"""
            SELECT a.id AS asignacion_id, a.numero_odp, a.cliente, a.material, a.estado,
                   a.maquina_asignada, a.maquina_router, a.requiere_corte, a.tipo_proceso,
                   a.cantidad_m2, a.cantidad_laminas, a.pasadas, a.tinta_blanca, a.day_night,
                   a.prioridad, a.tipo_corte, a.cantidad_cortes, a.tiempo_produccion_min,
                   a.tiempo_corte_min, a.tiempo_estimado_min, a.fecha_estimada_finalizacion,
                   a.fecha_asignacion, a.fecha_impresion, a.fecha_router, a.fecha_finalizacion,
                   a.usuario_asignacion
            FROM odp_asignaciones a
            WHERE (a.estado='CORTADO' OR (a.estado='IMPRESO' AND a.requiere_corte=FALSE))
            {filtro}
            ORDER BY a.fecha_finalizacion DESC, a.numero_odp
        """
        return self.query_db(query, params)

    def obtener_registro_odps_finalizadas(self, maquina=None, fecha_inicio=None, fecha_fin=None):
        df = self.obtener_odps_finalizadas(maquina, fecha_inicio, fecha_fin)
        if df.empty:
            return df

        df = df.rename(columns={
            "numero_odp": "ODP", "cliente": "Cliente", "material": "Material",
            "maquina_asignada": "Máquina Impresión", "maquina_router": "Máquina Router",
            "requiere_corte": "Requiere corte", "tipo_proceso": "Ruta",
            "cantidad_m2": "m²", "cantidad_laminas": "Láminas", "pasadas": "Pasadas",
            "tinta_blanca": "Tinta blanca", "day_night": "Day & Night",
            "prioridad": "Prioridad", "tipo_corte": "Tipo corte", "cantidad_cortes": "Cortes",
            "tiempo_produccion_min": "Min impresión", "tiempo_corte_min": "Min corte",
            "tiempo_estimado_min": "Min total estimado", "fecha_estimada_finalizacion": "Fin estimado",
            "estado": "Estado", "fecha_asignacion": "Asignación", "fecha_impresion": "Impresión",
            "fecha_router": "Router", "fecha_finalizacion": "Finalización",
            "usuario_asignacion": "Usuario"
        }).copy()

        if "Prioridad" in df.columns:
            df["Prioridad"] = df["Prioridad"].apply(self.normalizar_prioridad_odp)

        df["Requiere corte"] = df["Requiere corte"].map({True: "Sí", False: "No"}).fillna("No")

        if "Pasadas" in df.columns:
            def _formatear_pasadas_tabla(x):
                if x is None or pd.isna(x):
                    return "ESTÁNDAR"
                try:
                    xf = float(x)
                    if xf.is_integer():
                        return str(int(xf))
                except Exception:
                    pass
                return str(x)
            df["Pasadas"] = df["Pasadas"].apply(_formatear_pasadas_tabla)

        return df
