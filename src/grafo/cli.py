"""CLI del agente LV2: ejecuta el grafo completo desde la terminal."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from dotenv import load_dotenv

from src.grafo.grafo import invocar_agente


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Agente Auditor Comunitario (grafo LangGraph).")
    parser.add_argument("--texto", required=True, help="Texto de la publicacion o consulta normativa")
    parser.add_argument("--categoria", default="general", help="electricidad | ascensor | gas | agua | general")
    parser.add_argument("--thread-id", default="cli", help="Id de conversacion (memoria de corto plazo)")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Modo demostracion: responde sin API key (LLM simulado)",
    )
    args = parser.parse_args()

    from src.agent.llm import activar_modo_demo, se_uso_demo

    if args.demo:
        activar_modo_demo()

    estado = invocar_agente(args.texto, args.categoria, thread_id=args.thread_id)

    if se_uso_demo():
        print("*** MODO DEMO: sin API key, respuestas del LLM simuladas ***")
        print()
    print(estado.get("respuesta_final") or "(sin respuesta)")
    print("\n--- Bitacora de decisiones del agente ---")
    for i, b in enumerate(estado.get("bitacora", []), 1):
        print(f"{i}. [{b['nodo']}] {b['decision']}")
    print("\n--- Estado final (JSON) ---")
    print(
        json.dumps(
            {k: v for k, v in estado.items() if k not in ("bitacora", "pasos_ejecutados")},
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
