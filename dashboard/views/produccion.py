"""Vista de Render Producción.

Fase 3 del refactor: extracción estructural del bloque existente de
Render Producción. La lógica y el HTML se mantienen deliberadamente.
"""

import base64
import os
import textwrap
from datetime import timedelta
from html import escape

import pandas as pd
import streamlit as st


def render_produccion(
    *,
    machine_configs,
    current_dir,
    query_db,
    obtener_nombres_maquinas_operativas,
    es_maquina_router,
    normalizar_prioridad_odp,
    etiqueta_prioridad_odp,
    prioridad_es_critica,
    formatear_duracion,
    numero_seguro,
):
    """Renderiza la vista de producción conservando el comportamiento actual."""

    MACHINE_CONFIGS = machine_configs
    _numero_seguro = numero_seguro

    if "planta_maquina_index" not in st.session_state:
        st.session_state.planta_maquina_index = 0
    if "planta_vista" not in st.session_state:
        st.session_state.planta_vista = "🎬 Render automático"
    if "planta_solo_con_odp" not in st.session_state:
        st.session_state.planta_solo_con_odp = False

    def planta_escape(valor):
        return escape("" if valor is None else str(valor))

    def planta_html(contenido):
        contenido = textwrap.dedent(str(contenido)).strip()
        if hasattr(st, "html"):
            st.html(contenido)
        else:
            st.markdown(contenido, unsafe_allow_html=True)

    # ============================================================
    # RENDER PRODUCCIÓN — CONTROL ROOM INDUSTRIAL
    # ============================================================
    planta_html("""
    <style>
    :root{
        --pr-bg:#0b111a;
        --pr-panel:#121d2a;
        --pr-panel2:#172536;
        --pr-line:#34485d;
        --pr-text:#f7fbff;
        --pr-muted:#a8b8c9;
        --pr-blue:#4cc9f0;
        --pr-green:#39e58c;
        --pr-orange:#ffbf3f;
        --pr-purple:#b99cff;
        --pr-cyan:#67e8f9;
    }

    .prod-shell{
        background:
            radial-gradient(circle at 8% 0%, rgba(103,232,249,.10), transparent 24%),
            radial-gradient(circle at 92% 0%, rgba(56,189,248,.12), transparent 30%),
            linear-gradient(180deg,#101b28 0%,#0b111a 100%);
        border:1px solid #3a5066;
        border-radius:14px;
        padding:18px;
        margin-bottom:14px;
        box-shadow:0 14px 40px rgba(0,0,0,.30), inset 0 1px 0 rgba(255,255,255,.025);
    }
    .prod-title{
        display:flex; align-items:center; justify-content:space-between;
        gap:18px; padding-bottom:12px; border-bottom:1px solid #233143;
    }
    .prod-title-main{color:#ffffff;font:900 23px/1.1 Arial,sans-serif;letter-spacing:.5px;text-shadow:0 1px 2px rgba(0,0,0,.55)}
    .prod-title-sub{color:#c0cfde;font:800 10px/1.4 monospace;text-transform:uppercase;letter-spacing:1.2px;margin-top:5px}
    .prod-live{
        color:#86efac;background:rgba(22,101,52,.22);border:1px solid #166534;
        border-radius:999px;padding:6px 10px;font:800 9px monospace;letter-spacing:.8px;white-space:nowrap
    }
    .prod-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px}
    .prod-kpi{background:linear-gradient(145deg,rgba(25,40,56,.96),rgba(14,25,37,.96));border:1px solid #3a5066;border-radius:8px;padding:10px 11px;box-shadow:inset 0 1px 0 rgba(255,255,255,.035)}
    .prod-kpi-label{color:#aebed0;font:900 8px monospace;letter-spacing:1px;text-transform:uppercase}
    .prod-kpi-value{color:#f8fafc;font:800 19px monospace;margin-top:3px}
    .prod-kpi-value.blue{color:#7dd3fc}.prod-kpi-value.green{color:#86efac}.prod-kpi-value.orange{color:#fcd34d}

    .prod-machine{
        background:linear-gradient(160deg,#182737 0%,#101b28 100%);
        border:1px solid #40566b;border-radius:12px;overflow:hidden;
        height:365px;min-height:365px;box-shadow:0 12px 30px rgba(0,0,0,.32), inset 0 1px 0 rgba(255,255,255,.025);
        position:relative;
    }
    .prod-machine:before{
        content:"";display:block;height:5px;background:linear-gradient(90deg,#00b8ff,#4cc9f0,#39e58c);box-shadow:0 0 12px rgba(76,201,240,.28);
    }
    .prod-machine.router:before{background:linear-gradient(90deg,#8b5cf6,#b99cff,#e0c7ff);box-shadow:0 0 12px rgba(185,156,255,.25)}
    .prod-head{padding:14px 15px;background:linear-gradient(180deg,rgba(25,39,54,.98),rgba(18,29,42,.96));border-bottom:1px solid #3b5064}
    .prod-head-row{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
    .prod-machine-name{color:#ffffff;font:900 18px monospace;letter-spacing:.2px;text-shadow:0 1px 2px rgba(0,0,0,.6)}
    .prod-machine-type{color:#b2c2d3;font:900 8px monospace;text-transform:uppercase;letter-spacing:1.4px;margin-top:3px}
    .prod-status{border-radius:5px;padding:4px 7px;font:800 8px monospace;letter-spacing:.5px}
    .prod-status.ok{color:#86efac;background:#052e1a;border:1px solid #166534}
    .prod-status.router{color:#ddd6fe;background:#2e1065;border:1px solid #6d28d9}
    .prod-body{padding:12px 14px}
    .prod-lane{
        display:flex;justify-content:space-between;align-items:center;
        color:#b9c9d9;font:900 8px monospace;text-transform:uppercase;letter-spacing:1px;
        padding-bottom:8px;border-bottom:1px dashed #40566b;margin-bottom:8px
    }
    .prod-count{color:#dbeafe;background:#0c2740;border:1px solid #17456d;border-radius:5px;padding:3px 6px}
    .prod-order{
        background:linear-gradient(145deg,#132233,#0e1926);border:1px solid #3b5064;border-left:4px solid #16b9f4;
        border-radius:7px;padding:10px 10px;margin:7px 0;box-shadow:0 4px 12px rgba(0,0,0,.20)
    }
    .prod-order.router{border-left-color:#a78bfa;background:linear-gradient(145deg,#211b35,#151525)}
    .prod-order-top{display:flex;justify-content:space-between;gap:8px;align-items:center}
    .prod-order-list{display:flex;flex-direction:column;gap:5px;max-height:282px;overflow-y:auto;padding-right:4px;scrollbar-width:thin}
    .prod-order-list::-webkit-scrollbar{width:6px}
    .prod-order-list::-webkit-scrollbar-track{background:rgba(255,255,255,.03);border-radius:6px}
    .prod-order-list::-webkit-scrollbar-thumb{background:#3b5369;border-radius:6px}
    .prod-list-item{display:grid;grid-template-columns:1.05fr 2.2fr 1fr;gap:8px;align-items:center;min-height:42px;padding:7px 9px;background:linear-gradient(145deg,#132233,#0e1926);border:1px solid #334b61;border-left:3px solid #16b9f4;border-radius:6px}
    .prod-list-item.router{border-left-color:#a78bfa;background:linear-gradient(145deg,#211b35,#151525)}
    .prod-list-odp{color:#ffffff;font:900 11px monospace;white-space:nowrap}
    .prod-list-client{color:#dce7f1;font:700 9px Arial,sans-serif;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .prod-list-time{color:#aebfd0;font:800 8px monospace;text-align:right;white-space:nowrap}
    .prod-list-time strong{color:#dbeafe}
    .prod-list-note{color:#91a6ba;font:700 8px monospace;padding:2px 3px 4px;text-transform:uppercase;letter-spacing:.5px}
    .prod-odp{color:#f8fafc;font:800 13px monospace}
    .prod-state{color:#bae6fd;background:#082f49;border:1px solid #075985;border-radius:4px;padding:3px 5px;font:800 7px monospace}
    .prod-state.router{color:#ddd6fe;background:#3b0764;border-color:#6d28d9}
    .prod-client{color:#e0e9f2;font:600 10px Arial,sans-serif;margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .prod-meta{color:#aebfd0;font:900 9px monospace;margin-top:5px}
    .prod-empty{min-height:245px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;color:#a9bacb}
    .prod-empty-icon{font-size:35px;opacity:.55}
    .prod-empty strong{color:#f1f6fb;font:900 13px monospace;margin-top:7px;text-shadow:0 1px 2px rgba(0,0,0,.55)}
    .prod-empty span{color:#a9bacb;font:800 9px monospace;margin-top:4px}
    .prod-footer{text-align:center;color:#a9bacb;font:900 8px monospace;letter-spacing:1px;padding:8px;border:1px dashed #3a5066;border-radius:6px;margin-top:10px;background:rgba(16,29,43,.55)}
    .prod-alert{
        color:#fcd34d;background:rgba(120,53,15,.2);border:1px solid #92400e;
        border-radius:7px;padding:8px 10px;font:800 9px monospace;margin-top:10px
    }
    .prod-machine-alert{
        display:flex;align-items:center;justify-content:center;
        color:#fff;background:linear-gradient(90deg,#7f1d1d,#dc2626,#7f1d1d);
        border-bottom:1px solid #ef4444;padding:7px 10px;
        font:900 10px monospace;letter-spacing:1px;text-transform:uppercase;
        box-shadow:0 0 16px rgba(239,68,68,.30);
        animation:alarmBanner .8s infinite;
    }
    .odp-priority-badge{display:inline-flex;align-items:center;justify-content:center;gap:5px;border-radius:999px;padding:3px 7px;font:900 8px monospace;letter-spacing:.4px;white-space:nowrap}
    .odp-priority-normal{color:#bfdbfe;background:rgba(30,64,175,.18);border:1px solid #2563eb}
    .odp-priority-urgente{color:#fde68a;background:rgba(146,64,14,.24);border:1px solid #d97706}
    .odp-priority-bomberazo{color:#fff;background:linear-gradient(90deg,#991b1b,#ef4444,#991b1b);border:2px solid #ff5a5a;box-shadow:0 0 12px rgba(239,68,68,.55);padding:4px 9px;font-size:9px;animation:odpBomberazo .75s infinite}
    /* La alerta vive en la ODP; la tarjeta de la estación conserva su diseño normal. */
    .prod-order.priority-bomberazo,.prod-list-item.priority-bomberazo{border-left-color:#ef4444;border-color:#ef4444;box-shadow:0 0 12px rgba(239,68,68,.18)}
    .odp-alarm-banner{display:flex;align-items:center;justify-content:center;gap:12px;color:#fff;background:linear-gradient(90deg,#7f1d1d,#b91c1c,#7f1d1d);border:2px solid #ef4444;border-radius:10px;padding:12px 16px;margin:10px 0;font:900 13px monospace;letter-spacing:.8px;box-shadow:0 0 24px rgba(239,68,68,.28);animation:alarmBanner 1s infinite}
    @keyframes odpBomberazo{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.48;transform:scale(1.03)}}
    @keyframes barBomberazo{50%{opacity:.35}}
    @keyframes orderBomberazo{0%,100%{border-color:#ef4444}50%{border-color:#7f1d1d}}
    @keyframes alarmBanner{0%,100%{opacity:1}50%{opacity:.62}}
    /* MODO PANTALLA GRANDE / TV DE PRODUCCIÓN: más contraste y lectura a distancia */
    @media(min-width:1400px){
        .prod-shell{padding:22px;border-radius:16px}
        .prod-title-main{font-size:27px}
        .prod-title-sub{font-size:11px}
        .prod-machine{height:405px;min-height:405px;border-width:2px}
        .prod-machine:before{height:6px}
        .prod-head{padding:17px 18px}
        .prod-machine-name{font-size:21px}
        .prod-machine-type{font-size:9px}
        .prod-status{font-size:9px;padding:5px 8px}
        .prod-body{padding:15px 17px}
        .prod-lane{font-size:9px}
        .prod-count{font-size:10px}
        .prod-order{padding:12px 12px;margin:9px 0}
        .prod-odp{font-size:15px}
        .prod-state{font-size:8px}
        .prod-client{font-size:11px}
        .prod-meta{font-size:10px}
        .prod-empty strong{font-size:15px}
        .prod-empty span{font-size:10px}
    }

    @media(max-width:900px){
        .prod-kpis{grid-template-columns:repeat(2,1fr)}
        .prod-title{align-items:flex-start;flex-direction:column}
    }
    </style>
    """)

    todas_maquinas = list(MACHINE_CONFIGS.keys())
    maquinas_operativas = obtener_nombres_maquinas_operativas()

    # Estado operativo se consulta una sola vez para el resumen visual.
    estados_operativos = {}
    for _m in todas_maquinas:
        _d = query_db(
            "SELECT estado FROM estados_maquinas WHERE machine_name=:m",
            {"m": _m}
        )
        estados_operativos[_m] = str(_d.iloc[0]["estado"]) if not _d.empty else "Operativa"

    # Conteo global de ODP activas para el encabezado.
    df_activas_global = query_db("""
        SELECT estado, COUNT(*) AS total
        FROM odp_asignaciones
        WHERE estado IN ('EN PROCESO','EN ROUTER')
        GROUP BY estado
    """)
    n_proceso = int(df_activas_global.loc[df_activas_global["estado"]=="EN PROCESO","total"].iloc[0]) if not df_activas_global.empty and (df_activas_global["estado"]=="EN PROCESO").any() else 0
    n_router = int(df_activas_global.loc[df_activas_global["estado"]=="EN ROUTER","total"].iloc[0]) if not df_activas_global.empty and (df_activas_global["estado"]=="EN ROUTER").any() else 0

    # ============================================================
    # CONTROLES DE VISUALIZACIÓN
    # ============================================================
    # El video de fondo pertenece a Render Producción.
    # Fase 2 movió Render Estatus a views/estatus.py, por lo que
    # video_b64 ya no existe en este ámbito. Se carga localmente
    # para conservar exactamente el comportamiento anterior.
    ruta_video_planta = os.path.join(current_dir, "assets", "video.mp4")
    try:
        with open(ruta_video_planta, "rb") as _video_file:
            video_b64 = base64.b64encode(_video_file.read()).decode()
    except Exception:
        video_b64 = None

    if video_b64:
        planta_html(f'''<div class="planta-screen-wrap">
            <video autoplay muted loop playsinline class="planta-screen-video">
                <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
            </video>
            <div class="planta-screen-overlay"></div>
            <div class="planta-screen-title">🏭 MONITOREO DE PRODUCCIÓN EN TIEMPO REAL</div>
        </div>''')

    # Panel plegable para mantener el tablero limpio y dejar los controles
    # disponibles cuando el operador los necesite.
    with st.expander("⚙️ CONTROLES Y RESUMEN DEL RENDER", expanded=False):
        c_v1, c_v2  = st.columns([1.5, 2.5])
        with c_v1:
            vista_prod = st.selectbox(
                "Visualización",
                ["🎬 Render automático", "🧩 Mostrar todas"],
                key="planta_vista"
            )
        with c_v2:
            solo_con_odp = st.checkbox(
                "Solo Máquinas con ODP",
                key="planta_solo_con_odp"
            )


        maquinas_base = maquinas_operativas[:]
        if solo_con_odp:
            maquinas_filtradas = []
            for _m in maquinas_base:
                _router = es_maquina_router(_m)
                if _router:
                    _q = query_db(
                        "SELECT COUNT(*) AS n FROM odp_asignaciones WHERE maquina_router=:m AND estado='EN ROUTER'",
                        {"m": _m}
                    )
                else:
                    _q = query_db(
                        "SELECT COUNT(*) AS n FROM odp_asignaciones WHERE maquina_asignada=:m AND estado='EN PROCESO'",
                        {"m": _m}
                    )
                if not _q.empty and int(_q.iloc[0]["n"]) > 0:
                    maquinas_filtradas.append(_m)
            maquinas_base = maquinas_filtradas

        planta_html(f"""
        <div class="prod-kpis">
          <div class="prod-kpi"><div class="prod-kpi-label">Máquinas en Operación</div><div class="prod-kpi-value green">{len(maquinas_operativas)}</div></div>
          <div class="prod-kpi"><div class="prod-kpi-label">ODP en impresión</div><div class="prod-kpi-value blue">{n_proceso}</div></div>
          <div class="prod-kpi"><div class="prod-kpi-label">ODP en router</div><div class="prod-kpi-value">{n_router}</div></div>
          <div class="prod-kpi"><div class="prod-kpi-label">Máquinas fuera de servicio</div><div class="prod-kpi-value orange">{len(todas_maquinas)-len(maquinas_operativas)}</div></div>
        </div>
        """)

    if not maquinas_base:
        planta_html("""
        <div class="prod-machine" style="margin-top:12px;">
          <div class="prod-empty">
            <div class="prod-empty-icon">📭</div>
            <strong>NO HAY ESTACIONES PARA MOSTRAR</strong>
            <span>Verifique el estado operativo o desactive el filtro "Solo estaciones con ODP".</span>
          </div>
        </div>
        """)
    else:
        # --------------------------------------------------------
        # Render de una estación
        # --------------------------------------------------------
        def render_estacion_produccion(machine_name):
            router = es_maquina_router(machine_name)
            estado = estados_operativos.get(machine_name, "Operativa")

            if router:
                df_orders = query_db("""
                    SELECT numero_odp, cliente, material, estado, requiere_corte, fecha_asignacion,
                           tipo_proceso, cantidad_m2, cantidad_laminas, pasadas,
                           tinta_blanca, day_night, prioridad, tipo_corte, cantidad_cortes,
                           tiempo_produccion_min, tiempo_corte_min, tiempo_estimado_min,
                           fecha_estimada_finalizacion, fecha_impresion
                    FROM odp_asignaciones
                    WHERE maquina_router=:m AND estado='EN ROUTER'
                    ORDER BY CASE UPPER(COALESCE(prioridad, 'NORMAL')) WHEN 'BOMBERAZO' THEN 1 WHEN 'URGENTE' THEN 2 ELSE 3 END, fecha_asignacion ASC, numero_odp
                """, {"m": machine_name})
            else:
                df_orders = query_db("""
                    SELECT numero_odp, cliente, material, estado, requiere_corte, fecha_asignacion,
                           tipo_proceso, cantidad_m2, cantidad_laminas, pasadas,
                           tinta_blanca, day_night, prioridad, tipo_corte, cantidad_cortes,
                           tiempo_produccion_min, tiempo_corte_min, tiempo_estimado_min,
                           fecha_estimada_finalizacion, fecha_impresion
                    FROM odp_asignaciones
                    WHERE maquina_asignada=:m AND estado='EN PROCESO'
                    ORDER BY CASE UPPER(COALESCE(prioridad, 'NORMAL')) WHEN 'BOMBERAZO' THEN 1 WHEN 'URGENTE' THEN 2 ELSE 3 END, fecha_asignacion ASC, numero_odp
                """, {"m": machine_name})

            hay_bomberazo = (not df_orders.empty and any(prioridad_es_critica(v) for v in df_orders.get("prioridad", pd.Series(dtype=object))))
            # La tarjeta de la estación conserva siempre sus colores originales.
            # La alerta visual se concentra exclusivamente en la ODP BOMBERAZO.
            prioridad_maquina_cls = ""
            icono = "🪚" if router else "🖨️"
            tipo = "CORTE / ROUTER" if router else "IMPRESIÓN DIGITAL"
            css_tipo = "router" if router else ""
            status_cls = "router" if router else "ok"
            estado_txt = "OPERATIVA" if estado.strip().lower()=="operativa" else planta_escape(estado).upper()

            html = f"""
            <div class="prod-machine {css_tipo}{prioridad_maquina_cls}">
              <div class="prod-head">
                <div class="prod-head-row">
                  <div>
                    <div class="prod-machine-name">{icono} {planta_escape(machine_name)}</div>
                    <div class="prod-machine-type">{tipo}</div>
                  </div>
                  <div class="prod-status {status_cls}">● {estado_txt}</div>
                </div>
              </div>
              <div class="prod-body">
                <div class="prod-lane">
                  <span>{"COLA DE CORTE" if router else "COLA DE IMPRESIÓN"}</span>
                  <span class="prod-count">{len(df_orders)} ODP</span>
                </div>
            """

            if df_orders.empty:
                html += """
                <div class="prod-empty">
                  <div class="prod-empty-icon">📭</div>
                  <strong>ESTACIÓN DISPONIBLE</strong>
                  <span>Sin órdenes activas asignadas</span>
                </div>
                """
            else:
                # Con 4 o más ODP, usar lista compacta para conservar la altura.
                if len(df_orders) >= 4:
                    html += '<div class="prod-list-note">📋 Lista compacta · todas las ODP activas</div>'
                    html += '<div class="prod-order-list">'
                    for _, r in df_orders.iterrows():
                        tiempo_imp_min = _numero_seguro(r.get("tiempo_produccion_min"), 0)
                        tiempo_corte_min = _numero_seguro(r.get("tiempo_corte_min"), 0)
                        tiempo_estacion = tiempo_corte_min if router else tiempo_imp_min
                        tiempo_txt = formatear_duracion(tiempo_estacion) if tiempo_estacion > 0 else "Pendiente"
                        cliente_txt = f"{r.get('cliente', '')} · {r.get('material', '')}"
                        prioridad_item = normalizar_prioridad_odp(r.get("prioridad"))
                        clase_item = ("router " if router else "") + ("priority-bomberazo" if prioridad_item == "BOMBERAZO" else "")
                        prioridad_badge = f'<span class="odp-priority-badge odp-priority-{prioridad_item.lower()}">{planta_escape(etiqueta_prioridad_odp(prioridad_item))}</span>'
                        icono_tiempo = "🪚" if router else "🖨️"
                        html += f"""
                        <div class="prod-list-item {clase_item}">
                          <span class="prod-list-odp">ODP {planta_escape(r["numero_odp"])}</span>
                          <span class="prod-list-client">👤 {planta_escape(cliente_txt)}</span>
                          <span class="prod-list-time">{prioridad_badge} {icono_tiempo} <strong>{planta_escape(tiempo_txt)}</strong></span>
                        </div>
                        """
                    html += '</div>'
                else:
                    for _, r in df_orders.iterrows():
                        requiere = bool(r["requiere_corte"])
                        corte_txt = "ROUTER REQUERIDO" if requiere else "SIN CORTE"
                        fch = r["fecha_asignacion"]
                        try:
                            ftxt = "" if pd.isna(fch) else (fch.strftime("%d/%m %H:%M") if hasattr(fch, "strftime") else str(fch))
                        except Exception:
                            ftxt = ""
                        tiempo_imp_min = _numero_seguro(r.get("tiempo_produccion_min"), 0)
                        tiempo_corte_min = _numero_seguro(r.get("tiempo_corte_min"), 0)
                        tiempo_estacion = tiempo_corte_min if router else tiempo_imp_min
                        inicio_estacion = r.get("fecha_impresion") if router else r.get("fecha_asignacion")
                        if router and (inicio_estacion is None or pd.isna(inicio_estacion)):
                            inicio_estacion = r.get("fecha_asignacion")
                        try:
                            fin_est = (inicio_estacion + timedelta(minutes=float(tiempo_estacion))) if inicio_estacion is not None and not pd.isna(inicio_estacion) and tiempo_estacion > 0 else None
                            fin_txt = "" if fin_est is None else fin_est.strftime("%d/%m %H:%M")
                        except Exception:
                            fin_txt = ""
                        tiempo_txt = formatear_duracion(tiempo_estacion) if tiempo_estacion > 0 else "Pendiente de calibrar"
                        detalle_tiempo = f"🪚 Corte: {tiempo_txt}" if router else f"🖨️ Impresión: {tiempo_txt}"
                        prioridad_item = normalizar_prioridad_odp(r.get("prioridad"))
                        clase_prioridad = " priority-bomberazo" if prioridad_item == "BOMBERAZO" else ""
                        prioridad_badge = f'<span class="odp-priority-badge odp-priority-{prioridad_item.lower()}">{planta_escape(etiqueta_prioridad_odp(prioridad_item))}</span>'
                        if fin_txt:
                            detalle_tiempo += f" · 🏁 {fin_txt}"
                        # En el Render, el espacio donde antes aparecía
                        # "EN PROCESO / EN ROUTER" se reserva ahora para la prioridad.
                        # Así el BOMBERAZO queda visible exactamente en la zona más
                        # fácil de detectar de cada ODP.
                        distintivo_estado = prioridad_badge
                        html += f"""
                        <div class="prod-order {css_tipo}{clase_prioridad}">
                          <div class="prod-order-top">
                            <span class="prod-odp">ODP {planta_escape(r["numero_odp"])}</span>
                            <span>{distintivo_estado}</span>
                          </div>
                          <div class="prod-client">👤 {planta_escape(r["cliente"])} · 🗞️ {planta_escape(r["material"])}</div>
                          <div class="prod-meta">{"🪚" if requiere else "▣"} {corte_txt} · 🕐 {ftxt}</div>
                          <div class="prod-meta" style="margin-top:7px;"><span class="station-time"><strong>{detalle_tiempo}</strong></span></div>
                        </div>
                        """

            html += "</div></div>"
            planta_html(html)

        # ========================================================
        # MODO RENDER AUTOMÁTICO / MOSTRAR TODAS
        # ========================================================
        if vista_prod == "🎬 Render automático":
            @st.fragment(run_every="15s")
            def render_produccion_auto():
                if not maquinas_base:
                    return
                idx = st.session_state.get("planta_maquina_index", 0) % len(maquinas_base)
                visibles = maquinas_base[idx:idx+2]
                if len(visibles) < 2 and len(maquinas_base) > 1:
                    visibles += maquinas_base[:2-len(visibles)]

                cols = st.columns(2, gap="large")
                for i, m in enumerate(visibles):
                    with cols[i]:
                        render_estacion_produccion(m)

                paginas = max(1, (len(maquinas_base)+1)//2)
                planta_html(
                    f'<div class="prod-footer">BLOQUE {idx//2 + 1} / {paginas} · 2 ESTACIONES VISIBLES · ROTACIÓN AUTOMÁTICA CADA 15 SEGUNDOS</div>'
                )
                st.session_state.planta_maquina_index = (idx + 2) % len(maquinas_base)

            render_produccion_auto()

        else:
            # Vista completa: todas las estaciones operativas, sin rotación.
            for inicio in range(0, len(maquinas_base), 2):
                cols = st.columns(2, gap="large")
                for j, m in enumerate(maquinas_base[inicio:inicio+2]):
                    with cols[j]:
                        render_estacion_produccion(m)
            planta_html(
                f'<div class="prod-footer">VISTA COMPLETA · {len(maquinas_base)} ESTACIONES MOSTRADAS · SIN ROTACIÓN</div>'
            )

    # ============================================================

