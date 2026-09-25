"""Entry point compatible con Streamlit Cloud.

La implementación de arranque vive en :mod:`dashboard.bootstrap`.
"""

from pathlib import Path
import sys

# Streamlit ejecuta este archivo directamente; en ese modo el directorio
# `dashboard/` puede quedar como primer elemento de sys.path y el paquete
# `dashboard` no siempre es resoluble desde el directorio raíz del proyecto.
# Aseguramos explícitamente la raíz antes de importar el bootstrap.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.bootstrap import run_dashboard

run_dashboard()
