"""Lanzador opcional para ejecutar el dashboard Streamlit."""
import os
import sys
import streamlit.web.cli as stcli


def resolve_path(path):
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, path)
    return os.path.abspath(path)


if __name__ == "__main__":
    dashboard = resolve_path(os.path.join("dashboard", "dashboard.py"))
    sys.argv = [
        "streamlit",
        "run",
        dashboard,
        "--server.port=8501",
        "--server.headless=true",
    ]
    stcli.main()
