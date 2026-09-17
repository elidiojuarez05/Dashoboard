"""Report-generation services extracted from the dashboard entry point."""

import pandas as pd
from fpdf import FPDF

from dashboard.utils.dates import ahora_mexico_texto

def generar_pdf_reporte_maquinas(df):
    """Genera el PDF del reporte de máquinas sin depender de generate_pdf_report.

    Compatibilidad FPDF/FPDF2: output(dest="S") puede devolver bytearray;
    se normaliza explícitamente a bytes para que Streamlit pueda descargarlo.
    """
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 9, "REPORTE DE ESTATUS DE MAQUINAS", ln=True, align="C")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 6, f"Generado: {ahora_mexico_texto('%d/%m/%Y %H:%M:%S')} | America/Mexico_City", ln=True, align="C")
    pdf.ln(4)

    columnas = [
        ("Fecha", 25),
        ("Maquina", 48),
        ("Salud %", 20),
        ("Nodos", 18),
        ("Estatus", 34),
        ("Notas", 125),
    ]

    pdf.set_fill_color(27, 38, 59)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    for encabezado, ancho in columnas:
        pdf.cell(ancho, 7, encabezado, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "", 7.5)

    def limpiar(valor):
        if valor is None:
            return ""
        try:
            if pd.isna(valor):
                return ""
        except Exception:
            pass
        texto = str(valor)
        return texto.encode("latin-1", "replace").decode("latin-1")

    def fecha(valor):
        if valor is None:
            return ""
        try:
            if pd.isna(valor):
                return ""
        except Exception:
            pass
        if hasattr(valor, "strftime"):
            try:
                return valor.strftime("%d/%m/%y")
            except Exception:
                pass
        return limpiar(valor)[:10]

    for _, row in df.iterrows():
        valores = [
            fecha(row.get("fecha")),
            limpiar(row.get("maquina")),
            limpiar(row.get("salud")),
            limpiar(row.get("fallas")),
            limpiar(row.get("estado")),
            limpiar(row.get("notas")),
        ]
        for (encabezado, ancho), valor in zip(columnas, valores):
            limite = max(8, int(ancho / 1.55))
            pdf.cell(ancho, 6, valor[:limite], border=1)
        pdf.ln()

    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 7, f"Registros: {len(df)}", ln=True, align="R")

    salida = pdf.output(dest="S")
    return bytes(salida)
