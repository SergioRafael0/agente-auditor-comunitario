"""Middleware de autenticacion bearer token + rate limit por IP.

Controles de seguridad:
- Comparacion del token en tiempo constante (`hmac.compare_digest`) para
  evitar ataques de cronometraje (timing attack).
- Fail-closed: si `MCP_AUTH_TOKEN` no esta configurado, toda peticion se
  rechaza (no se aceptan tokens vacios).
- Auditoria de accesos: cada intento (exitoso o fallido) se registra en
  `data/accesos.jsonl` con IP, motivo y timestamp. Nunca se registra el token.
- Rate limit por IP: ventana deslizante de 60 segundos.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import time
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Valida Authorization: Bearer <token> contra MCP_AUTH_TOKEN del .env."""

    def __init__(self) -> None:
        self._token = os.getenv("MCP_AUTH_TOKEN", "")
        self._rate_limit_per_min = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
        self._requests_por_ip: dict[str, list[float]] = defaultdict(list)

    def validar(self, headers: dict) -> tuple[bool, str | None]:
        """Devuelve (ok, ip). Si ok=False, rechaza la peticion."""
        ip = self._ip(headers)
        auth = headers.get("authorization", "")
        if not self._token:
            self._registrar_acceso(ip, False, "MCP_AUTH_TOKEN no configurado")
            return False, "Servidor no configurado"
        if not auth.startswith("Bearer "):
            self._registrar_acceso(ip, False, "Falta header Authorization: Bearer")
            return False, "Falta header Authorization: Bearer"
        token = auth.removeprefix("Bearer ").strip()
        if not hmac.compare_digest(token, self._token):
            self._registrar_acceso(ip, False, "Token invalido")
            return False, "Token invalido"

        if not self._rate_limit_ok(ip):
            self._registrar_acceso(ip, False, "Rate limit excedido")
            return False, "Rate limit excedido"
        self._registrar_acceso(ip, True, "acceso concedido")
        return True, ip

    def _ip(self, headers: dict) -> str:
        return headers.get("x-forwarded-for", headers.get("x-real-ip", "unknown")).split(",")[0].strip()

    def _rate_limit_ok(self, ip: str) -> bool:
        ahora = time.time()
        ventana = [t for t in self._requests_por_ip[ip] if ahora - t < 60]
        self._requests_por_ip[ip] = ventana
        if len(ventana) >= self._rate_limit_per_min:
            return False
        ventana.append(ahora)
        return True

    def _registrar_acceso(self, ip: str, ok: bool, motivo: str) -> None:
        """Auditoria de accesos: quien intento entrar y con que resultado."""
        ruta = os.getenv("LOG_FILE_ACCESOS", "data/accesos.jsonl")
        if not ruta:
            return
        try:
            p = Path(ruta)
            p.parent.mkdir(parents=True, exist_ok=True)
            registro = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "ip": ip,
                "acceso": "concedido" if ok else "rechazado",
                "motivo": motivo,
            }
            with p.open("a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning("No se pudo registrar el acceso en %s: %s", ruta, e)
