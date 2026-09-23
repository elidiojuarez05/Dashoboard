"""Coordinación de servicios de aplicación.

Centraliza la construcción de servicios que comparten la conexión SQL y la
configuración de máquinas. No contiene lógica de UI ni reglas de negocio.
"""

from dashboard.services.auth_service import AuthService
from dashboard.services.database_service import DatabaseService
from dashboard.services.machine_status_service import MachineStatusService
from dashboard.services.odp_query_service import ODPQueryService
from dashboard.components.priority import normalizar_prioridad_odp


class ApplicationServices:
    """Contenedor de servicios compartidos por las vistas del dashboard."""

    def __init__(self, conn, machine_configs, ahora_mexico, es_maquina_router):
        self.db = DatabaseService(conn=conn, machine_configs=machine_configs)
        self.auth = AuthService(query_db=lambda sql, params=None: self.db.query_db(sql, params))
        self.status = MachineStatusService(
            query_db=lambda sql, params=None: self.db.query_db(sql, params),
            commit_db=lambda sql, params=None: self.db.commit_db(sql, params),
            machine_configs=machine_configs,
            ahora_mexico=ahora_mexico,
        )
        self.odp_query = ODPQueryService(
            query_db=lambda sql, params=None: self.db.query_db(sql, params),
            es_maquina_router=es_maquina_router,
            normalizar_prioridad_odp=normalizar_prioridad_odp,
        )
