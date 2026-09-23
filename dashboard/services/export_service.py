"""Servicios de exportación de datos.

Mantiene la generación de XLSX autocontenidos sin acoplar la interfaz
Streamlit a detalles del formato Office Open XML.
"""
from datetime import datetime
import io
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd


def dataframe_to_xlsx_bytes(df):
    """Convierte un DataFrame a bytes XLSX sin depender de un motor externo."""
    if df is None:
        df = pd.DataFrame()
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    buf = io.BytesIO()
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ET.register_namespace("", ns)

    def val(v):
        if v is None or pd.isna(v):
            return ""
        if isinstance(v, (pd.Timestamp, datetime)):
            return v.strftime("%d/%m/%Y %H:%M:%S")
        if isinstance(v, bool):
            return "Sí" if v else "No"
        return str(v)

    sheet = ET.Element(f"{{{ns}}}worksheet")
    data = ET.SubElement(sheet, f"{{{ns}}}sheetData")
    rows = [list(df.columns)] + df.astype(object).where(pd.notna(df), None).values.tolist()

    for ri, row in enumerate(rows, 1):
        er = ET.SubElement(data, f"{{{ns}}}row", {"r": str(ri)})
        for ci, value in enumerate(row, 1):
            n = ci
            letters = ""
            while n:
                n, rem = divmod(n - 1, 26)
                letters = chr(65 + rem) + letters
            c = ET.SubElement(er, f"{{{ns}}}c", {"r": f"{letters}{ri}", "t": "inlineStr"})
            isel = ET.SubElement(c, f"{{{ns}}}is")
            t = ET.SubElement(isel, f"{{{ns}}}t")
            t.text = val(value)

    sheet_xml = ET.tostring(sheet, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>''',
        )
        z.writestr(
            "_rels/.rels",
            '''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''',
        )
        z.writestr(
            "xl/workbook.xml",
            '''<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="ODPs Acabadas" sheetId="1" r:id="rId1"/></sheets></workbook>''',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>''',
        )
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()
