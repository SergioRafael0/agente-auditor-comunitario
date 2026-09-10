"""Middleware de autenticacion bearer token + rate limit por IP."""

from __future__ import annotations

import os
import time
from collections import defaultdict


class AuthMiddleware:
    """Valida Authorization: Bearer <token> contra MCP_AUTH_TOKEN del .env."""

    def __init__(self) -> None:
        self._token = os.getenv("MCP_AUTH_TOKEN", "")
        self._rate_limit_per_min = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
        self._requests_por_ip: dict[str, list[float]] = defaultdict(list)

    def validar(self, headers: dict) -> tuple[bool, str | None]:
        """Devuelve (ok, ip). Si ok=False, rechaza la peticion."""
        auth = headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return False, "Falta header Authorization: Bearer"
        token = auth.removeprefix("Bearer ").strip()
        if token != self._token:
            return False, "Token invalido"

        ip = headers.get("x-forwarded-for", headers.get("x-real-ip", "unknown")).split(",")[0].strip()
        if not self._rate_limit_ok(ip):
            return False, "Rate limit excedido"
        return True, ip

    def _rate_limit_ok(self, ip: str) -> bool:
        ahora = time.time()
        ventana = [t for t in self._requests_por_ip[ip] if ahora - t < 60]
        self._requests_por_ip[ip] = ventana
        if len(ventana) >= self._rate_limit_per_min:
            return False
        ventana.append(ahora)
        return True
