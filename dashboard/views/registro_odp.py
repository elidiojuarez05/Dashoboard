"""Vista de registro y asignación de ODP.

Extracción estructural de la fase 4: conserva la lógica y la UI del baseline.
"""

import time

import streamlit as st


def render_registro_odp(
    *,
    LARGO_LAMINA_RIGIDA_M,
    PRIORIDADES_ODP,
    TIPOS_CORTE,
    _config_produccion_maquina,
    _numero_seguro,
    asignar_odp,
    calcular_area_produccion,
    estimar_produccion,
    etiqueta_prioridad_odp,
    formatear_duracion,
    maquinas_impresion,
    maquinas_impresion_compatibles,
    maquinas_router,
    opciones_pasadas_para_maquina,
    planta_html,
    registrar_odp,
    routers_compatibles,
):
        with st.expander("📥 NUEVO INGRESO Y ASIGNACIÓN DE ODP", expanded=False):
            planta_html(
                '<div class="planta-sub" style="margin-bottom:14px;">'
                "Registro rápido de producción · captura solo los datos necesarios "
                "y calcula el tiempo cuando el operador lo solicita."
                "</div>"
            )

            with st.container(border=True):
                tipo_proceso = st.radio(
                    "Ruta de producción",
                    ["IMPRESION", "IMPRESION + CORTE", "SOLO CORTE"],
                    horizontal=True,
                    key="form_tipo_proceso",
                )
                solo_corte = tipo_proceso == "SOLO CORTE"
                requiere_corte = tipo_proceso in {"IMPRESION + CORTE", "SOLO CORTE"}

                st.divider()

                c1, c2, c3 = st.columns([1.0, 2.0, 1.2], gap="medium")
                with c1:
                    nueva_odp = st.text_input("No. ODP", placeholder="66788", key="form_odp_num")
                with c2:
                    nuevo_cliente = st.text_input("Cliente", placeholder="Nombre del cliente", key="form_odp_cliente")
                with c3:
                    material = st.selectbox(
                        "Material",
                        ["FLEXIBLE", "RÍGIDO", "VINIL", "PAPEL COUCHÉ", "GENERAL"],
                        key="form_material",
                    )
                prioridad = st.selectbox(
                    "🚦 Prioridad de la ODP",
                    PRIORIDADES_ODP,
                    index=0,
                    key="form_prioridad",
                    format_func=lambda x: etiqueta_prioridad_odp(x),
                )

            col_izq, col_der = st.columns(2, gap="medium")

            maquinas_imp_compatibles = maquinas_impresion_compatibles(material, maquinas_impresion)
            maquinas_router_compatibles = routers_compatibles(material, maquinas_router)

            # Inicialización de variables de control
            cantidad_m2 = 0.0
            cantidad_laminas = 0
            metros_lineales = 0.0
            cantidad_copias = 1
            ancho_material = 1.52
            pasadas = None
            tinta_blanca = False
            day_night = False
            doble_saturacion = False
            router_sel = None
            maquina_imp = None

            with col_izq:
                with st.container(border=True):
                    st.markdown("##### 🏭 Estaciones")
                    if not solo_corte:
                        opciones_imp = maquinas_imp_compatibles or ["Sin máquinas compatibles"]
                        maquina_imp = st.selectbox("🖨️ Impresora asignada", opciones_imp, key="form_maquina_imp")
                        if maquina_imp and maquina_imp != "Sin máquinas compatibles":
                            cfg_imp_form = _config_produccion_maquina(maquina_imp)
                            ancho_material = _numero_seguro(cfg_imp_form.get("ancho_referencia_m"), 1.52) or 1.52

                    if requiere_corte:
                        opciones_router = maquinas_router_compatibles or ["Sin ROUTER compatible"]
                        router_sel = st.selectbox("🔧 Router CNC", opciones_router, key="form_router")
                    else:
                        router_sel = None
                        st.markdown('<div class="route-note">✓ Ruta solo impresión · no requiere Router</div>', unsafe_allow_html=True)

                    nombre_imp_upper = str(maquina_imp or "").strip().upper()
                    es_vutek_pro = nombre_imp_upper == "VUTEK PRO"
                    es_epson = nombre_imp_upper in {"EPSON 1", "EPSON 2"}
                    if (es_vutek_pro or es_epson) and not solo_corte:
                        st.markdown("##### 🎨 Procesos especiales")
                        b_col, d_col = st.columns(2) if es_vutek_pro else (st.columns(1)[0], None)
                        with b_col:
                            tinta_blanca = st.checkbox("🎨 Tinta blanca a registro", key="form_blanco")
                        if es_vutek_pro:
                            with d_col:
                                day_night = st.checkbox("🌗 Day & Night", key="form_daynight")
                            if tinta_blanca and day_night:
                                st.warning("Seleccione solo un proceso especial: Tinta blanca a registro o Day & Night.")
                        elif es_epson:
                            st.caption("Calibración real: 50 m × 1.52 m · 12 pasadas = 12 h por rollo")
                    pass_options = opciones_pasadas_para_maquina(maquina_imp, tinta_blanca=tinta_blanca, day_night=day_night) if (not solo_corte and maquina_imp and maquina_imp != "Sin máquinas compatibles") else None
                    if pass_options and not solo_corte:
                        st.markdown("##### ⚙️ Impresión")
                        if tinta_blanca and es_vutek_pro:
                            pass_options = [48]
                        elif day_night and es_vutek_pro:
                            pass_options = [72]
                        elif tinta_blanca and es_epson:
                            pass_options = [12]
                        pasadas = st.selectbox("Pasadas", pass_options, key="form_pasadas")
                    #modo de velocidades estandar maximo
                    modo_velocidad = "MAXIMA"

                    if (
                        maquina_imp
                        and str(maquina_imp).strip().upper() in {
                            "VUTEK PRO",
                            "VUTEK F4"
                        }
                    ):
                        st.markdown("##### 🚀 Velocidad de producción")

                        modo_velocidad = st.radio(
                            "Modo",
                            ["MAXIMA", "ESTANDAR"],
                            horizontal=True,
                            key="form_modo_velocidad",
                            format_func=lambda x: (
                                "⚡ Máxima"
                                if x == "MAXIMA"
                                else "🎯 Estándar"
                            )
                        )

                    if (
                        maquina_imp
                        and str(maquina_imp).strip().upper() == "DURST 312"
                        and not solo_corte
                    ):
                        doble_saturacion = st.checkbox(
                            "🔥 Doble saturación",
                            key="form_doble_saturacion"
                        )
                        # Referencia segura si un rerun deja momentáneamente
                        # la selección de pasadas sin valor.
                        if pasadas is None:
                            pasadas = 4


            with col_der:
                with st.container(border=True):
                    st.markdown("##### 📐 Cantidad y Cortes")

                    if not solo_corte:
                        # EVALUACIÓN EXCLUSIVA SEGÚN EL MATERIAL SELECCIONADO
                        if material == "PAPEL COUCHÉ":
                            cantidad_laminas = st.number_input("Cantidad de hojas", min_value=0, step=1, key="form_hojas_xerox")
                            cantidad_m2 = 0.0 # No aplica m2 directo
                        elif material == "FLEXIBLE":
                            metros_lineales = st.number_input(
                                "Metros lineales", min_value=0.0, step=0.5, key="form_metros"
                            )
                            cantidad_copias = int(metros_lineales) if metros_lineales >= 1 else (1 if metros_lineales > 0 else 0)
                            restante = max(0.0, metros_lineales - int(metros_lineales))
                            st.caption(
                                f"Ancho estándar de la máquina: **{ancho_material:.2f} m** · Copias calculadas: **{cantidad_copias}**"
                                + (f" · excedente: **{restante:.2f} m**" if restante > 0 else "")
                            )
                            cantidad_m2 = metros_lineales * ancho_material
                        elif material == "RÍGIDO":
                            cantidad_laminas = st.number_input("Láminas · 1.22 × 2.44 m", min_value=0, step=1, key="form_laminas")
                            cantidad_copias = max(1, int(cantidad_laminas or 1))
                            metros_lineales = float(cantidad_laminas or 0) * LARGO_LAMINA_RIGIDA_M
                            cantidad_m2 = calcular_area_produccion("RÍGIDO", cantidad_laminas=cantidad_laminas)
                        else:
                            cantidad_m2 = st.number_input("Cantidad a producir (m²)", min_value=0.0, step=1.0, key="form_m2")
                            cantidad_laminas = 0

                    tipo_corte, cantidad_cortes = None, 1
                    if requiere_corte:
                        cfg_router = _config_produccion_maquina(router_sel)
                        tipos_router = cfg_router.get("tipos_corte") or TIPOS_CORTE
                        tipo_corte = st.selectbox("Tipo de corte", tipos_router, key="form_tipo_corte")
                        cantidad_cortes = st.number_input("Cantidad de cortes", min_value=1, value=1, step=1, key="form_cantidad_cortes")

            # Firma de los parámetros actuales. El resumen de tiempo solo se considera
            # vigente después de pulsar "CALCULAR" y vuelve a quedar pendiente si el
            # operador modifica cualquier parámetro.
            calculo_firma_actual = repr((
                maquina_imp, router_sel, material, tipo_proceso,
                float(cantidad_m2 or 0), int(cantidad_laminas or 0),
                pasadas, bool(tinta_blanca), bool(day_night),
                tipo_corte, int(cantidad_cortes or 0), modo_velocidad,
                float(metros_lineales or 0), int(cantidad_copias or 0),
                float(ancho_material or 0), bool(doble_saturacion),
                prioridad,
            ))

            # Cálculo seguro de tiempos
            min_imp_prev, min_corte_prev, min_total_prev = estimar_produccion(
            maquina_imp if not solo_corte else None,
            router_sel if requiere_corte else None,
            material,
            tipo_proceso,
            cantidad_m2,
            cantidad_laminas,
            pasadas,
            tinta_blanca,
            day_night,
            tipo_corte,
            cantidad_cortes,
            modo_velocidad,
            metros_lineales, cantidad_copias, ancho_material,
            doble_saturacion=doble_saturacion,
        )

            calculo_vigente = (
                st.session_state.get("calculo_ingreso_firma") == calculo_firma_actual
            )

            if calculo_vigente and min_total_prev > 0:
                if requiere_corte:
                    planta_html(
                        f"""<div class="time-summary"><div class="time-summary-label">⏱️ Tiempo estimado de producción</div><div class="time-summary-main">🏁 {formatear_duracion(min_total_prev)}</div><div class="time-summary-detail">🖨️ Impresión: <strong>{formatear_duracion(min_imp_prev)}</strong> &nbsp; · &nbsp; 🪚 Corte: <strong>{formatear_duracion(min_corte_prev)}</strong></div></div>"""
                    )
                else:
                    planta_html(
                        f"""<div class="time-summary"><div class="time-summary-label">⏱️ Tiempo estimado</div><div class="time-summary-main">🖨️ {formatear_duracion(min_imp_prev)}</div><div class="time-summary-detail">Ruta: <strong>Solo impresión</strong> · Sin tiempo de Router</div></div>"""
                    )
            elif not calculo_vigente:
                st.info("🧮 Complete los parámetros y pulse **CALCULAR** para actualizar el tiempo estimado.")

            # El cálculo manual queda al final del formulario, justo antes de registrar.
            # Así el operador puede completar todos los parámetros y calcular una sola vez.
            col_calcular, col_registrar = st.columns([1.0, 2.2], gap="medium")
            with col_calcular:
                calcular_ingreso = st.button(
                    "🧮 CALCULAR",
                    use_container_width=True,
                    key="btn_calcular_nuevo_ingreso",
                )
            with col_registrar:
                registrar_asignar = st.button(
                    "🚀 REGISTRAR Y ENVIAR A PRODUCCIÓN",
                    type="primary",
                    use_container_width=True,
                    key="btn_registro_produccion",
                )

            if calcular_ingreso:
                # Guardamos exactamente los parámetros actuales. En el siguiente render
                # el resumen se mostrará solo si sigue correspondiendo a estos valores.
                st.session_state["calculo_ingreso_firma"] = calculo_firma_actual
                st.rerun()




            if registrar_asignar:
                odp_n = str(nueva_odp).strip()
                cli = str(nuevo_cliente).strip()

                if not odp_n or not cli:
                    st.error("Debe especificar No. ODP y Cliente.")

                elif not solo_corte and (
                    not maquina_imp or maquina_imp == "Sin máquinas"
                ):
                    st.error("Debe seleccionar una máquina de impresión.")

                elif requiere_corte and (
                    not maquinas_router_compatibles or router_sel == "Sin ROUTER compatible"
                ):
                    st.error("Debe seleccionar un Router.")

                elif not solo_corte and cantidad_m2 <= 0 and cantidad_laminas <= 0 and metros_lineales <= 0:
                    st.error("La cantidad de producción debe ser mayor que cero.")

                elif requiere_corte and not tipo_corte:
                    st.error("Debe seleccionar el tipo de corte.")

                else:
                    ok_reg, msg_reg = registrar_odp(
                        odp_n,
                        cli,
                        st.session_state.username
                    )

                    if ok_reg:
                        ok_asig, msg_asig = asignar_odp(
                            odp_n,
                            maquina_imp,
                            cli,
                            st.session_state.username,
                            material,
                            requiere_corte,
                            router_sel if requiere_corte else None,
                            tipo_proceso,
                            cantidad_m2,
                            cantidad_laminas,
                            pasadas,
                            tinta_blanca,
                            day_night,
                            tipo_corte,
                            cantidad_cortes,
                            modo_velocidad,
                            metros_lineales, cantidad_copias, ancho_material,
                            doble_saturacion=doble_saturacion,
                            prioridad=prioridad,
                        )

                        if ok_asig:
                            st.success(msg_asig)
                            time.sleep(.25)
                            st.rerun()
                        else:
                            st.error(msg_asig)
                    else:
                        st.error(msg_reg)

    # ============================================================
