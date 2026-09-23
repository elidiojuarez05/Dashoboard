"""Vista del historial de ODPs finalizadas y sus exportaciones."""

import pandas as pd
import streamlit as st


def render_historial_odp(
    *,
    todas_maquinas,
    obtener_registro_odps_finalizadas,
    dataframe_to_xlsx_bytes,
    generar_pdf_odps_finalizadas,
    ahora_mexico,
    formatear_duracion,
    numero_seguro,
):
    """Renderiza el historial de ODPs conservando la UI y flujo existentes."""
    with st.expander("🔵 HISTORIAL DE ODPs FINALIZADAS Y REPORTES", expanded=False):
        col_filtro, col_fecha = st.columns(2)

        with col_filtro:
            filtro_fin = st.selectbox(
                "Filtrar historial por estación",
                ["Todas"] + todas_maquinas,
                key="filtro_final_maquina_v3",
            )

        with col_fecha:
            fecha_default = (
                ahora_mexico().date() - pd.Timedelta(days=7),
                ahora_mexico().date(),
            )
            rango_fechas = st.date_input(
                "Filtrar por rango de fechas",
                value=fecha_default,
                key="rango_fechas_odps_finalizadas",
            )

        if len(rango_fechas) != 2:
            st.warning(
                "Por favor, selecciona una fecha de inicio "
                "y una fecha de fin."
            )
            return

        fecha_inicio, fecha_fin = rango_fechas
        df_fin = obtener_registro_odps_finalizadas(
            filtro_fin,
            fecha_inicio,
            fecha_fin,
        )

        if df_fin.empty:
            st.info(
                "No existen registros de ODPs finalizadas "
                "para el filtro seleccionado."
            )
            return

        busqueda = st.text_input(
            "🔍 Buscar por número de ODP o Cliente en este rango:",
            "",
            key="buscar_odp_historial",
        )

        if busqueda:
            texto_busqueda = busqueda.strip()
            df_fin = df_fin[
                df_fin["ODP"].astype(str).str.contains(
                    texto_busqueda, case=False, na=False
                )
                |
                df_fin["Cliente"].astype(str).str.contains(
                    texto_busqueda, case=False, na=False
                )
            ]

        if df_fin.empty:
            st.warning("No se encontraron coincidencias para tu búsqueda.")
            return

        excel_data = dataframe_to_xlsx_bytes(df_fin)
        pdf_data = generar_pdf_odps_finalizadas(
            df_fin,
            filtro_fin,
            fecha_inicio,
            fecha_fin,
            ahora_mexico,
        )

        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "📄 EXPORTAR REPORTE PDF",
                pdf_data,
                f"ODPs_{fecha_inicio}_al_{fecha_fin}.pdf",
                "application/pdf",
                use_container_width=True,
                key="download_pdf_odps_finalizadas",
            )

        with d2:
            st.download_button(
                "📊 EXPORTAR DATOS EXCEL",
                excel_data,
                f"ODPs_{fecha_inicio}_al_{fecha_fin}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="download_excel_odps_finalizadas",
            )

        columnas_registro = [
            c
            for c in [
                "ODP",
                "Cliente",
                "Material",
                "Prioridad",
                "Máquina Impresión",
                "Máquina Router",
                "Ruta",
                "m²",
                "Láminas",
                "Pasadas",
                "Min total estimado",
                "Estado",
                "Finalización",
            ]
            if c in df_fin.columns
        ]
        df_tabla = df_fin[columnas_registro].copy()

        if "Min total estimado" in df_tabla.columns:
            df_tabla["Tiempo"] = df_tabla["Min total estimado"].apply(
                lambda x: formatear_duracion(numero_seguro(x))
            )
            df_tabla.drop(columns=["Min total estimado"], inplace=True)

        if "Finalización" in df_tabla.columns:
            df_tabla["Finalización"] = pd.to_datetime(
                df_tabla["Finalización"], errors="coerce"
            ).dt.strftime("%d/%m/%y %H:%M")

        st.dataframe(
            df_tabla,
            use_container_width=True,
            hide_index=True,
            height=330,
            column_config={
                "ODP": st.column_config.TextColumn("ODP", width="small"),
                "Cliente": st.column_config.TextColumn("Cliente", width="medium"),
                "Material": st.column_config.TextColumn("Material", width="small"),
                "Prioridad": st.column_config.TextColumn("Prioridad", width="small"),
                "Tiempo": st.column_config.TextColumn("Tiempo", width="small"),
                "Estado": st.column_config.TextColumn("Estado", width="small"),
            },
        )
