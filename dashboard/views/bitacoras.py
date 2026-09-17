"""Vista de Bitácora Anual de Mantenimiento."""

import base64
import io
import os
import tempfile
import time
from datetime import datetime

import pandas as pd
import pytz
import streamlit as st
from fpdf import FPDF
from PIL import Image


class PDFBitacora(FPDF):
    def __init__(self, maq_nombre, anio):
        super().__init__()
        self.maq_nombre = maq_nombre
        self.anio = anio

    def header(self):
        self.set_fill_color(240, 244, 248)
        self.set_draw_color(26, 54, 93)
        self.set_line_width(0.6)
        self.rect(10, 10, 190, 22, style='DF')
        self.set_xy(10, 12)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(26, 54, 93)
        self.cell(190, 8, txt="LIBRO DE BITÁCORA Y MANTENIMIENTO", align='C', ln=True)
        self.set_xy(10, 20)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(44, 82, 130)
        self.cell(190, 6, txt=f"Equipo: {self.maq_nombre}   |   Año: {self.anio}", align='C', ln=True)
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(85, 85, 85)
        self.cell(100, 10, txt=f"Bitácora Oficial de Mantenimiento - {self.maq_nombre}", align='L')
        self.cell(90, 10, txt=f"Página {self.page_no()} de {{nb}}", align='R')


