"""Vista operativa de ODPs en curso y asignaciones complementarias.

Fase 19: extrae de dashboard.py la interacción operativa de ODPs,
manteniendo la misma lógica y las mismas claves de session_state.
"""

import time

import pandas as pd
import streamlit as st


def render_operacion_odp(
    *,
    todas_maquinas,
    query_db,
    obtener_odps_en_proceso,
    prioridad_es_critica,
    normalizar_prioridad_odp,
    etiqueta_prioridad_odp,
    PRIORIDADES_ODP,
    TIPOS_CORTE,
    planta_html,
    planta_escape,
    _numero_seguro,
    formatear_duracion,
    opciones_pasadas_para_maquina,
    _config_produccion_maquina,
    editar_asignacion_produccion,
    eliminar_asignacion,
    actualizar_estado_asignacion,
    maquinas_impresion,
    maquinas_router,
    LARGO_LAMINA_RIGIDA_M,
    M2_POR_LAMINA_RIGIDA,
    estimar_produccion,
    asignar_odp,
):
    with st.expander("🟢 ÓRDENES DE PRODUCCIÓN EN CURSO", expanded=False):
        # La lista de ODPs se puede actualizar manualmente para que el operador
        # tenga control sobre cuándo traer los cambios más recientes de BD.
        col_filtro_op, col_refresh_op = st.columns([4.5, 1.0], gap="small")
        with col_filtro_op:
            filtro_op = st.selectbox(
                "Filtrar por estación",
                ["Todas"] + todas_maquinas,
                key="filtro_odp_maquina_v4"
            )
        with col_refresh_op:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("🔄 Actualizar", use_container_width=True, key="btn_actualizar_odps_proceso"):
                query_db.clear()
                st.rerun()

        df_proc = obtener_odps_en_proceso(filtro_op)
        df_bomberazos = df_proc[df_proc["prioridad"].apply(prioridad_es_critica)] if (not df_proc.empty and "prioridad" in df_proc.columns) else pd.DataFrame()
        if not df_bomberazos.empty:
            nombres_alarm = ", ".join(f"ODP {x}" for x in df_bomberazos["numero_odp"].astype(str).tolist()[:5])
            if len(df_bomberazos) > 5: nombres_alarm += f" +{len(df_bomberazos)-5} más"
            planta_html(f'<div class="odp-alarm-banner">🚨 BOMBERAZO ACTIVO · {planta_escape(nombres_alarm)} · ATENCIÓN PRIORITARIA</div>')
        if df_proc.empty:
            st.info("No hay órdenes de producción activas bajo los criterios actuales.")
        else:
            planta_html('<div class="odp-process-panel"><div class="odp-process-title"><span>📋 Asignaciones activas</span><span class="odp-process-badge">' + str(len(df_proc)) + ' ACTIVAS</span></div></div>')
            # Altura fija equivalente a unas 5 tarjetas compactas. Si hay más
            # registros, el usuario se desplaza dentro del panel y el resto
            # del dashboard no se desplaza hacia abajo.
            with st.container(height=1100, border=False):
                for _, r in df_proc.iterrows():
                    aid = int(r["asignacion_id"]); numero = str(r["numero_odp"]); cliente = str(r["cliente"]); est = str(r["estado"]); corte = bool(r["requiere_corte"])
                    with st.container(border=True):
                        a, b, c = st.columns([2.0, 2.3, 1.7], gap="small")
                        with a:
                            p_odp = normalizar_prioridad_odp(r.get("prioridad"))
                            st.markdown(f"**📋 ODP {numero}** · {etiqueta_prioridad_odp(p_odp)}")
                            st.caption(f"👤 {cliente} · 🗞️ {r['material']}")
                        with b:
                            maquina_display = r['maquina_asignada'] or 'Solo ROUTER'
                            st.write(f"🖨️ {maquina_display}")
                            if corte:
                                st.caption(f"🪚 ROUTER: {r['maquina_router'] or 'SIN ASIGNAR'}")
                            # En la tarjeta de una impresora mostramos solo impresión.
                            # En la tarjeta de un Router mostramos solo corte.
                            if r.get('tiempo_produccion_min') and _numero_seguro(r.get('tiempo_produccion_min'), 0) > 0:
                                st.caption(f"🖨️ Impresión: **{formatear_duracion(_numero_seguro(r.get('tiempo_produccion_min'), 0))}**")
                            if corte and r.get('tiempo_corte_min') and _numero_seguro(r.get('tiempo_corte_min'), 0) > 0:
                                st.caption(f"🪚 Corte: **{formatear_duracion(_numero_seguro(r.get('tiempo_corte_min'), 0))}**")
                            st.caption(f"Estado: **{est}**")
                        with c:
                            if st.button("✏️ Editar parámetros", key=f"edit_{aid}", use_container_width=True):
                                st.session_state[f"editar_odp_{aid}"] = not st.session_state.get(f"editar_odp_{aid}", False)
                                st.rerun()

                            if st.session_state.get(f"editar_odp_{aid}", False):
                                with st.expander("⚙️ Ajustar ODP", expanded=True):
                                    edit_prioridad = normalizar_prioridad_odp(r.get("prioridad"))
                                    edit_prioridad = st.selectbox("🚦 Prioridad", PRIORIDADES_ODP, index=PRIORIDADES_ODP.index(edit_prioridad), key=f"edit_prioridad_{aid}", format_func=lambda x: etiqueta_prioridad_odp(x))
                                    edit_pass = r.get("pasadas", None)
                                    edit_modo = r.get("modo_velocidad", None) or "MAXIMA"
                                    edit_tipo_corte = r.get("tipo_corte", None)
                                    edit_cortes = int(r.get("cantidad_cortes", 1) or 1)

                                    pass_opts_edit = []
                                    # Las pasadas pertenecen a la IMPRESORA, no al Router.
                                    # Una ODP puede ser "IMPRESION + CORTE" y aun así debe
                                    # permitir editar las pasadas de impresión.
                                    if r.get("maquina_asignada"):
                                        pass_opts_edit = opciones_pasadas_para_maquina(
                                            r.get("maquina_asignada"),
                                            tinta_blanca=bool(r.get("tinta_blanca")),
                                            day_night=bool(r.get("day_night")),
                                        )
                                    nombre_edit_maquina = str(r.get("maquina_asignada") or "").strip().upper()
                                    if nombre_edit_maquina == "VUTEK PRO" and bool(r.get("tinta_blanca")):
                                        pass_opts_edit = [48]
                                    elif nombre_edit_maquina == "VUTEK PRO" and bool(r.get("day_night")):
                                        pass_opts_edit = [72]
                                    elif nombre_edit_maquina in {"EPSON 1", "EPSON 2"} and bool(r.get("tinta_blanca")):
                                        pass_opts_edit = [12]

                                    if pass_opts_edit:
                                        current_pass = int(r["pasadas"]) if pd.notna(r["pasadas"]) else pass_opts_edit[0]
                                        if current_pass not in pass_opts_edit:
                                            current_pass = pass_opts_edit[0]
                                        edit_pass = st.selectbox("Pasadas", pass_opts_edit, index=pass_opts_edit.index(current_pass), key=f"edit_pass_{aid}")

                                    if r["maquina_asignada"] and str(r["maquina_asignada"]).strip().upper() in {"VUTEK PRO", "VUTEK F4"}:
                                        edit_modo = st.radio(
                                            "Velocidad",
                                            ["MAXIMA", "ESTANDAR"],
                                            index=0 if str(r.get("modo_velocidad", "MAXIMA") or "MAXIMA").upper() == "MAXIMA" else 1,
                                            horizontal=True,
                                            key=f"edit_modo_{aid}",
                                            format_func=lambda x: "⚡ Máxima" if x == "MAXIMA" else "🎯 Estándar"
                                        )

                                    if corte and r.get("maquina_router"):
                                        cfg_re = _config_produccion_maquina(r.get("maquina_router"))
                                        tipos_re = cfg_re.get("tipos_corte") or TIPOS_CORTE
                                        if edit_tipo_corte not in tipos_re:
                                            edit_tipo_corte = tipos_re[0]
                                        edit_tipo_corte = st.selectbox(
                                            "Tipo de corte",
                                            tipos_re,
                                            index=tipos_re.index(edit_tipo_corte),
                                            key=f"edit_tipo_corte_{aid}"
                                        )
                                        edit_cortes = st.number_input(
                                            "Cantidad de cortes",
                                            min_value=1,
                                            value=max(1, edit_cortes),
                                            step=1,
                                            key=f"edit_cortes_{aid}"
                                        )

                                    if st.button("💾 Guardar cambios", type="primary", use_container_width=True, key=f"save_edit_{aid}"):
                                        ok_edit, msg_edit = editar_asignacion_produccion(
                                            aid,
                                            pasadas=edit_pass,
                                            prioridad=edit_prioridad,
                                            tipo_corte=edit_tipo_corte,
                                            cantidad_cortes=edit_cortes,
                                            modo_velocidad=edit_modo,
                                            usuario=st.session_state.username,
                                        )
                                        if ok_edit:
                                            st.success(msg_edit)
                                            st.session_state[f"editar_odp_{aid}"] = False
                                            time.sleep(.25)
                                            st.rerun()
                                        else:
                                            st.error(msg_edit)

                            if st.button("➕ Otra asignación", key=f"otra_{aid}", use_container_width=True):
                                st.session_state.odp_para_asignar = numero
                                st.session_state.odp_proceso_expanded = False
                                st.rerun()
                            if st.button("🗑️ Eliminar", key=f"elim_{aid}", use_container_width=True):
                                st.session_state[f"confirmar_eliminar_{aid}"] = True
                                st.rerun()
                        if st.session_state.get(f"confirmar_eliminar_{aid}", False):
                            st.warning(f"¿Eliminar la asignación de la ODP {numero}? Se registrará como cancelación.")
                            y, n = st.columns(2)
                            with y:
                                if st.button("Sí, eliminar asignación", key=f"conf_elim_{aid}", type="primary", use_container_width=True):
                                    ok, msg = eliminar_asignacion(aid, st.session_state.username)
                                    st.session_state[f"confirmar_eliminar_{aid}"] = False
                                    if ok: st.success(msg)
                                    else: st.error(msg)
                                    time.sleep(.2); st.rerun()
                            with n:
                                if st.button("Cancelar", key=f"cancel_elim_{aid}", use_container_width=True):
                                    st.session_state[f"confirmar_eliminar_{aid}"] = False
                                    st.rerun()
                        if est == "EN PROCESO":
                            if st.button("🟦 MARCAR IMPRESO", key=f"imp_{aid}", type="primary", use_container_width=True):
                                ok, msg = actualizar_estado_asignacion(aid, "IMPRESO", st.session_state.username)
                                if ok: st.success(msg)
                                else: st.error(msg)
                                time.sleep(.2); st.rerun()
                        elif est == "EN ROUTER":
                            if st.button("🟩 MARCAR CORTADO / FINALIZAR", key=f"cut_{aid}", type="primary", use_container_width=True):
                                ok, msg = actualizar_estado_asignacion(aid, "CORTADO", st.session_state.username)
                                if ok: st.success(msg)
                                else: st.error(msg)
                                time.sleep(.2); st.rerun()

    # ============================================================
    # OTRA ASIGNACIÓN PARA LA MISMA ODP
    # ============================================================
    if st.session_state.get("odp_para_asignar"):
        odp_sel = st.session_state.odp_para_asignar
        df_o = query_db(
            "SELECT numero_odp, cliente FROM odps WHERE numero_odp=:o",
            {"o": odp_sel}
        )

        if not df_o.empty:
            cliente_odp = str(df_o.iloc[0]["cliente"] or "")

            planta_html(
                f"""<div class="assign-hero"><div class="assign-kicker">Asignación complementaria</div><div class="assign-title">➕ ODP {planta_escape(odp_sel)}</div><div class="assign-subtitle">{planta_escape(cliente_odp)} · Asigna una nueva parte sin modificar las asignaciones existentes.</div></div>"""
            )

            tipo2 = st.radio(
                "Ruta complementaria",
                ["IMPRESION", "IMPRESION + CORTE", "SOLO CORTE"],
                horizontal=True,
                key=f"tipo2_{odp_sel}"
            )
            solo2 = tipo2 == "SOLO CORTE"
            corte2 = tipo2 in {"IMPRESION + CORTE", "SOLO CORTE"}

            x1, x2 = st.columns(2)
            with x1:
                if solo2:
                    m2 = None
                    st.info("🪚 **Solo corte:** no se asignará impresora.")
                else:
                    m2 = st.selectbox("🖨️ Impresora", maquinas_impresion, key=f"m2_{odp_sel}")
            with x2:
                mat2 = st.selectbox("🗞️ Material", ["FLEXIBLE", "RÍGIDO", "VINIL", "PAPEL COUCHÉ", "GENERAL"], key=f"mat2_{odp_sel}")

            prioridad2 = st.selectbox("🚦 Prioridad de la asignación", PRIORIDADES_ODP, key=f"prioridad2_{odp_sel}", format_func=lambda x: etiqueta_prioridad_odp(x))

            if corte2:
                router2 = st.selectbox(
                    "🔧 Router CNC",
                    maquinas_router if maquinas_router else ["Sin ROUTER"],
                    key=f"router2_{odp_sel}"
                )
            else:
                router2 = None
                st.markdown('<div class="route-note">✓ Ruta sin corte · no requiere Router</div>', unsafe_allow_html=True)

            cantidad_m2_2 = 0.0
            laminas2 = 0
            pasadas2 = None
            blanco2 = False
            dn2 = False
            doble_saturacion2 = False

            if not solo2:
                q1, q2, q3 = st.columns(3)
                cfg_m2_form = _config_produccion_maquina(m2)
                ancho2 = _numero_seguro(cfg_m2_form.get("ancho_referencia_m"), 1.52) or 1.52
                if mat2 == "FLEXIBLE":
                    with q1:
                        metros2 = st.number_input("Metros lineales", min_value=0.0, step=0.5, key=f"metros2_{odp_sel}")
                    cantidad_copias2 = int(metros2) if metros2 >= 1 else (1 if metros2 > 0 else 0)
                    cantidad_m2_2 = float(metros2 * ancho2)
                    with q2:
                        st.metric("Copias calculadas", cantidad_copias2)
                    with q3:
                        st.metric("Ancho estándar", f"{ancho2:.2f} m")
                elif mat2 == "RÍGIDO":
                    with q1:
                        laminas2 = st.number_input("Láminas · 1.22 × 2.44 m", min_value=0, step=1, key=f"laminas2_{odp_sel}")
                    cantidad_m2_2 = float(laminas2 * M2_POR_LAMINA_RIGIDA)
                    with q2:
                        st.metric("Copias", int(laminas2 or 0))
                    with q3:
                        st.metric("Área", f"{cantidad_m2_2:.2f} m²")
                else:
                    with q1:
                        cantidad_m2_2 = st.number_input("Cantidad (m²)", min_value=0.0, step=1.0, key=f"m2_2_{odp_sel}")
                    with q3:
                        st.metric("Área", f"{cantidad_m2_2:.2f} m²")

                pass_options2 = opciones_pasadas_para_maquina(
                    m2,
                    tinta_blanca=bool(r.get("tinta_blanca")),
                    day_night=bool(r.get("day_night")),
                )
                if pass_options2:
                    p1, p2, p3 = st.columns(3)
                    with p1:
                        pasadas2 = st.selectbox("Pasadas", pass_options2, key=f"pasadas2_{odp_sel}")
                    with p2:
                        if "vutek" in str(m2).lower() and "pro" in str(m2).lower():
                            blanco2 = st.checkbox("🎨 Tinta blanca a registro (×2)", key=f"blanco2_{odp_sel}")
                    with p3:
                        if "vutek" in str(m2).lower() and "pro" in str(m2).lower():
                            dn2 = st.checkbox("🌗 Day & Night (×3)", key=f"dn2_{odp_sel}")

            if (
                m2
                and str(m2).strip().upper() == "DURST 312"
                and not solo2
            ):
                doble_saturacion2 = st.checkbox(
                    "🔥 Doble saturación",
                    key=f"doble_sat2_{odp_sel}"
                )
                if pasadas2 is None:
                    pasadas2 = 4

            tipo_corte2 = None
            cantidad_cortes2 = 0
            if corte2:
                c1, c2 = st.columns([2.2, 1.2])
                with c1:
                    cfg_router2 = _config_produccion_maquina(router2)
                    tipos_router2 = cfg_router2.get("tipos_corte") or TIPOS_CORTE
                    tipo_corte2 = st.selectbox("Tipo de corte", tipos_router2, key=f"tc2_{odp_sel}")
                with c2:
                    cantidad_cortes2 = st.number_input("Cantidad de cortes", min_value=1, value=1, step=1, key=f"nc2_{odp_sel}")

            ml2 = float(metros2) if mat2 == "FLEXIBLE" else (float(laminas2) * LARGO_LAMINA_RIGIDA_M if mat2 == "RÍGIDO" else 0.0)
            copias2 = cantidad_copias2 if mat2 == "FLEXIBLE" else (int(laminas2 or 0) if mat2 == "RÍGIDO" else 1)
            modo2 = "MAXIMA"
            if m2 and str(m2).strip().upper() in {"VUTEK PRO", "VUTEK F4"}:
                modo2 = st.radio(
                    "Velocidad",
                    ["MAXIMA", "ESTANDAR"],
                    horizontal=True,
                    key=f"modo2_{odp_sel}",
                    format_func=lambda x: "⚡ Máxima" if x == "MAXIMA" else "🎯 Estándar"
                )

            mi2, mc2, mt2 = estimar_produccion(
                m2, router2 if corte2 else None, mat2, tipo2,
                cantidad_m2_2, laminas2, pasadas2, blanco2, dn2,
                tipo_corte2, cantidad_cortes2,
                modo_velocidad=modo2,
                metros_lineales=ml2, cantidad_copias=copias2, ancho_material_m=ancho2,
                doble_saturacion=doble_saturacion2
            )
            if mt2 > 0:
                if corte2:
                    planta_html(
                        f"""<div class="time-summary"><div class="time-summary-label">⏱️ Tiempo estimado de esta asignación</div><div class="time-summary-main">🏁 {formatear_duracion(mt2)}</div><div class="time-summary-detail">🖨️ Impresión: <strong>{formatear_duracion(mi2)}</strong> &nbsp; · &nbsp; 🪚 Corte: <strong>{formatear_duracion(mc2)}</strong></div></div>"""
                    )
                else:
                    planta_html(
                        f"""<div class="time-summary"><div class="time-summary-label">⏱️ Tiempo estimado</div><div class="time-summary-main">🖨️ {formatear_duracion(mi2)}</div><div class="time-summary-detail">Ruta: <strong>Solo impresión</strong> · Sin tiempo de Router</div></div>"""
                    )
            else:
                st.info("Complete los campos de cantidad para calcular el tiempo de impresión.")

            z1, z2 = st.columns(2)
            with z1:
                guardar2 = st.button("🚀 ENVIAR A PRODUCCIÓN", type="primary", use_container_width=True, key=f"guardar2_{odp_sel}")
            with z2:
                cerrar2 = st.button("Cancelar", use_container_width=True, key=f"cerrar2_{odp_sel}")

            if cerrar2:
                st.session_state.odp_para_asignar = None
                st.rerun()

            if guardar2:
                if not solo2 and not m2:
                    st.error("Debe seleccionar una impresora.")
                elif corte2 and (not maquinas_router or router2 == "Sin ROUTER"):
                    st.error("Debe seleccionar un Router.")
                elif not solo2 and cantidad_m2_2 <= 0:
                    st.error("La cantidad de producción debe ser mayor que cero.")
                else:
                    ok, msg = asignar_odp(
                        odp_sel, m2, cliente_odp, st.session_state.username,
                        mat2, corte2, router2 if corte2 else None,
                        tipo2, cantidad_m2_2, laminas2, pasadas2,
                        blanco2, dn2, tipo_corte2, cantidad_cortes2,
                        modo2, ml2, copias2, ancho2,
                        doble_saturacion=doble_saturacion2,
                        prioridad=prioridad2,
                    )
                    if ok:
                        st.success(msg)
                        st.session_state.odp_para_asignar = None
                        time.sleep(.25)
                        st.rerun()
                    else:
                        st.error(msg)
