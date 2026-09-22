"""Servicio de estado y presentación de máquinas.

Centraliza la lectura de estados, resultados de tests y la tarjeta visual
de cada máquina sin modificar la interfaz existente.
"""

import json
from datetime import datetime, time as dt_time

import pandas as pd
import streamlit as st


class MachineStatusService:
    def __init__(self, query_db, commit_db, machine_configs, ahora_mexico):
        self.query_db = query_db
        self.commit_db = commit_db
        self.machine_configs = machine_configs
        self.ahora_mexico = ahora_mexico

    def estado_con_icono(self, estado):
        if not isinstance(estado, str): estado = str(estado)
        estado = estado.lower().strip()
        if "operativa" in estado: return "🟢 Operativa"
        elif "falla" in estado: return "🔴 Falla"
        elif "sin actividad" in estado: return "⚪ Sin actividad"
        else: return "⚪ Sin registro"

    def obtener_maquinas_operativas(self):
        return self.query_db("""
            SELECT machine_name, estado
            FROM estados_maquinas
            WHERE LOWER(TRIM(estado)) = 'operativa'
            ORDER BY machine_name
        """)

    def obtener_nombres_maquinas_operativas(self):
        """Máquinas configuradas cuyo estado actual en BD es OPERATIVA."""
        df = self.obtener_maquinas_operativas()
        if df is None or df.empty:
            return []
        operativas_bd = {str(x).strip() for x in df["machine_name"].dropna().tolist()}
        return [m for m in self.machine_configs.keys() if str(m).strip() in operativas_bd]

    def obtener_maquinas_impresion(self):
        return [m for m in self.machine_configs.keys() if not self.es_maquina_router(m)]

    def obtener_maquinas_router(self):
        return [m for m in self.machine_configs.keys() if self.es_maquina_router(m)]

    def es_maquina_router(self, nombre_maquina):
        config = self.machine_configs.get(nombre_maquina, {})
        if isinstance(config, dict) and str(config.get("type", "")).lower() == "manual":
            return True
        return "router" in str(nombre_maquina).lower()

    def numero_seguro(self, valor, default=0.0):
        try:
            if valor is None or pd.isna(valor):
                return float(default)
            return float(valor)
        except Exception:
            return float(default)

    def save_test_result(self, machine_name, health_score, missing_nodes, health_map, evidence_path):
        map_json = json.dumps(health_map)
        return self.commit_db("""
            INSERT INTO test_results (machine_name, health_score, missing_nodes, health_map, evidence_path, timestamp)
            VALUES (:m, :s, :n, :map, :e, :t)
        """, {"m": machine_name, "s": health_score, "n": missing_nodes, "map": map_json, "e": evidence_path, "t": self.ahora_mexico()})

    def render_machine_card(self, m_name, fecha_consulta, suffix=""):
    
        config = self.machine_configs.get(m_name, {})
        if isinstance(config, dict):
            es_manual = config.get("type") == "manual"
        else:
            es_manual = "Router" in m_name
    
        inicio_dia = datetime.combine(fecha_consulta, dt_time.min)
        fin_dia = datetime.combine(fecha_consulta, dt_time.max)
    
        res_estado = self.query_db("SELECT estado FROM estados_maquinas WHERE machine_name = :m", {"m": m_name})
        estado_actual = res_estado.iloc[0]['estado'] if not res_estado.empty else "Operativa"
        
        color_router = "#1f77b4" 
        opciones_estilo = {
            "Operativa": {"color_b": "#28a745", "color_f": "rgba(40, 167, 69, 0.05)", "icon": "✅"},
            "Mantenimiento": {"color_b": "#6c757d", "color_f": "rgba(108, 117, 125, 0.1)", "icon": "🛠️"},
            "Falla Total": {"color_b": "#dc3545", "color_f": "rgba(220, 53, 69, 0.1)", "icon": "🚫"},
            "Falla de Slots": {"color_b": "#fd7e14", "color_f": "rgba(253, 126, 20, 0.1)", "icon": "😥"},
            "Falla de Tarjetas": {"color_b": "#0dcaf0", "color_f": "rgba(13, 202, 240, 0.1)", "icon": "😟"}
        }
        
        if estado_actual in opciones_estilo:
            estilo = opciones_estilo[estado_actual].copy()
        else:
            estilo = {"color_b": "#ffc107", "color_f": "rgba(255, 193, 7, 0.1)", "icon": "⚠️"}
    
        with st.container(border=True):
            if es_manual:
                df_manual = self.query_db("""
                    SELECT health_score FROM test_results 
                    WHERE machine_name = :m 
                    AND timestamp BETWEEN :i AND :f
                    ORDER BY timestamp DESC LIMIT 1
                """, {"m": m_name, "i": inicio_dia, "f": fin_dia})
                
                health_val = f"{df_manual.iloc[0]['health_score']:.1f}%" if not df_manual.empty else "N/A"
                icono_router = "🪚" if estado_actual == "Operativa" else estilo['icon']
                
                if estado_actual == "Operativa":
                    color_b_card = color_router 
                    color_f_card = "rgba(31, 119, 180, 0.05)" 
                else:
                    color_b_card = estilo['color_b']
                    color_f_card = estilo['color_f']
                    
                st.html(f"""
                    <div style="height: 355px; border-left: 5px solid {color_b_card}; padding: 25px; 
                                background-color: {color_f_card}; display: flex; flex-direction: column; 
                                justify-content: center; align-items: center; text-align: center; box-sizing: border-box;">
                        <h1 style="font-size: 3.5em; margin: 0;">{icono_router}</h1>
                        <h2 style="margin: 10px 0; font-family: sans-serif; font-weight: 700; color: #1a1a1a;">{m_name}</h2>
                        <div style="margin: 20px 0;">
                            <p style="font-size: 0.85em; color: #666; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">Estatus del Equipo</p>
                            <h1 style="margin: 0; color: {color_b_card}; font-size: 2.8em; font-family: sans-serif; font-weight: bold;">{health_val}</h1>
                        </div>
                        <div style="background-color: {color_b_card}; color: white; padding: 10px 0; 
                                    font-weight: bold; text-transform: uppercase; font-size: 0.9em; letter-spacing: 2px; width: 100%; border-radius: 2px;">
                            {estado_actual}
                        </div>
                    </div>
                """)
            else:
                df_test = self.query_db("""
                    SELECT * FROM test_results 
                    WHERE machine_name = :m 
                    AND timestamp BETWEEN :inicio AND :fin
                    ORDER BY timestamp DESC LIMIT 1
                """, {"m": m_name, "inicio": inicio_dia, "fin": fin_dia})
                
                last_test = df_test.iloc[0] if not df_test.empty else None
    
                if estado_actual == "Operativa" and last_test is not None:
                    health = last_test['health_score']
                    if health < 75: estilo["color_b"] = "#fd7e14"
                    if health < 50: estilo["color_b"] = "#dc3545"
    
                if last_test is not None:
                    ts = last_test['timestamp']
                    fecha_txt = ts.strftime('%d/%m/%Y %I:%M %p') if hasattr(ts, 'strftime') else str(ts)
                else:
                    fecha_txt = "Sin registros"
    
                if estado_actual == "Operativa" and last_test is not None:
                    st.markdown(f"""
                        <div style="height: 60px; border-bottom: 1px solid {estilo['color_b']}; margin-bottom: 10px;">
                            <h3 style="margin: 0; color: {estilo['color_b']};">🖨️ {m_name}</h3>
                            <p style="color: gray; font-size: 0.8em; margin: 0;">Registro Último Test: {fecha_txt}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.metric(
                        label="Status", 
                        value=f"{last_test['health_score']:.1f}%", 
                        delta=f"{int(last_test['missing_nodes'])} Nozzles Fallidos", 
                        delta_color="inverse"
                    )
                    
                    history = self.query_db("""
                        SELECT timestamp, health_score FROM test_results 
                        WHERE machine_name = :m ORDER BY timestamp DESC LIMIT 10
                    """, {"m": m_name})
                    
                    if not history.empty:
                        st.area_chart(
                            history.sort_values('timestamp').set_index('timestamp')['health_score'], 
                            height=150, 
                            color=[estilo["color_b"]]
                        )
                else:
                    etiqueta = estado_actual if last_test is not None or estado_actual != "Operativa" else "SIN TEST PROCESADO"
                    
                    st.markdown(f"""
                        <div style="height: 372px; border: 2px solid {estilo['color_b']}; border-radius: 10px; padding: 20px; 
                                    background-color: {estilo['color_f']}; display: flex; flex-direction: column; 
                                    justify-content: center; align-items: center; text-align: center; box-sizing: border-box;">
                            <h1 style="font-size: 3.5em; margin: 0;">{estilo['icon']}</h1>
                            <h2 style="margin: 10px 0;">{m_name}</h2>
                            <div style="background-color: {estilo['color_b']}; color: white; padding: 6px 20px; 
                                        border-radius: 20px; font-weight: bold; text-transform: uppercase; font-size: 0.9em;">
                                {etiqueta}
                            </div>
                            <p style="color: gray; font-size: 0.9em; margin-top: 25px;">
                                {f"Último análisis: {fecha_txt}" if last_test is not None else "No hay registros de análisis en esta fecha."}
                            </p>
                        </div>
                    """, unsafe_allow_html=True)

    @staticmethod
    def generar_svg_slot_falla(color="#fd7e14"):
        return f"""
        <div style="text-align: center; padding: 10px;">
            <svg width="80" height="80" viewBox="0 0 100 100">
                <path d="M 20 20 L 80 20 L 80 60 L 70 75 L 30 75 L 20 60 Z" fill="none" stroke="{color}" stroke-width="3"/>
                <rect x="35" y="75" width="6" height="12" fill="{color}" opacity="0.3"/>
                <rect x="47" y="75" width="6" height="12" fill="{color}" opacity="0.3"/>
                <rect x="59" y="75" width="6" height="12" fill="#e63946"/>
                <line x1="59" y1="90" x2="65" y2="96" stroke="#e63946" stroke-width="2"/>
                <line x1="65" y1="90" x2="59" y2="96" stroke="#e63946" stroke-width="2"/>
            </svg>
        </div>
        """
