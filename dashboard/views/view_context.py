"""Contexto tipado compartido por las vistas principales del dashboard.

Agrupa configuraciones y callbacks que antes se pasaban como decenas de
argumentos individuales. No contiene lógica de negocio.
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class DashboardViewContext:
    fecha_consulta: Any
    ahora_mexico: Callable
    machine_configs: dict
    current_dir: str
    query_db: Callable
    commit_db: Callable
    run_camera: bool
    render_estatus: Callable
    render_planta: Callable
    render_registro_odp: Callable
    render_operacion_odp: Callable
    render_historial_odp: Callable
    render_analisis: Callable
    render_bitacora: Callable
    render_gestion: Callable
    render_machine_card: Callable
    lista_maquinas: list
    reiniciar_modo_interaccion: Callable
    obtener_nombres_maquinas_operativas: Callable
    obtener_maquinas_impresion: Callable
    obtener_maquinas_router: Callable
    es_maquina_router: Callable
    normalizar_prioridad_odp: Callable
    etiqueta_prioridad_odp: Callable
    prioridad_es_critica: Callable
    formatear_duracion: Callable
    numero_seguro: Callable
    render_produccion: Callable
    todas_maquinas: list
    obtener_odps_en_proceso: Callable
    PRIORIDADES_ODP: list
    TIPOS_CORTE: list
    planta_html: Callable
    planta_escape: Callable
    config_produccion_maquina: Callable
    asignar_odp: Callable
    registrar_odp: Callable
    calcular_area_produccion: Callable
    estimar_produccion: Callable
    maquinas_impresion: list
    maquinas_impresion_compatibles: Callable
    maquinas_router: list
    opciones_pasadas_para_maquina: Callable
    routers_compatibles: Callable
    largo_lamina_rigida_m: float
    m2_por_lamina_rigida: float
    editar_asignacion_produccion: Callable
    eliminar_asignacion: Callable
    actualizar_estado_asignacion: Callable
    obtener_registro_odps_finalizadas: Callable
    dataframe_to_xlsx_bytes: Callable
    generar_pdf_odps_finalizadas: Callable
    process_smart_grid: Callable
    generar_pdf_reporte_maquinas: Callable
    ahora_mexico_texto: Callable
    sql_ahora_mexico: str
