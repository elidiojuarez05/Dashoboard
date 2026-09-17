"""Vista de análisis de tests y ajuste manual de estatus.

Extraída de dashboard.py durante la Fase 5 del refactor.
"""

import json
import time

import cv2
import numpy as np
from PIL import Image
import streamlit as st
from streamlit_cropper import st_cropper


def render_analisis(
    *,
    machine_configs,
    process_smart_grid,
    commit_db,
    ahora_mexico,
):
    def ensure_cv2(img):
        if not isinstance(img, np.ndarray):
            img = np.array(img.convert("RGB"))
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img

    if 'finalizado' not in st.session_state: st.session_state.finalizado = False
    if 'ultima_salud' not in st.session_state: st.session_state.ultima_salud = 0
    if 'giro_base' not in st.session_state: st.session_state.giro_base = 0

    # 1. DEFINIR LA MÁQUINA PRIMERO para que la variable exista en todo el scope
    st.subheader("🖼️ Recorte y procesamiento del Test")
    st.divider()
    machine_selected_global = st.selectbox("Seleccione una Máquina destino (Cámara/Manual):", list(machine_configs.keys()))

    # 2. AHORA SÍ EVALUAR SI YA FINALIZÓ
    if st.session_state.finalizado:
        st.success(f"### ✅ ¡{machine_selected_global} Sincronizada!")
        st.metric("SALUD TOTAL", f"{st.session_state.ultima_salud:.2f}%")
        if st.button("🔄 Nuevo análisis"):
            st.session_state.recortes = {}
            st.session_state.finalizado = False
            st.rerun()
        st.stop()

    sensibilidad = st.slider("Sensibilidad de Nozzles", 0.01, 0.20, 0.05)
    uploaded_file = st.file_uploader("Sube un archivo manualmente", type=["jpg", "png"], key="manual_up")
    img_desde_cam = st.session_state.get("img_desde_camara", None)

    img_raw = None
    if uploaded_file is not None:
        img_raw = Image.open(uploaded_file)
        st.session_state["img_desde_camara"] = None 
    elif img_desde_cam is not None:
        img_raw = img_desde_cam

    if img_raw is not None:
        st.write("🔄 **Ajuste de Orientación**")
        c_btn1, c_btn2, c_slider = st.columns([1, 1, 2])
        with c_btn1:
            if st.button("↺ Girar 90°", use_container_width=True):
                st.session_state.giro_base = (st.session_state.giro_base + 90) % 360
        with c_btn2:
            if st.button("↻ Girar -90°", use_container_width=True):
                st.session_state.giro_base = (st.session_state.giro_base - 90) % 360
        with c_slider:
            ajuste_fino = st.slider("Ajuste fino (grados)", -15.0, 15.0, 0.0, step=0.1)

        grados_totales = st.session_state.giro_base + ajuste_fino
        img_rotated = img_raw.rotate(grados_totales, expand=True, resample=Image.BICUBIC, fillcolor="white")

        if img_rotated.size[0] > 1800:
            img_rotated.thumbnail((1800, 1800))

        col_edit, col_prev = st.columns([2, 1])
        with col_edit:
            num_h = st.number_input("Total cabezales", 1, 12, 2)
            h_id = st.selectbox("Cabezal actual", range(1, num_h + 1))
            crop_key = f"crop_{h_id}"
            llave_dinamica = f"cropper_{h_id}_{grados_totales}"

            img_crop = st_cropper(img_rotated, realtime_update=True, box_color="#FF0000", key=llave_dinamica)

            if img_crop is not None:
                st.session_state[crop_key] = img_crop

            if st.button(f"💾 Guardar H{h_id}", use_container_width=True):
                if crop_key in st.session_state:
                    st.session_state.recortes[h_id] = st.session_state[crop_key]
                    st.toast(f"Cabezal {h_id} guardado")
                else:
                    st.warning("Ajusta el recorte primero")

        with col_prev:
            st.subheader("Recortes")
            config = machine_configs[machine_selected_global]
            total_missing = 0
            total_nodes = 0
            mapas = []
        
            for idx in sorted(st.session_state.recortes.keys()):
                img_item = st.session_state.recortes[idx]
                cols_mini = st.columns([1, 2])
                with cols_mini[0]:
                    st.image(img_item, use_container_width=True)
                with cols_mini[1]:
                    try:
                        img_cv2 = ensure_cv2(img_item)
                        if config.get("type") == "epson":
                            from backend.image_processor import process_epson_final
                            porcentaje, mapa = process_epson_final(img_cv2, config)
                        else:
                            porcentaje, mapa = process_smart_grid(img_cv2, config)
                        
                        missing = int(np.count_nonzero(mapa == 0))
                        total_missing += missing
                        total_nodes += mapa.size
                        mapas.append({"id": idx, "mapa": mapa.tolist()})
                        st.metric(f"H{idx}", f"{porcentaje:.1f}%")
                        
                        if st.button("Reintentar🗑️", key=f"del_{idx}"):
                            del st.session_state.recortes[idx]
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error H{idx}")
        
            if len(st.session_state.recortes) >= num_h:
                st.divider()
                if st.button("🚀 Procesar análisis", use_container_width=True):
                    if total_nodes > 0:
                        salud = ((total_nodes - total_missing) / total_nodes) * 100
                        st.session_state.ultima_salud = salud
                        commit_db("""
                            INSERT INTO test_results (machine_name, health_score, missing_nodes, health_map, timestamp)
                            VALUES (:m, :s, :n, :map, (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'))
                        """, {"m": machine_selected_global, "s": salud, "n": total_missing, "map": json.dumps(mapas)})
                        st.session_state.finalizado = True
                        st.rerun()
    else:
        st.info("💡 sube un archivo aquí para comenzar.")

    # ==========================================
    # AJUSTE MANUAL DE ESTATUS (Movido desde tab_gestion)
    # ==========================================
    st.divider()
    st.subheader("✍️ Ajuste Manual de Estatus")
    st.info("Utilice esta sección si el análisis automático no es posible o requiere corrección inmediata.")

    with st.expander("🔧 Forzar Estatus de Máquina"):
        with st.form("form_manual_health"):
            col_m1, col_m2 = st.columns(2)
            # Aseguramos que la lista de máquinas esté disponible aquí
            todas_las_maquinas = list(machine_configs.keys())
            m_manual = col_m1.selectbox("Seleccionar Máquina", todas_las_maquinas)
            s_manual = col_m2.number_input("Porcentaje de Salud (%)", 0.0, 100.0, 100.0, step=0.1)
            comentario = st.text_input("Observaciones del equipo y Motivo del ajuste manual (opcional)", placeholder="Ej: Máquina ok / Imagen borrosa / Corrección visual")

            if st.form_submit_button("Actualizar Estatus", type="primary"):
                mapa_dummy = json.dumps([{"id": 1, "mapa": [[1]]}]) 
                ahora_local = ahora_mexico()
                params_manual = {
                    "m": m_manual, "s": s_manual, "n": 0 if s_manual == 100 else -1, 
                    "map": mapa_dummy, "c": comentario, "t": ahora_local
                }
                try:
                    commit_db("""
                        INSERT INTO test_results (machine_name, health_score, missing_nodes, health_map, timestamp, comments) 
                        VALUES (:m, :s, :n, :map, :t, :c)
                    """, params_manual)
                    st.success(f"✅ Estatus de **{m_manual}** actualizada a **{s_manual}%**")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

      


