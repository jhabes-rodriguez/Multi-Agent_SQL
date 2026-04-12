"""
start_orchestrator.py
=====================
Punto de entrada del orquestador Multi-Agent.

Uso:
  python start_orchestrator.py              ← Menú interactivo
  python start_orchestrator.py --pipeline   ← Pipeline completo secuencial
  python start_orchestrator.py --agent2     ← Solo Agente 2 (+ API)
  python start_orchestrator.py --agent3     ← Solo Agente 3 (+ API)
  python start_orchestrator.py --api        ← Solo API Central
  python start_orchestrator.py --keys       ← Ver API keys configuradas
"""

import sys
from orchestrator.orchestrator import run

if __name__ == "__main__":
    run(sys.argv[1:])
