import os
import sys
import argparse
from datetime import datetime, timezone
import logging

from main import run_pipeline
from monitor_picks import monitor_active_picks

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def run_job(mode: str = "auto", dry_run: bool = False):
    """
    Orquesta la ejecución:
    - A las 11:00 UTC (12:00 hora peninsular española): Escaneo completo de las 14 ligas (main.py).
    - De 12:00 a 20:00 UTC (13:00 a 21:00 hora peninsular española): Monitor horario de cuotas (monitor_picks.py).
    """
    mode = mode.lower()
    now_utc = datetime.now(timezone.utc)
    current_utc_hour = now_utc.hour

    logging.info(f"Iniciando trabajo programado. Modo: {mode} | Hora UTC: {current_utc_hour:02d}:00")

    if mode == "scan":
        logging.info("Modo 'scan' explícito: ejecutando escaneo completo matinal...")
        run_pipeline(dry_run=dry_run)
    elif mode == "monitor":
        logging.info("Modo 'monitor' explícito: ejecutando monitor horario de picks...")
        monitor_active_picks(dry_run=dry_run)
    else:
        # Modo 'auto'
        # 8 UTC corresponde a las 09:00 AM peninsular española (horario estándar de invierno)
        if current_utc_hour == 8:
            logging.info("Hora 08:00 UTC detectada (09:00 AM España). Ejecutando escaneo principal de ligas...")
            run_pipeline(dry_run=dry_run)
        else:
            logging.info(f"Hora {current_utc_hour:02d}:00 UTC detectada. Ejecutando monitor de cuotas...")
            monitor_active_picks(dry_run=dry_run)

if __name__ == "__main__":
    env_mode = os.getenv("EXECUTION_MODE", "auto")
    
    parser = argparse.ArgumentParser(description="Orquestador de ejecución del Bot de Apuestas")
    parser.add_argument("--mode", type=str, default=env_mode, choices=["auto", "scan", "monitor"],
                        help="Modo de ejecución: auto, scan o monitor")
    parser.add_argument("--dry-run", action="store_true", help="No enviar mensajes a Telegram")
    args = parser.parse_args()

    run_job(mode=args.mode, dry_run=args.dry_run)
