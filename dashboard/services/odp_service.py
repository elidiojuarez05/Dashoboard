"""Servicios de negocio para el ciclo de vida de las ODPs.

Fase 9 del refactor: se separa de dashboard.py la lógica de asignación,
edición, eliminación, cambio de estado y registro de ODPs.
"""

from __future__ import annotations

import pandas as pd


class ODPService:
    """Encapsula las operaciones de negocio de ODP.

    Las dependencias se inyectan desde dashboard.py para evitar acoplar este
    servicio a Streamlit o a la implementación concreta de la base de datos.
    """

    def __init__(
        self,
        *,
        query_db,
        commit_db,
        ahora_mexico,
        estimar_produccion,
        normalizar_prioridad_odp,
        etiqueta_prioridad_odp,
        formatear_duracion,
        numero_seguro,
        norm_nombre_estacion,
        maquina_compatible_material,
    ):
        self.query_db = query_db
        self.commit_db = commit_db
        self.ahora_mexico = ahora_mexico
        self.estimar_produccion = estimar_produccion
        self.normalizar_prioridad_odp = normalizar_prioridad_odp
        self.etiqueta_prioridad_odp = etiqueta_prioridad_odp
        self.formatear_duracion = formatear_duracion
        self.numero_seguro = numero_seguro
        self.norm_nombre_estacion = norm_nombre_estacion
        self.maquina_compatible_material = maquina_compatible_material

    def _sincronizar_estado_maestro_odp(self, numero_odp):

        df = self.query_db("""
            SELECT
                COUNT(*) AS total,

                COUNT(*) FILTER (
                    WHERE estado = 'CORTADO'
                       OR (
                           estado = 'IMPRESO'
                           AND requiere_corte = FALSE
                       )
                ) AS finalizadas,

                COUNT(*) FILTER (
                    WHERE estado IN ('EN PROCESO', 'EN ROUTER')
                ) AS activas,

                COUNT(*) FILTER (
                    WHERE estado = 'CORTADO'
                ) AS cortadas

            FROM odp_asignaciones
            WHERE numero_odp = :odp
        """, {
            "odp": numero_odp
        })

        if df.empty:
            return

        total = int(df.iloc[0]["total"] or 0)
        finalizadas = int(df.iloc[0]["finalizadas"] or 0)
        activas = int(df.iloc[0]["activas"] or 0)
        cortadas = int(df.iloc[0]["cortadas"] or 0)

        if total == 0:

            estado = "PENDIENTE"

        elif activas > 0:

            estado = "EN PROCESO"

        elif finalizadas == total:

            estado = "CORTADO" if cortadas > 0 else "IMPRESO"

        else:

            estado = "EN PROCESO"

        self.commit_db("""
            UPDATE odps
            SET
                estado = :estado,
                updated_at = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City')
            WHERE numero_odp = :odp
        """, {
            "estado": estado,
            "odp": numero_odp
        })

    def actualizar_estado_asignacion(self, asignacion_id, nuevo_estado, usuario):
        nuevo_estado = str(nuevo_estado).strip().upper()
        if nuevo_estado not in {"IMPRESO", "CORTADO"}: 
            return False, "Estado no válido."
        
        df = self.query_db("SELECT id, numero_odp, cliente, estado, maquina_asignada, maquina_router, requiere_corte FROM odp_asignaciones WHERE id=:id", {"id": asignacion_id})
        if df.empty: 
            return False, "La asignación no existe."
        
        anterior = str(df.iloc[0]["estado"]).strip().upper()
        corte = bool(df.iloc[0]["requiere_corte"])
        router = df.iloc[0]["maquina_router"]
    
        if nuevo_estado == "IMPRESO":
            if anterior != "EN PROCESO": 
                return False, f"No se puede marcar IMPRESO desde {anterior}."
            if corte:
                if not router: 
                    return False, "La ODP requiere corte pero no tiene ROUTER asignada."
            
                estado_final = "EN ROUTER"
                # OJO: Aquí NO llenamos fecha_router. Solo fecha_impresion.
                sql = "UPDATE odp_asignaciones SET estado='EN ROUTER', fecha_impresion=(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'), updated_at=(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City') WHERE id=:id"
                mensaje = f"ODP {df.iloc[0]['numero_odp']} impresa y enviada a ROUTER {router}."
            else:
                estado_final = "IMPRESO"
                sql = "UPDATE odp_asignaciones SET estado='IMPRESO', fecha_impresion=(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'), fecha_finalizacion=(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'), updated_at=(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City') WHERE id=:id"
                mensaje = f"ODP {df.iloc[0]['numero_odp']} marcada como IMPRESA y finalizada."
            
        else:  # Cuando se marca como CORTADO
            if anterior != "EN ROUTER": 
                return False, "Para marcar CORTADO la ODP debe estar en ROUTER."
            
            estado_final = "CORTADO"
            # ¡Aquí es donde oficialmente se sella la fecha de router y la fecha de finalización!
            sql = "UPDATE odp_asignaciones SET estado='CORTADO', fecha_router=(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'), fecha_finalizacion=(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'), updated_at=(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City') WHERE id=:id"
            mensaje = f"ODP {df.iloc[0]['numero_odp']} marcada como CORTADA y finalizada."

        ok = self.commit_db(sql, {"id": int(asignacion_id)})
        if not ok: 
            return False, "No fue posible actualizar la asignación."
        
        maquina_historial = df.iloc[0]["maquina_asignada"] or df.iloc[0]["maquina_router"]
        self.commit_db("""INSERT INTO historial_odps (numero_odp, cliente, estado_anterior, estado_nuevo, maquina_anterior, maquina_nueva, usuario) VALUES (:odp, :cliente, :anterior, :nuevo, :maquina, :maquina, :usuario)""", 
                  {"odp": df.iloc[0]["numero_odp"], "cliente": df.iloc[0]["cliente"], "anterior": anterior, "nuevo": estado_final, "maquina": maquina_historial, "usuario": usuario})
              
        self._sincronizar_estado_maestro_odp(str(df.iloc[0]["numero_odp"]))
        self.query_db.clear()
        return True, mensaje

    def eliminar_asignacion(self, asignacion_id, usuario):
        """Elimina una asignación activa ingresada por error o cancelada."""
        try:
            aid = int(asignacion_id)
        except Exception:
            return False, "Identificador de asignación no válido."
        df = self.query_db("""
            SELECT id, numero_odp, cliente, estado, maquina_asignada, maquina_router
            FROM odp_asignaciones WHERE id=:id
        """, {"id": aid})
        if df.empty:
            return False, "La asignación ya no existe."
        r = df.iloc[0]
        anterior = str(r["estado"] or "").strip().upper()
        if anterior not in {"EN PROCESO", "EN ROUTER"}:
            return False, f"No se puede eliminar una asignación con estado {anterior}."
        numero = str(r["numero_odp"] or "")
        maquina = r["maquina_asignada"] or r["maquina_router"]
        ok_hist = self.commit_db(
            """INSERT INTO historial_odps
            (numero_odp, cliente, estado_anterior, estado_nuevo, maquina_anterior, maquina_nueva, usuario)
            VALUES (:odp, :cliente, :anterior, 'CANCELADO / ELIMINADO', :maquina, :maquina, :usuario)""",
            {"odp": numero, "cliente": r["cliente"], "anterior": anterior, "maquina": maquina, "usuario": usuario}
        )
        if not ok_hist:
            return False, "No fue posible registrar la cancelación."
        ok = self.commit_db("DELETE FROM odp_asignaciones WHERE id=:id", {"id": aid})
        if not ok:
            return False, "No fue posible eliminar la asignación."
        self._sincronizar_estado_maestro_odp(numero)
        self.query_db.clear()
        return True, f"Asignación de ODP {numero} eliminada correctamente."

    def editar_asignacion_produccion(self, 
        asignacion_id,
        pasadas=None,
        prioridad=None,
        tipo_corte=None,
        cantidad_cortes=None,
        modo_velocidad=None,
        usuario=None,
    ):
        """Actualiza parámetros de una ODP activa y recalcula sus tiempos."""
        df = self.query_db("""
            SELECT id, numero_odp, cliente, maquina_asignada, maquina_router,
                   estado, material, requiere_corte, tipo_proceso,
                   cantidad_m2, cantidad_laminas, pasadas, tinta_blanca,
                   day_night, tipo_corte, cantidad_cortes, metros_lineales,
                   ancho_material_m, cantidad_copias, modo_velocidad,
                   doble_saturacion, prioridad
            FROM odp_asignaciones
            WHERE id=:id
        """, {"id": int(asignacion_id)})

        if df.empty:
            return False, "La asignación no existe."

        r = df.iloc[0]
        estado = str(r["estado"] or "").strip().upper()
        if estado not in {"EN PROCESO", "EN ROUTER"}:
            return False, f"No se puede editar una ODP con estado {estado}."

        maquina = r["maquina_asignada"]
        router = r["maquina_router"]
        material = str(r["material"] or "GENERAL").strip().upper()
        tipo_proceso = str(r["tipo_proceso"] or "IMPRESION").strip().upper()

        nueva_prioridad = self.normalizar_prioridad_odp(prioridad if prioridad is not None else r.get("prioridad"))

        nuevas_pasadas = pasadas
        if nuevas_pasadas is None:
            nuevas_pasadas = r["pasadas"]

        nuevo_tipo_corte = tipo_corte if tipo_corte is not None else r["tipo_corte"]
        nuevos_cortes = int(cantidad_cortes if cantidad_cortes is not None else (r["cantidad_cortes"] or 0))
        nuevo_modo = str(modo_velocidad if modo_velocidad is not None else (r["modo_velocidad"] or "MAXIMA")).strip().upper()
        nuevo_modo = "ESTANDAR" if nuevo_modo in {"ESTÁNDAR", "ESTANDAR", "STANDARD", "NORMAL"} else "MAXIMA"

        mi, mc, mt = self.estimar_produccion(
            maquina=maquina,
            maquina_router=router,
            material=material,
            tipo_proceso=tipo_proceso,
            cantidad_m2=self.numero_seguro(r["cantidad_m2"]),
            cantidad_laminas=int(r["cantidad_laminas"] or 0),
            pasadas=nuevas_pasadas,
            tinta_blanca=bool(r["tinta_blanca"]),
            day_night=bool(r["day_night"]),
            tipo_corte=nuevo_tipo_corte,
            cantidad_cortes=nuevos_cortes,
            modo_velocidad=nuevo_modo,
            metros_lineales=self.numero_seguro(r["metros_lineales"]),
            cantidad_copias=max(1, int(r["cantidad_copias"] or 1)),
            ancho_material_m=self.numero_seguro(r["ancho_material_m"], 1.52),
            doble_saturacion=bool(r["doble_saturacion"]),
        )

        if tipo_proceso != "SOLO CORTE" and mi <= 0:
            return False, "Los nuevos parámetros no tienen una calibración válida de impresión."
        if bool(r["requiere_corte"]) and mc <= 0:
            return False, f"Los nuevos parámetros no tienen una calibración válida para {router} / {nuevo_tipo_corte}."
        if mt <= 0:
            return False, "El nuevo tiempo estimado resultó en 0 minutos."

        fecha_estimada = self.ahora_mexico() + timedelta(minutes=float(mt))

        ok = self.commit_db("""
            UPDATE odp_asignaciones
            SET prioridad=:prioridad,
                pasadas=:pasadas,
                tipo_corte=:tipo_corte,
                cantidad_cortes=:cantidad_cortes,
                modo_velocidad=:modo,
                tiempo_produccion_min=:mi,
                tiempo_corte_min=:mc,
                tiempo_estimado_min=:mt,
                fecha_estimada_finalizacion=:fin,
                updated_at=:ahora
            WHERE id=:id
        """, {
            "prioridad": nueva_prioridad,
            "pasadas": nuevas_pasadas,
            "tipo_corte": nuevo_tipo_corte,
            "cantidad_cortes": nuevos_cortes,
            "modo": nuevo_modo,
            "mi": float(mi),
            "mc": float(mc),
            "mt": float(mt),
            "fin": fecha_estimada,
            "ahora": self.ahora_mexico(),
            "id": int(asignacion_id),
        })

        if not ok:
            return False, "No fue posible actualizar la ODP."

        self.commit_db("""
            INSERT INTO historial_odps
            (numero_odp, cliente, estado_anterior, estado_nuevo,
             maquina_anterior, maquina_nueva, usuario)
            VALUES
            (:odp, :cliente, :anterior, :nuevo, :maquina, :maquina, :usuario)
        """, {
            "odp": r["numero_odp"],
            "cliente": r["cliente"],
            "anterior": estado,
            "nuevo": "PARÁMETROS EDITADOS",
            "maquina": maquina or router,
            "usuario": usuario or "sistema",
        })

        self.query_db.clear()
        return True, (
            f"ODP {r['numero_odp']} actualizada: "
            f"{self.formatear_duracion(mt)} total."
        )

    def asignar_odp(self, 
        numero_odp,
        maquina,
        cliente,
        usuario,
        material="GENERAL",
        requiere_corte=False,
        maquina_router=None,
        tipo_proceso="IMPRESION",
        cantidad_m2=0,
        cantidad_laminas=0,
        pasadas=None,
        tinta_blanca=False,
        day_night=False,
        tipo_corte=None,
        cantidad_cortes=0,
        modo_velocidad="MAXIMA",
        metros_lineales=0.0, cantidad_copias=1, ancho_material_m=1.52, doble_saturacion=False,
        prioridad="NORMAL"
    ):
        """
        Crea la asignación de producción y guarda el tiempo estimado.

        modo_velocidad:
            MAXIMA   = tiempo más rápido
            ESTANDAR = tiempo estándar de producción
        """

        numero_odp = str(numero_odp).strip()

        material = str(
            material or "GENERAL"
        ).strip().upper()

        tipo_proceso = str(
            tipo_proceso or "IMPRESION"
        ).strip().upper()

        maquina = (
            str(maquina).strip()
            if maquina
            else None
        )

        maquina_router = (
            str(maquina_router).strip()
            if maquina_router
            else None
        )

        # Normalizar modo
        modo_velocidad = str(
            modo_velocidad or "MAXIMA"
        ).strip().upper()

        if modo_velocidad in {
            "ESTÁNDAR",
            "ESTANDAR",
            "STANDARD",
            "NORMAL"
        }:
            modo_velocidad = "ESTANDAR"
        else:
            modo_velocidad = "MAXIMA"

        prioridad = self.normalizar_prioridad_odp(prioridad)

        # ============================================================
        # VALIDACIONES
        # ============================================================

        if tipo_proceso == "SOLO CORTE":
            maquina = None

        elif not maquina:
            return False, (
                "Debe seleccionar una máquina de impresión."
            )

        if maquina and not self.maquina_compatible_material(
            maquina,
            material
        ):
            return False, (
                f"La máquina {maquina} no es compatible "
                f"con el material {material}."
            )

        if requiere_corte and not maquina_router:
            return False, (
                "Debe seleccionar un Router para esta ruta."
            )

        if (
            requiere_corte
            and not self.maquina_compatible_material(
                maquina_router,
                material
            )
        ):
            return False, (
                f"El Router {maquina_router} no es compatible "
                f"con el material {material}."
            )

        # Plotter: exclusivamente VINIL.
        if (
            maquina_router
            and "PLOTTER RECORTE"
            in self.norm_nombre_estacion(maquina_router)
            and material != "VINIL"
        ):
            return False, (
                "El Plotter Recorte solamente puede "
                "utilizarse con VINIL."
            )

        # ============================================================
        # CÁLCULO ÚNICO DE PRODUCCIÓN
        # ============================================================

        min_imp, min_corte, min_total = self.estimar_produccion(
            maquina=maquina,
            maquina_router=maquina_router,
            material=material,
            tipo_proceso=tipo_proceso,
            cantidad_m2=cantidad_m2,
            cantidad_laminas=cantidad_laminas,
            pasadas=pasadas,
            tinta_blanca=tinta_blanca,
            day_night=day_night,
            tipo_corte=tipo_corte,
            cantidad_cortes=cantidad_cortes,
            modo_velocidad=modo_velocidad,
            metros_lineales=metros_lineales, cantidad_copias=cantidad_copias,
            ancho_material_m=ancho_material_m,
            doble_saturacion=doble_saturacion
        )

        # ============================================================
        # VALIDAR TIEMPOS
        # ============================================================

        if (
            tipo_proceso != "SOLO CORTE"
            and min_imp <= 0
        ):
            return False, (
                f"No hay una calibración válida de producción "
                f"para {maquina}."
            )

        if requiere_corte and min_corte <= 0:
            return False, (
                f"No hay una calibración válida para "
                f"{maquina_router} / {tipo_corte}."
            )

        if min_total <= 0:
            return False, (
                "El tiempo estimado resultó en 0 minutos. "
                "Revise cantidades y configuración."
            )

        # ============================================================
        # BUSCAR Y VALIDAR ODP
        # ============================================================

        odp = self.query_db(
            """
            SELECT id, cliente, estado, maquina_asignada
            FROM odps
            WHERE numero_odp=:odp
            LIMIT 1
            """,
            {
                "odp": numero_odp
            }
        )

        if odp.empty:
            return False, (
                f"La ODP {numero_odp} no existe."
            )

        registro_odp = odp.iloc[0]
        odp_id = int(registro_odp["id"])
        cliente_maestro = str(registro_odp.get("cliente") or "").strip()

        # La validación real se hace contra las asignaciones que siguen
        # vigentes o que ya terminaron. La tabla maestra `odps` puede conservar
        # un registro antiguo después de una cancelación/eliminación; ese registro
        # por sí solo NO debe bloquear una nueva alta.
        asignaciones_odp = self.query_db(
            """
            SELECT id, cliente, estado, fecha_finalizacion
            FROM odp_asignaciones
            WHERE numero_odp=:odp
            ORDER BY id DESC
            """,
            {"odp": numero_odp}
        )

        estados_bloqueantes = {"EN PROCESO", "EN ROUTER", "IMPRESO", "CORTADO"}
        asignacion_vigente_o_finalizada = (
            not asignaciones_odp.empty
            and asignaciones_odp["estado"].fillna("").astype(str).str.strip().str.upper().isin(estados_bloqueantes).any()
        )

        if asignacion_vigente_o_finalizada:
            clientes_activos = {
                str(v).strip()
                for v in asignaciones_odp.loc[
                    asignaciones_odp["estado"].fillna("").astype(str).str.strip().str.upper().isin(estados_bloqueantes),
                    "cliente"
                ].tolist()
                if str(v or "").strip()
            }
            cliente_referencia = next(iter(clientes_activos), cliente_maestro)

            if cliente_referencia and cliente and cliente_referencia.casefold() != cliente.casefold():
                return False, (
                    f"La ODP {numero_odp} ya está registrada para el cliente: {cliente_referencia}. "
                    f"Verifica el número de ODP antes de asignar."
                )
        else:
            # No existe ninguna asignación activa ni finalizada.
            # Si `odps` conserva un cliente antiguo, se trata de un registro maestro
            # huérfano/pendiente y se permite reutilizar la ODP con el cliente nuevo.
            if cliente_maestro and cliente and cliente_maestro.casefold() != cliente.casefold():
                ok_reactivar = self.commit_db(
                    """
                    UPDATE odps
                    SET cliente=:cliente,
                        estado='PENDIENTE',
                        maquina_asignada=NULL,
                        prioridad='NORMAL',
                        updated_at=(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City')
                    WHERE id=:id
                    """,
                    {"cliente": cliente, "id": odp_id}
                )
                if not ok_reactivar:
                    return False, "No fue posible actualizar el registro antiguo de la ODP."
                cliente_maestro = cliente

        # ============================================================
        # FECHAS Y ESTADO
        # ============================================================

        estado_inicial = (
            "EN ROUTER"
            if tipo_proceso == "SOLO CORTE"
            else "EN PROCESO"
        )

        fecha_asig = self.ahora_mexico()

        fecha_estimada = (
            fecha_asig
            + timedelta(
                minutes=float(min_total)
            )
        )

        # ============================================================
        # GUARDAR ASIGNACIÓN
        # ============================================================

        ok = self.commit_db(
            """
            INSERT INTO odp_asignaciones (
                odp_id,
                numero_odp,
                cliente,
                material,
                maquina_asignada,
                maquina_router,
                requiere_corte,
                tipo_proceso,
                cantidad_m2,
                cantidad_laminas,
                pasadas,
                tinta_blanca,
                day_night,
                tipo_corte,
                cantidad_cortes,
                tiempo_produccion_min,
                tiempo_corte_min,
                tiempo_estimado_min,
                fecha_estimada_finalizacion,
                metros_lineales, ancho_material_m, cantidad_copias, modo_velocidad,
                doble_saturacion, prioridad,
                estado,
                fecha_asignacion,
                usuario_asignacion,
                created_at,
                updated_at
            )
            VALUES (
                :odp_id,
                :numero_odp,
                :cliente,
                :material,
                :maquina,
                :maquina_router,
                :requiere_corte,
                :tipo_proceso,
                :cantidad_m2,
                :cantidad_laminas,
                :pasadas,
                :tinta_blanca,
                :day_night,
                :tipo_corte,
                :cantidad_cortes,
                :min_imp,
                :min_corte,
                :min_total,
                :fecha_estimada,
                :metros_lineales, :ancho_material_m, :cantidad_copias, :modo_velocidad,
                :doble_saturacion, :prioridad,
                :estado,
                :fecha_asig,
                :usuario,
                :fecha_asig,
                :fecha_asig
            )
            """,
            {
                "odp_id": odp_id,
                "numero_odp": numero_odp,
                "cliente": cliente,
                "material": material,
                "maquina": maquina,
                "maquina_router": maquina_router,

                "requiere_corte": bool(
                    requiere_corte
                ),

                "tipo_proceso": tipo_proceso,

                "cantidad_m2": float(
                    cantidad_m2 or 0
                ),

                "cantidad_laminas": int(
                    cantidad_laminas or 0
                ),

                "pasadas": pasadas,

                "tinta_blanca": bool(
                    tinta_blanca
                ),

                "day_night": bool(
                    day_night
                ),

                "tipo_corte": tipo_corte,

                "cantidad_cortes": int(
                    cantidad_cortes or 0
                ),

                "min_imp": float(
                    min_imp
                ),

                "min_corte": float(
                    min_corte
                ),

                "min_total": float(
                    min_total
                ),

                "fecha_estimada": fecha_estimada,
                "metros_lineales": float(metros_lineales or 0),
                "ancho_material_m": 1.52 if material == "FLEXIBLE" else float(ancho_material_m or 1.52),
                "cantidad_copias": max(1, int(cantidad_copias or 1)),
                "modo_velocidad": modo_velocidad,
                "doble_saturacion": bool(doble_saturacion),
                "prioridad": prioridad,

                "estado": estado_inicial,

                "fecha_asig": fecha_asig,

                "usuario": usuario
            }
        )

        if not ok:
            return False, (
                "No fue posible guardar la asignación "
                "de producción."
            )

        # ============================================================
        # ACTUALIZAR ODP MAESTRA
        # ============================================================

        maquina_maestra = (
            maquina
            or maquina_router
        )

        self.commit_db(
            """
            UPDATE odps
            SET
                estado='EN PROCESO',
                maquina_asignada=:maquina,
                prioridad=:prioridad,
                fecha_asignacion=
                    COALESCE(
                        fecha_asignacion,
                        :fecha
                    ),
                usuario_asignacion=
                    COALESCE(
                        usuario_asignacion,
                        :usuario
                    ),
                updated_at=:fecha
            WHERE numero_odp=:odp
            """,
            {
                "maquina": maquina_maestra,
                "prioridad": prioridad,
                "fecha": fecha_asig,
                "usuario": usuario,
                "odp": numero_odp
            }
        )

        self.query_db.clear()

        # ============================================================
        # MENSAJE FINAL
        # ============================================================

        modo_texto = (
            "Máxima"
            if modo_velocidad == "MAXIMA"
            else "Estándar"
        )

        return True, (
            f"ODP {numero_odp} asignada correctamente. "
            f"Prioridad: {self.etiqueta_prioridad_odp(prioridad)} · "
            f"Velocidad: {modo_texto} · "
            f"Impresión: {self.formatear_duracion(min_imp)} · "
            f"Corte: {self.formatear_duracion(min_corte)} · "
            f"Total: {self.formatear_duracion(min_total)} · "
            f"final estimado: "
            f"{fecha_estimada.strftime('%d/%m/%Y %H:%M')}"
        )

    def registrar_odp(self, numero_odp, cliente, usuario):
        """Registra una ODP nueva o reutiliza una ODP sin asignaciones vigentes.

        La tabla maestra `odps` puede conservar registros antiguos después de una
        cancelación/eliminación. Por eso una coincidencia en `odps` no significa
        por sí sola que la ODP siga ocupada. Solo bloqueamos si existe una
        asignación activa o finalizada.
        """
        numero_odp = str(numero_odp).strip()
        cliente = str(cliente).strip()

        if not numero_odp:
            return False, "El número de ODP es obligatorio."
        if not cliente:
            return False, "El cliente es obligatorio."

        existente = self.query_db("""
            SELECT id, numero_odp, cliente, estado, maquina_asignada
            FROM odps
            WHERE numero_odp = :odp
            LIMIT 1
        """, {"odp": numero_odp})

        if existente.empty:
            ok = self.commit_db("""
                INSERT INTO odps (
                    numero_odp, cliente, estado, maquina_asignada,
                    fecha_asignacion, usuario_asignacion, created_at, updated_at
                )
                VALUES (
                    :odp, :cliente, 'PENDIENTE', NULL, NULL, NULL,
                    (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'),
                    (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City')
                )
            """, {"odp": numero_odp, "cliente": cliente})

            if ok:
                self.query_db.clear()
                return True, f"ODP {numero_odp} registrada. Ahora puedes asignarla a una máquina."
            return False, "No fue posible registrar la ODP."

        registro = existente.iloc[0]
        odp_id = int(registro["id"])
        cliente_db = str(registro.get("cliente") or "").strip()

        asignaciones = self.query_db("""
            SELECT id, cliente, estado, fecha_finalizacion
            FROM odp_asignaciones
            WHERE odp_id=:odp_id OR numero_odp=:odp
            ORDER BY id DESC
        """, {"odp_id": odp_id, "odp": numero_odp})

        estados_bloqueantes = {"EN PROCESO", "EN ROUTER", "IMPRESO", "CORTADO"}
        mask_bloqueo = (
            asignaciones["estado"].fillna("").astype(str).str.strip().str.upper().isin(estados_bloqueantes)
            if not asignaciones.empty else pd.Series(dtype=bool)
        )

        if not asignaciones.empty and bool(mask_bloqueo.any()):
            clientes_bloqueantes = {
                str(v).strip()
                for v in asignaciones.loc[mask_bloqueo, "cliente"].tolist()
                if str(v or "").strip()
            }
            cliente_referencia = next(iter(clientes_bloqueantes), cliente_db)

            if cliente_referencia and cliente_referencia.casefold() != cliente.casefold():
                return False, (
                    f"La ODP {numero_odp} ya está registrada para el cliente: {cliente_referencia}. "
                    f"Verifica el número de ODP antes de asignar."
                )

            maquina = registro["maquina_asignada"] or "Sin asignar"
            estado = str(registro["estado"] or "EN PROCESO").strip().upper()
            return True, (
                f"ODP {numero_odp} ya está registrada. Se agregará la nueva asignación. "
                f"Estado actual: {estado} | Máquina: {maquina}"
            )

        # No hay asignaciones activas ni finalizadas: el registro maestro está
        # libre para reutilizarse, aunque conserve un cliente anterior.
        if cliente_db.casefold() != cliente.casefold() or str(registro["estado"] or "").strip().upper() != "PENDIENTE":
            ok_reactivar = self.commit_db("""
                UPDATE odps
                SET cliente=:cliente,
                    estado='PENDIENTE',
                    maquina_asignada=NULL,
                    prioridad='NORMAL',
                    fecha_asignacion=NULL,
                    usuario_asignacion=NULL,
                    updated_at=(CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City')
                WHERE id=:id
            """, {"cliente": cliente, "id": odp_id})
            if not ok_reactivar:
                return False, "No fue posible reactivar el registro de la ODP."

        self.query_db.clear()
        return True, (
            f"ODP {numero_odp} disponible para asignación. "
            f"Cliente: {cliente}."
        )
