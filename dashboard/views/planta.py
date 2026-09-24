"""Vista de planta y monitoreo visual de producción."""

from dashboard.utils.ui import render_html, ui_escape


def render_planta(
    tab_planta,
    *,
    machine_configs,
    current_dir,
    query_db,
    obtener_nombres_maquinas_operativas,
    obtener_maquinas_impresion,
    obtener_maquinas_router,
    es_maquina_router,
    normalizar_prioridad_odp,
    etiqueta_prioridad_odp,
    prioridad_es_critica,
    formatear_duracion,
    numero_seguro,
    render_produccion,
):
    """Renderiza la planta completa sin mover reglas de negocio."""
    with tab_planta:
        if "planta_maquina_index" not in __import__("streamlit").session_state:
            __import__("streamlit").session_state.planta_maquina_index = 0
        if "odp_para_asignar" not in __import__("streamlit").session_state:
            __import__("streamlit").session_state.odp_para_asignar = None

        render_html("""
        <style>
        :root {
            --ind-bg: #0b0f19;
            --ind-surface: #111827;
            --ind-surface-alt: #1f2937;
            --ind-border: #334155;
            --ind-border-glow: #38bdf8;
            --ind-text: #f8fafc;
            --ind-muted: #94a3b8;
            --ind-accent: #0284c7;
            --ind-success: #059669;
            --ind-warning: #d97706;
        }
        .planta-hero { background:linear-gradient(135deg,#090d16 0%,#111c33 50%,#1e1b4b 100%); border:1px solid var(--ind-border); border-radius:12px; padding:20px 24px; margin-bottom:16px; box-shadow:0 8px 24px rgba(0,0,0,.4); border-left:5px solid #0ea5e9; }
        .planta-hero h1 { margin:0; color:var(--ind-text); font-size:26px; font-weight:800; letter-spacing:.5px; }
        .planta-hero p { margin:6px 0 0; color:var(--ind-muted); font-size:13px; font-family:monospace; }
        .planta-section { font-size:18px; font-weight:800; color:var(--ind-text); margin:16px 0 4px; display:flex; align-items:center; gap:8px; }
        .planta-sub { font-size:11px; color:var(--ind-muted); margin-bottom:10px; font-family:monospace; text-transform:uppercase; letter-spacing:.8px; }
        .odp-process-panel { background:linear-gradient(145deg,rgba(15,23,42,.98),rgba(17,24,39,.96)); border:1px solid #334155; border-left:4px solid #10b981; border-radius:14px; padding:10px; margin:8px 0 14px; box-shadow:0 10px 28px rgba(0,0,0,.25); }
        .odp-process-title { display:flex; align-items:center; justify-content:space-between; gap:12px; color:#f8fafc; font:800 15px/1.2 system-ui,sans-serif; padding:4px 6px 10px; }
        .odp-process-badge { display:inline-flex; align-items:center; gap:5px; border-radius:999px; padding:4px 9px; background:rgba(16,185,129,.12); color:#6ee7b7; border:1px solid rgba(16,185,129,.35); font:700 10px monospace; }
        .machine-card { background:linear-gradient(150deg,#0f172a 0%,#111827 100%); border:1px solid var(--ind-border); border-radius:10px; overflow:hidden; box-shadow:0 6px 18px rgba(0,0,0,.3); min-height:380px; transition:border-color .2s ease; }
        .machine-card:hover { border-color:#475569; }
        .machine-head { padding:14px 16px; background:rgba(15,23,42,.7); border-bottom:1px solid var(--ind-border); display:flex; justify-content:space-between; align-items:center; }
        .machine-name { color:var(--ind-text); font-size:18px; font-weight:750; font-family:monospace; }
        .machine-type { color:var(--ind-muted); font-size:9px; text-transform:uppercase; letter-spacing:1.5px; margin-top:2px; }
        .machine-pill { background:rgba(6,78,59,.6); color:#34d399; border:1px solid #059669; border-radius:6px; padding:4px 8px; font-size:9px; font-weight:700; font-family:monospace; letter-spacing:.5px; }
        .machine-body { padding:12px 14px; }
        .machine-count { color:var(--ind-muted); font-size:10px; margin-bottom:8px; font-family:monospace; text-transform:uppercase; }
        .order-card { background:#090d16; border:1px solid var(--ind-border); border-left:3px solid #0ea5e9; border-radius:8px; padding:10px 12px; margin:8px 0; }
        .order-card.router { border-left-color:#8b5cf6; }
        .order-top { display:flex; justify-content:space-between; gap:8px; align-items:center; }
        .order-odp { color:var(--ind-text); font-size:14px; font-weight:800; font-family:monospace; }
        .order-state { font-size:8px; font-weight:800; border-radius:4px; padding:3px 6px; background:#0369a1; color:#e0f2fe; font-family:monospace; letter-spacing:.5px; }
        .order-state.router { background:#5b21b6; color:#ede9fe; }
        .order-client { color:#cbd5e1; font-size:11px; margin-top:4px; }
        .order-meta { color:var(--ind-muted); font-size:9px; margin-top:4px; font-family:monospace; }
        .machine-empty { text-align:center; padding:44px 15px; color:var(--ind-muted); }
        .machine-empty strong { display:block; color:var(--ind-text); font-size:13px; margin-top:6px; font-family:monospace; }
        .carousel-indicator { text-align:center; color:var(--ind-muted); font-size:11px; font-weight:600; font-family:monospace; padding:8px; background:rgba(15,23,42,.4); border-radius:6px; margin-top:8px; border:1px dashed var(--ind-border); }
        .planta-screen-wrap { position:relative; height:100px; border-radius:10px; overflow:hidden; margin:0 0 12px; border:1px solid var(--ind-border); background:#020617; display:flex; align-items:center; justify-content:center; }
        .planta-screen-video { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; opacity:.25; }
        .planta-screen-overlay { position:absolute; inset:0; background:linear-gradient(90deg,rgba(2,6,23,.9),rgba(2,6,23,.4),rgba(2,6,23,.9)); }
        .planta-screen-title { position:relative; z-index:2; color:var(--ind-text); font-size:20px; font-weight:900; letter-spacing:1px; font-family:monospace; text-align:center; }
        .planta-screen-card { min-height:410px; }
        </style>
        """)

        maquinas_impresion = obtener_maquinas_impresion()
        maquinas_router = obtener_maquinas_router()
        todas_maquinas = list(machine_configs.keys())
        maquinas_operativas = obtener_nombres_maquinas_operativas()

        render_produccion(
            machine_configs=machine_configs,
            current_dir=current_dir,
            query_db=query_db,
            obtener_nombres_maquinas_operativas=obtener_nombres_maquinas_operativas,
            es_maquina_router=es_maquina_router,
            normalizar_prioridad_odp=normalizar_prioridad_odp,
            etiqueta_prioridad_odp=etiqueta_prioridad_odp,
            prioridad_es_critica=prioridad_es_critica,
            formatear_duracion=formatear_duracion,
            numero_seguro=numero_seguro,
        )

        problemas = []
        for maquina in todas_maquinas:
            datos = query_db(
                "SELECT estado FROM estados_maquinas WHERE machine_name=:m",
                {"m": maquina},
            )
            estado = str(datos.iloc[0]["estado"]) if not datos.empty else "Operativa"
            if estado.strip().lower() != "operativa":
                problemas.append((maquina, estado))

        with __import__("streamlit").expander(
            f"⚠️ MÁQUINAS CON FALLA Y/O MANTENIMIENTO ({len(problemas)})",
            expanded=False,
        ):
            if not problemas:
                __import__("streamlit").success("🟢 Todos los equipos se encuentran operativos y sin reportes críticos.")
            else:
                for inicio in range(0, len(problemas), 2):
                    cols = __import__("streamlit").columns(2, gap="large")
                    for j, (maquina, estado) in enumerate(problemas[inicio:inicio + 2]):
                        with cols[j]:
                            render_html(
                                f'<div class="machine-card"><div class="machine-head"><div><div class="machine-name">⚠️ {ui_escape(maquina)}</div><div class="machine-type">{"ROUTER" if es_maquina_router(maquina) else "IMPRESIÓN"}</div></div><div class="machine-pill" style="background:#7f1d1d;color:#fca5a5;border-color:#991b1b;">⚠️ {ui_escape(estado).upper()}</div></div><div class="machine-body"><div class="machine-empty"><div style="font-size:32px">🛠️</div><strong>ESTACIÓN BLOQUEADA</strong><div>Inspeccionar bitácora de mantenimiento o falla mecánica.</div></div></div></div>'
                            )
