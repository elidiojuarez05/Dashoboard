# Monitor de Cabezales / Producción

Dashboard Streamlit para monitoreo de máquinas, registro y seguimiento de ODPs,
estimación de producción y corte, historial y reportes.

## Arquitectura actual

- `dashboard/dashboard.py`: composición de la interfaz Streamlit y flujo de pantalla.
- `backend/config.py`: fuente única de configuración y calibraciones de máquinas.
- `backend/services/production.py`: reglas de producción, compatibilidad, áreas y tiempos.
- `backend/image_processor.py`: procesamiento de imágenes de pruebas de cabezales.
- `dashboard/assets/`: recursos visuales usados por Streamlit.
- PostgreSQL: persistencia de la aplicación actual, configurada mediante Streamlit Secrets.

El código histórico de SQLite/Flask fue retirado del árbol principal porque no forma parte
del flujo actual. Mantener el ZIP de respaldo original fuera del repositorio como copia de seguridad.

## Ejecución

```bash
streamlit run dashboard/dashboard.py
```

También puede usarse el lanzador:

```bash
python run_app.py
```

## Pruebas rápidas

```bash
python -m compileall backend dashboard run_app.py
python -m unittest discover -s tests -v
```
