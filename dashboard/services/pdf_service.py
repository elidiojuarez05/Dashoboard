"""Servicios para generar reportes PDF.

La capa de interfaz solo prepara los datos y presenta el botón de descarga;
la construcción del PDF queda aislada aquí.
"""
import os
import tempfile

import pandas as pd
from fpdf import FPDF


def _pdf_text(valor):
    """Convierte un valor a texto compatible con Helvetica/latin-1."""
    if valor is None:
        return ""
    try:
        if pd.isna(valor):
            return ""
    except Exception:
        pass
    return str(valor).encode("latin-1", "replace").decode("latin-1")


def _formatear_fecha_pdf(valor):
    """Formatea fechas para las celdas del PDF."""
    if valor is None:
        return ""
    try:
        if pd.isna(valor):
            return ""
    except Exception:
        pass
    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%d/%m/%y %H:%M")
        except (ValueError, TypeError, AttributeError):
            return ""
    return str(valor)[:16]


def generar_pdf_odps_finalizadas(df, filtro_estacion, fecha_inicio, fecha_fin, ahora_mexico):
    """Genera el PDF del historial de ODPs finalizadas y devuelve bytes."""
    if df is None:
        df = pd.DataFrame()

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, "REGISTRO DE ODPs FINALIZADAS", ln=True, align="C")

    pdf.set_font("Helvetica", "", 8)
    texto_filtro = "Todas" if filtro_estacion == "Todas" else str(filtro_estacion)
    texto_periodo = (
        f"Periodo: {fecha_inicio.strftime('%d/%m/%Y')} "
        f"al {fecha_fin.strftime('%d/%m/%Y')}"
    )
    pdf.cell(
        0,
        6,
        f"Generado: {ahora_mexico().strftime('%d/%m/%Y %H:%M')} "
        f"| Estación: {texto_filtro} | {texto_periodo}",
        ln=True,
    )
    pdf.ln(3)

    headers = [
        "ODP", "Cliente", "Material", "Máq. Impresión", "Máq. Router",
        "Prioridad", "Corte", "Estado", "Impresión", "Router", "Finalización",
    ]
    widths = [16, 39, 20, 33, 28, 27, 11, 22, 27, 27, 27]

    pdf.set_font("Helvetica", "B", 6.5)
    for encabezado, ancho in zip(headers, widths):
        pdf.cell(ancho, 6, _pdf_text(encabezado), border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 6.2)
    for _, row in df.iterrows():
        requiere_corte = row.get("Requiere corte", "")
        if isinstance(requiere_corte, bool):
            corte_txt = "SI" if requiere_corte else "NO"
        else:
            corte_txt = _pdf_text(requiere_corte)

        valores = [
            row.get("ODP", ""),
            row.get("Cliente", ""),
            row.get("Material", ""),
            row.get("Máquina Impresión", ""),
            row.get("Máquina Router", "") or "—",
            row.get("Prioridad", "NORMAL"),
            corte_txt,
            row.get("Estado", ""),
            _formatear_fecha_pdf(row.get("Impresión")),
            _formatear_fecha_pdf(row.get("Router")),
            _formatear_fecha_pdf(row.get("Finalización")),
        ]

        for valor, ancho in zip(valores, widths):
            texto = _pdf_text(valor)
            limite = max(8, int(ancho / 1.6))
            pdf.cell(ancho, 5.5, texto[:limite], border=1)
        pdf.ln()

    pdf_tmp = os.path.join(
        tempfile.gettempdir(),
        f"odps_finalizadas_{os.getpid()}_{ahora_mexico().strftime('%Y%m%d%H%M%S%f')}.pdf",
    )
    try:
        pdf.output(pdf_tmp)
        with open(pdf_tmp, "rb") as archivo_pdf:
            return archivo_pdf.read()
    finally:
        try:
            if os.path.exists(pdf_tmp):
                os.remove(pdf_tmp)
        except OSError:
            pass
