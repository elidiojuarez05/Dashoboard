"""Servicios de autenticación y validación de usuarios.

Mantiene la lógica de credenciales fuera de dashboard.py sin cambiar
el contrato que usa la interfaz.
"""

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class AuthenticatedUser:
    id: Any
    username: Any
    role: Any


class AuthService:
    """Valida usuarios contra la tabla ``usuarios``.

    ``query_db`` se inyecta para reutilizar la capa de base de datos
    existente y mantener este servicio independiente de Streamlit.
    """

    def __init__(self, query_db: Callable[[str, Optional[dict]], Any]):
        self.query_db = query_db

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(str(password).encode()).hexdigest()

    def check_password(self, username: str, password: str) -> Optional[AuthenticatedUser]:
        """Devuelve el usuario autenticado o ``None`` si las credenciales fallan."""
        res = self.query_db(
            "SELECT * FROM usuarios WHERE username = :u",
            {"u": username},
        )

        if res is None or res.empty:
            return None

        res.columns = [c.lower() for c in res.columns]
        db_pass = str(res.iloc[0]["password"]).strip()
        input_hash = self._hash_password(password)

        if db_pass != input_hash:
            return None

        return AuthenticatedUser(
            id=res.iloc[0]["id"],
            username=res.iloc[0]["username"],
            role=res.iloc[0]["role"],
        )
