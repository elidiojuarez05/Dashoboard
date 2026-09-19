"""Vista de Gestión Administrativa.

Extraída del controlador principal durante la Fase 7 del refactor.
La lógica funcional se conserva; las dependencias externas se reciben
explícitamente para evitar acoplamiento con dashboard.py.
"""

import hashlib
import time
from datetime import timedelta

import pandas as pd
import streamlit as st


def render_gestion(
    *,
    machine_configs,
    query_db,
    commit_db,
    ahora_mexico,
    ahora_mexico_texto,
    sql_ahora_mexico,
    generar_pdf_reporte_maquinas,
    formatear_duracion,
    numero_seguro,
):
    if st.session_state.user_role != "admin":
        st.warning("⚠️ Esta sección es exclusiva para el personal de administración.")
        st.image("https://cdn-icons-png.flaticon.com/512/7506/7506500.png", width=100)
    else:
        st.header("🛠️ Panel de Control Administrativo")
        st.divider()

        col_u1, col_u2 = st.columns(2)
        with col_u1:
            with st.expander("👤 Crear Usuarios"):
                with st.form("crear_user", clear_on_submit=True):
                    new_u = st.text_input("Usuario")
                    new_p = st.text_input("Password", type="password")
                    new_r = st.selectbox("Rol", ["operator", "admin"])
                    if st.form_submit_button("Registrar en Sistema"):
                        if new_u and new_p:
                            h_pw = hashlib.sha256(new_p.encode()).hexdigest()
                            try:
                                commit_db("INSERT INTO usuarios (username, password, role) VALUES (:u, :p, :r)", 
                                          {"u": new_u, "p": h_pw, "r": new_r})
                                st.success("Usuario creado con éxito")
                                time.sleep(1); st.rerun()
                            except:
                                st.success("USUARIO REGISTRADO EN EL SISTEMA")
    
        with col_u2:
            with st.expander("🗑️ Eliminar Usuarios"):
                users_df = query_db("SELECT username FROM usuarios")
                if not users_df.empty:
                    users_df.columns = [c.lower() for c in users_df.columns]
                    lista_nombres = [u for u in users_df['username'].tolist() if u != st.session_state.username]
                    if lista_nombres:
                        u_eliminar = st.selectbox("Seleccionar usuario para borrar", lista_nombres, key=f"sb_del_{len(lista_nombres)}")
                        confirm = st.checkbox("Confirmo eliminación permanente", key="conf_del")
                        if st.button("Eliminar Usuario", type="secondary"):
                            if confirm:
                                if commit_db("DELETE FROM usuarios WHERE username=:u", {"u": u_eliminar}):
                                    st.success(f"Usuario {u_eliminar} borrado")
                                    time.sleep(1)
                                    st.rerun()
                            else:
                                st.warning("Debes marcar la casilla de confirmación")
                    else:
                        st.info("No hay otros usuarios para eliminar.")
                else:
                    st.info("No se encontraron usuarios.")
    
        st.divider()
        st.subheader("📈 Rendimiento General (Últimos 7 días)")
        ahora_admin = ahora_mexico()
        f_inicio = (ahora_admin - timedelta(days=7)).date()
        f_fin = ahora_admin.date()
        df_stats = query_db("""
            SELECT machine_name, health_score, timestamp 
            FROM test_results 
            WHERE timestamp::date >= :fi AND timestamp::date <= :ff
        """, {"fi": f_inicio, "ff": f_fin})

        todas_las_maquinas = list(machine_configs.keys())

        if not df_stats.empty:
            df_stats['health_score'] = pd.to_numeric(df_stats['health_score'], errors='coerce')
            promedio_real = df_stats.groupby("machine_name")["health_score"].mean()
            grafica_final = promedio_real.reindex(todas_las_maquinas, fill_value=0)
            st.bar_chart(grafica_final, color="#28a745")
        else:
            chart_vacio = pd.Series(0, index=todas_las_maquinas)
            st.bar_chart(chart_vacio, color="#6c757d")
            st.info("No hay registros en los últimos 7 días.")


        st.divider()
        st.subheader("Eliminación de Registros Equívocas")
        st.info("Utilice esta sección para la eliminar datos erróneas.")


        with st.expander("🗑️ Historial y Eliminación de Registros"):
            st.warning("Cuidado: Los registros eliminados no se pueden recuperar.")
            filtro_maq = st.selectbox("Filtrar historial por máquina:", ["Todas"] + todas_las_maquinas)
        
            query_historial = "SELECT id, machine_name, health_score, missing_nodes, timestamp FROM test_results "
            params_h = {}
            if filtro_maq != "Todas":
                query_historial += "WHERE machine_name = :m "
                params_h = {"m": filtro_maq}
            query_historial += "ORDER BY timestamp DESC LIMIT 15"
            ultimos_registros = query_db(query_historial, params_h)
    
            if not ultimos_registros.empty:
                h_col1, h_col2, h_col3 = st.columns([3, 2, 1])
                h_col1.caption("MÁQUINA / FECHA")
                h_col2.caption("VALOR")
                h_col3.caption("ACCIÓN")
                for _, row in ultimos_registros.iterrows():
                    with st.container():
                        c1, c2, c3 = st.columns([3, 2, 1])
                        tipo = "✍️" if row["missing_nodes"] == -1 else "📷"
                        fecha_str = row["timestamp"].strftime("%d/%m %H:%M")
                        c1.write(f"{tipo} **{row['machine_name']}**")
                        c1.caption(f"{fecha_str}")
                        c2.write(f"**{row['health_score']}%**")
                        if c3.button("🗑️", key=f"btn_del_{row['id']}"):
                            commit_db("DELETE FROM test_results WHERE id = :id", {"id": int(row['id'])})
                            st.toast(f"Registro de {row['machine_name']} eliminado")
                            time.sleep(0.5); st.rerun()
                        st.divider()
            else:
                st.info("No hay registros que coincidan con la selección.")


            
    
    
        # =========================================================
        # 11. GENERACIÓN Y REVISIÓN DE REPORTES POR MÁQUINA
        # =========================================================
        ahora_local = ahora_mexico()
        hoy = ahora_local.date()
        st.divider()
        st.subheader("📄 Generación y revisión de reportes por máquina")
        st.caption(f"🕒 Hora oficial de generación: {ahora_mexico_texto()} | Zona: America/Mexico_City (UTC-6)")

        c_r0, c_r1, c_r2 = st.columns([1.4, 1, 1])
        todas_maquinas_reporte = list(machine_configs.keys())
        filtro_reporte_maquina = c_r0.selectbox(
            "🖨️ Máquina a reportar",
            ["Todas"] + todas_maquinas_reporte,
            key="admin_filtro_maquina_reportes"
        )
        f_i = c_r1.date_input("Desde", value=hoy - timedelta(days=7), key="admin_f1")
        f_f = c_r2.date_input("Hasta", value=hoy, key="admin_f2")

        if f_i > f_f:
            st.warning("⚠️ La fecha inicial no puede ser posterior a la fecha final.")

        if st.button("📊 Preparar Archivos para Descarga", use_container_width=True) and f_i <= f_f:
            params_reporte = {"fi": f_i, "ff": f_f}
            filtro_sql_maquina = ""
            if filtro_reporte_maquina != "Todas":
                filtro_sql_maquina = " AND machine_name = :maquina "
                params_reporte["maquina"] = filtro_reporte_maquina

            # Resumen de tiempos por máquina y estado, usando fechas locales.
            query_tiempos = f"""
                SELECT machine_name AS "Máquina", estado AS "Estado",
                       ROUND(CAST(SUM(
                           COALESCE(duracion_horas, EXTRACT(EPOCH FROM ({sql_ahora_mexico} - fecha_inicio)) / 3600.0)
                       ) AS NUMERIC), 2) AS "Horas Totales"
                FROM historial_estados
                WHERE DATE(fecha_inicio) BETWEEN :fi AND :ff
                {filtro_sql_maquina}
                GROUP BY machine_name, estado
                ORDER BY machine_name, estado;
            """

            try:
                df_tiempos = query_db(query_tiempos, params_reporte)
                if df_tiempos is not None and not df_tiempos.empty:
                    st.write("### ⏱️ Resumen de Tiempos por Estado (Horas)")
                    st.dataframe(df_tiempos, use_container_width=True, hide_index=True)
                
                    # Preparar CSV independiente de tiempos para descarga
                    st.session_state.archivo_csv_tiempos = df_tiempos.to_csv(index=False).encode('utf-8-sig')
            except Exception as e:
                st.error(f"❌ Error en SQL Tiempos: {e}")
            st.session_state.archivo_pdf_listo = None 
            st.session_state.archivo_csv_listo = None
        
            filtro_debug = ""
            params_debug = {}
            if filtro_reporte_maquina != "Todas":
                filtro_debug = "WHERE m.machine_name = :maquina"
                params_debug["maquina"] = filtro_reporte_maquina

            query_debug = f"""
                SELECT TRIM(m.machine_name) as maquina, COALESCE(r.health_score::text, '---') as salud_num,
                       COALESCE(r.missing_nodes, 0) as fallas, COALESCE(r.comments, 'Sin observaciones') as notas,
                       m.estado as estado_actual
                FROM estados_maquinas m
                LEFT JOIN (
                    SELECT DISTINCT ON (machine_name) *
                    FROM test_results
                    ORDER BY machine_name, timestamp DESC
                ) r ON UPPER(TRIM(m.machine_name)) = UPPER(TRIM(r.machine_name))
                {filtro_debug}
                ORDER BY m.machine_name ASC;
            """
            df_debug = query_db(query_debug, params_debug)
            if df_debug is not None:
                st.write("### 🔍 Vista Previa de Datos Actuales")
                st.dataframe(df_debug, use_container_width=True)

            query_historico = f"""
                WITH fechas AS (SELECT generate_series(DATE(:fi), DATE(:ff), INTERVAL '1 day')::date AS fecha),
                maquinas AS (
                    SELECT machine_name, estado
                    FROM estados_maquinas
                    {"WHERE machine_name = :maquina" if filtro_reporte_maquina != "Todas" else ""}
                ),
                calendario AS (SELECT m.machine_name, m.estado as estado_manual, f.fecha FROM maquinas m CROSS JOIN fechas f),
                tests_diarios AS (
                    SELECT DISTINCT ON (machine_name, DATE(timestamp)) machine_name, DATE(timestamp) as fecha_test,
                           health_score, missing_nodes, comments
                    FROM test_results
                    WHERE timestamp::date BETWEEN :fi AND :ff
                    {"AND machine_name = :maquina" if filtro_reporte_maquina != "Todas" else ""}
                    ORDER BY machine_name, DATE(timestamp), timestamp DESC
                )
                SELECT c.machine_name AS maquina, c.fecha, COALESCE(t.health_score::text, '---') AS salud,
                       COALESCE(t.missing_nodes, 0) AS fallas, COALESCE(t.comments, 'Sin observaciones') AS notas,
                       CASE WHEN c.estado_manual != 'Operativa' THEN c.estado_manual
                            WHEN t.health_score IS NOT NULL THEN 'Operativa'
                            ELSE 'Sin actividad' END AS estado,
                       CASE WHEN c.estado_manual != 'Operativa' THEN '#dc3545'
                            WHEN t.health_score IS NOT NULL THEN '#28a745'
                            ELSE '#6c757d' END AS color_hex
                FROM calendario c
                LEFT JOIN tests_diarios t ON c.machine_name = t.machine_name AND c.fecha = t.fecha_test
                ORDER BY c.fecha DESC, c.machine_name ASC;
            """
            try:
                df_temp = query_db(query_historico, params_reporte)
                if df_temp is not None and not df_temp.empty:
                    df_temp.columns = [col.lower() for col in df_temp.columns]
                    df_temp["estado_visual"] = df_temp["estado"].apply(estado_con_icono)
                    columnas_ui = ["fecha", "maquina", "salud", "fallas", "estado_visual", "notas"]
                    st.dataframe(df_temp[columnas_ui], use_container_width=True, hide_index=True)

                    pdf_bytes = generar_pdf_reporte_maquinas(df_temp)
                    st.session_state.archivo_pdf_listo = pdf_bytes
                    csv_df = df_temp[["fecha", "maquina", "salud", "fallas", "estado", "notas"]].copy()
                    csv_df.columns = ["Fecha", "Máquina", "Salud %", "Nodos Caídos", "Estatus", "Notas"]
                    st.session_state.archivo_csv_listo = csv_df.to_csv(index=False).encode('utf-8-sig')
                    st.session_state.filas_encontradas = len(df_temp)
                    st.session_state.mostrar_descargas = True
                    st.rerun()
                else:
                    st.warning("⚠️ No se encontraron datos para los parámetros seleccionados.")
            except Exception as e:
                st.error(f"❌ Error al generar el reporte histórico: {e}")

        if st.session_state.mostrar_descargas:
            st.divider()
            nombre_maquina_reporte = "todas_las_maquinas" if filtro_reporte_maquina == "Todas" else str(filtro_reporte_maquina).replace(" ", "_")
            st.success(
                f"✅ Reporte generado: {st.session_state.get('filas_encontradas', 0)} registros | "
                f"Máquina: {filtro_reporte_maquina} | Periodo: {f_i} al {f_f}"
            )
        
            c1, c2, c3 = st.columns(3)
            with c1:
                st.download_button("💾 DESCARGAR PDF", st.session_state.archivo_pdf_listo, f"Reporte_Maquina_{nombre_maquina_reporte}_{f_i}_al_{f_f}.pdf", "application/pdf", use_container_width=True)
            with c2:
                st.download_button("📉 DESCARGAR CSV ESTADO", st.session_state.archivo_csv_listo, f"Datos_Maquina_{nombre_maquina_reporte}_{f_i}_al_{f_f}.csv", "text/csv", use_container_width=True)
            with c3:
                if 'archivo_csv_tiempos' in st.session_state:
                    st.download_button("⏱️ DESCARGAR CSV TIEMPOS", st.session_state.archivo_csv_tiempos, f"Tiempos_Maquina_{nombre_maquina_reporte}_{f_i}_al_{f_f}.csv", "text/csv", use_container_width=True)
        
            if st.button("Limpiar y Cerrar 🗑️", use_container_width=True):
                st.session_state.mostrar_descargas = False
                st.session_state.archivo_pdf_listo = None
                st.session_state.archivo_csv_listo = None
                if 'archivo_csv_tiempos' in st.session_state: del st.session_state.archivo_csv_tiempos
                st.rerun()