def render_bitacora(
    machine_configs,
    query_db,
    commit_db,
    ahora_mexico,
):
    st.header("📖 Bitácora Anual de Mantenimiento")

    col_sel1, col_sel2 = st.columns(2)
    maq_bitacora = col_sel1.selectbox(
        "Seleccionar Equipo:", list(machine_configs.keys()), key="maq_bitacora"
    )

    anio_actual = datetime.now(pytz.timezone('America/Mexico_City')).year
    lista_anios = list(range(anio_actual - 1, anio_actual + 3))
    anio_consulta = col_sel2.selectbox(
        "Año del libro (Consulta):", lista_anios, index=1, key="anio_bitacora"
    )

    with st.expander("➕ Registrar Nuevo Mantenimiento", expanded=False):
        st.write("🏷️ **Fotografía del Tag de Tinta (Opcional)**")
        metodo_foto = st.radio(
            "¿Cómo deseas adjuntar la foto?",
            ["Subir archivo", "Usar cámara"],
            horizontal=True,
            key="radio_foto_tag",
        )

        tag_file = None
        if metodo_foto == "Usar cámara":
            tag_file = st.camera_input("Toma la foto del tag directamente", key="cam_tag_uploader")
        else:
            tag_file = st.file_uploader(
                "Sube la imagen del tag",
                type=["jpg", "png", "jpeg"],
                key="file_tag_uploader",
            )

        with st.form("form_nueva_bitacora", clear_on_submit=True):
            st.subheader(f"Nuevo registro para {maq_bitacora}")

            c_form1, c_form2 = st.columns(2)
            fecha_ejecucion = c_form1.date_input(
                "Fecha del Mantenimiento",
                datetime.now(pytz.timezone('America/Mexico_City')).date(),
            )
            tipo_mant = c_form2.selectbox(
                "Tipo de Intervención",
                ["Preventivo", "Correctivo", "Cambio de Piezas", "Limpieza Profunda", "Vaciado de Tinta / Tag"],
            )

            piezas = st.text_area(
                "Piezas Reemplazadas",
                placeholder="Ej: Filtros, Damper, Cabezal H2... (Dejar en blanco si no aplica)",
            )
            notas_mant = st.text_input(
                "Observaciones / Detalles de la falla",
                placeholder="Describe el trabajo realizado",
            )
            fecha_proximo = st.date_input(
                "Programar Próximo Mantenimiento (Opcional)", value=None
            )

            submit_bitacora = st.form_submit_button(
                "💾 Guardar en Libro de Bitácora", type="primary"
            )

            if submit_bitacora:
                if not notas_mant.strip():
                    st.warning("⚠️ Es recomendable agregar una observación o detalle del trabajo.")
                else:
                    foto_b64 = None
                    if tag_file is not None:
                        foto_bytes = tag_file.getvalue()
                        if foto_bytes:
                            foto_b64 = base64.b64encode(foto_bytes).decode('utf-8')

                    query_insert = """
                        INSERT INTO bitacora_mantenimiento
                        (machine_name, tipo_mantenimiento, piezas_cambiadas, notas, fecha_ejecucion, proximo_mantenimiento, foto_tag)
                        VALUES (:m, :tipo, :piezas, :notas, :f_ejec, :f_prox, :foto)
                    """
                    params_bitacora = {
                        "m": maq_bitacora,
                        "tipo": tipo_mant,
                        "piezas": piezas if piezas.strip() else "Ninguna",
                        "notas": notas_mant,
                        "f_ejec": fecha_ejecucion,
                        "f_prox": fecha_proximo,
                        "foto": foto_b64,
                    }

                    exito = commit_db(query_insert, params_bitacora)
                    if exito:
                        if "cam_tag_uploader" in st.session_state:
                            del st.session_state["cam_tag_uploader"]
                        if "file_tag_uploader" in st.session_state:
                            del st.session_state["file_tag_uploader"]
                        st.success("✅ Registro guardado y formulario reiniciado correctamente.")
                        time.sleep(1.2)
                        st.rerun()

    st.divider()
    st.subheader(f"📖 Libro de Mantenimiento - {anio_consulta} ({maq_bitacora})")

    filtrar_por_mes = st.checkbox(
        "Filtrar por mes específico", value=False, key="check_mes_bitacora"
    )

    meses_dict = {
        "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
        "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
        "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
    }

    if filtrar_por_mes:
        col_m1, col_m2 = st.columns(2)
        mes_nombre = col_m1.selectbox(
            "Selecciona el mes:", list(meses_dict.keys()), key="select_mes_nombre"
        )
        mes_seleccionado = meses_dict[mes_nombre]
        query_consulta_bit = """
            SELECT id, tipo_mantenimiento, piezas_cambiadas, notas, fecha_ejecucion, proximo_mantenimiento, foto_tag
            FROM bitacora_mantenimiento
            WHERE machine_name = :m
              AND EXTRACT(YEAR FROM fecha_ejecucion) = :anio
              AND EXTRACT(MONTH FROM fecha_ejecucion) = :mes
            ORDER BY fecha_ejecucion DESC, id DESC
        """
        params_query = {"m": maq_bitacora, "anio": anio_consulta, "mes": mes_seleccionado}
    else:
        query_consulta_bit = """
            SELECT id, tipo_mantenimiento, piezas_cambiadas, notas, fecha_ejecucion, proximo_mantenimiento, foto_tag
            FROM bitacora_mantenimiento
            WHERE machine_name = :m
              AND EXTRACT(YEAR FROM fecha_ejecucion) = :anio
            ORDER BY fecha_ejecucion DESC, id DESC
        """
        params_query = {"m": maq_bitacora, "anio": anio_consulta}

    df_bitacora = query_db(query_consulta_bit, params_query)

    if not df_bitacora.empty:
        df_bitacora["Folio"] = range(1, len(df_bitacora) + 1)

        df_display = df_bitacora.copy()
        df_display["Tiene Tag"] = df_display["foto_tag"].notna().map({True: "📷 Sí", False: "—"})
        df_display_clean = df_display[[
            "Folio", "id", "tipo_mantenimiento", "piezas_cambiadas", "notas",
            "fecha_ejecucion", "proximo_mantenimiento", "Tiene Tag"
        ]]
        df_display_clean.columns = [
            "N° Libro", "ID Base", "Tipo", "Piezas Cambiadas", "Observaciones",
            "Fecha Ejecución", "Próximo Mantenimiento", "Foto Tag"
        ]
        st.dataframe(df_display_clean, use_container_width=True, hide_index=True)

        registros_con_foto = df_bitacora[
            df_bitacora["foto_tag"].notnull()
            & (df_bitacora["foto_tag"].astype(str).str.strip() != "")
        ]
        if not registros_con_foto.empty:
            with st.expander("📷 Ver fotografías de Tags", expanded=False):
                for _, r in registros_con_foto.iterrows():
                    try:
                        foto_guardada = r["foto_tag"]
                        if isinstance(foto_guardada, memoryview):
                            foto_guardada = foto_guardada.tobytes()
                        elif isinstance(foto_guardada, bytearray):
                            foto_guardada = bytes(foto_guardada)
                        if isinstance(foto_guardada, bytes):
                            try:
                                texto_foto = foto_guardada.decode("utf-8")
                                img_bytes = base64.b64decode(texto_foto, validate=True)
                            except Exception:
                                img_bytes = foto_guardada
                        else:
                            texto_foto = str(foto_guardada).strip()
                            if texto_foto.lower().startswith("data:image") and "," in texto_foto:
                                texto_foto = texto_foto.split(",", 1)[1]
                            texto_foto = "".join(texto_foto.split())
                            texto_foto += "=" * ((4 - len(texto_foto) % 4) % 4)
                            img_bytes = base64.b64decode(texto_foto)
                        st.image(
                            img_bytes,
                            caption=f"Folio #{r['Folio']} - {r['fecha_ejecucion']} ({r['tipo_mantenimiento']})",
                            use_container_width=True,
                        )
                    except Exception:
                        st.warning(f"No se pudo renderizar la imagen Folio #{r['Folio']}")

        with st.expander("⚙️ Opciones avanzadas (Eliminar un registro erróneo)", expanded=False):
            opciones_borrado = {
                f"Folio #{row['Folio']} (ID: {row['id']} - {row['fecha_ejecucion']})": row['id']
                for _, row in df_bitacora.iterrows()
            }
            seleccion_borrar_str = st.selectbox(
                "Selecciona el registro a eliminar:",
                options=list(opciones_borrado.keys()),
                key="del_bit_select",
            )
            if st.button("🗑️ Eliminar Registro Seleccionado", type="secondary"):
                id_a_borrar = opciones_borrado[seleccion_borrar_str]
                if commit_db("DELETE FROM bitacora_mantenimiento WHERE id = :id_reg", {"id_reg": id_a_borrar}):
                    st.success("Registro eliminado correctamente. La secuencia se actualizará automáticamente.")
                    time.sleep(1.0)
                    st.rerun()

        try:
            pdf = PDFBitacora(maq_bitacora, anio_consulta)
            pdf.alias_nb_pages()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)

            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(74, 85, 104)
            fecha_emision = ahora_mexico().strftime('%Y-%m-%d %H:%M')
            pdf.cell(95, 6, txt=f"Fecha de Emisión: {fecha_emision}", align='L')
            pdf.cell(95, 6, txt=f"Total de Registros: {len(df_bitacora)}", align='R', ln=True)
            pdf.set_draw_color(203, 213, 224)
            pdf.set_line_width(0.3)
            pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
            pdf.ln(6)

            for _, row in df_bitacora.iterrows():
                if pdf.get_y() > 240:
                    pdf.add_page()
                pdf.set_fill_color(44, 82, 130)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 9)
                folio_txt = f"N° FOLIO: #{row['Folio']}    |    FECHA: {row['fecha_ejecucion']}    |    TIPO: {row['tipo_mantenimiento']}"
                pdf.cell(190, 7, txt=folio_txt, fill=True, ln=True, align='L')

                pdf.set_draw_color(203, 213, 224)
                prox_mant = row['proximo_mantenimiento'] if pd.notna(row['proximo_mantenimiento']) else "No programado"
                datos_fila = [
                    ("Piezas Reemplazadas", str(row['piezas_cambiadas'])),
                    ("Observaciones / Detalles", str(row['notas'])),
                    ("Próximo Mantenimiento", str(prox_mant)),
                ]
                for etiqueta, valor in datos_fila:
                    pdf.set_fill_color(247, 250, 252)
                    pdf.set_font("Helvetica", "B", 8.5)
                    pdf.set_text_color(74, 85, 104)
                    pdf.cell(50, 6, txt=etiqueta, border=1, fill=True)
                    pdf.set_fill_color(255, 255, 255)
                    pdf.set_font("Helvetica", "", 8.5)
                    pdf.set_text_color(45, 55, 72)
                    pdf.cell(140, 6, txt=valor, border=1, fill=True, ln=True)

                if pd.notna(row["foto_tag"]) and str(row["foto_tag"]).strip():
                    pdf.set_fill_color(247, 250, 252)
                    pdf.set_font("Helvetica", "B", 8.5)
                    pdf.set_text_color(74, 85, 104)
                    y_antes = pdf.get_y()
                    pdf.cell(50, 20, txt="Fotografía de Tag", border=1, fill=True)
                    temp_img_name = None
                    try:
                        foto_guardada = row["foto_tag"]
                        if isinstance(foto_guardada, memoryview):
                            foto_guardada = foto_guardada.tobytes()
                        elif isinstance(foto_guardada, bytearray):
                            foto_guardada = bytes(foto_guardada)
                        if isinstance(foto_guardada, bytes):
                            try:
                                texto_foto = foto_guardada.decode("utf-8")
                                img_data = base64.b64decode(texto_foto, validate=True)
                            except Exception:
                                img_data = foto_guardada
                        else:
                            texto_foto = str(foto_guardada).strip()
                            if texto_foto.lower().startswith("data:image") and "," in texto_foto:
                                texto_foto = texto_foto.split(",", 1)[1]
                            texto_foto = "".join(texto_foto.split())
                            texto_foto += "=" * ((4 - len(texto_foto) % 4) % 4)
                            img_data = base64.b64decode(texto_foto)
                        if not img_data:
                            raise ValueError("La fotografía está vacía")
                        imagen = Image.open(io.BytesIO(img_data))
                        imagen.load()
                        if imagen.mode in ("RGBA", "LA", "P"):
                            fondo = Image.new("RGB", imagen.convert("RGBA").size, "white")
                            if imagen.mode == "P":
                                imagen = imagen.convert("RGBA")
                            fondo.paste(imagen, mask=imagen.getchannel("A") if "A" in imagen.getbands() else None)
                            imagen = fondo
                        else:
                            imagen = imagen.convert("RGB")
                        temp_img_name = os.path.join(os.getcwd(), f"temp_tag_{row['Folio']}.jpg")
                        imagen.save(temp_img_name, format="JPEG", quality=92)
                        pdf.cell(140, 20, txt="", border=1, ln=True)
                        pdf.image(temp_img_name, x=65, y=y_antes + 1, h=18)
                    except Exception:
                        pdf.cell(140, 20, txt="[Error al cargar imagen]", border=1, ln=True)
                    finally:
                        if temp_img_name and os.path.exists(temp_img_name):
                            try:
                                os.remove(temp_img_name)
                            except OSError:
                                pass
                else:
                    pdf.set_fill_color(247, 250, 252)
                    pdf.set_font("Helvetica", "B", 8.5)
                    pdf.set_text_color(74, 85, 104)
                    pdf.cell(50, 6, txt="Fotografía de Tag", border=1, fill=True)
                    pdf.set_font("Helvetica", "I", 8.5)
                    pdf.set_text_color(160, 174, 192)
                    pdf.cell(140, 6, txt="Sin tag de tinta adjunto", border=1, fill=True, ln=True)
                pdf.ln(8)

            pdf_tmp = os.path.join(
                tempfile.gettempdir(),
                f"bitacora_{os.getpid()}_{ahora_mexico().strftime('%Y%m%d%H%M%S%f')}.pdf",
            )
            try:
                pdf.output(pdf_tmp)
                with open(pdf_tmp, "rb") as _fh:
                    pdf_bytes = _fh.read()
            finally:
                try:
                    if os.path.exists(pdf_tmp):
                        os.remove(pdf_tmp)
                except OSError:
                    pass

            st.download_button(
                label=f"📥 Descargar Libro de Bitácora Oficial en PDF ({maq_bitacora})",
                data=pdf_bytes,
                file_name=f"Libro_Bitacora_{maq_bitacora}_{anio_consulta}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Error al generar el documento PDF: {e}")
