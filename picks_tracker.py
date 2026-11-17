import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

STATE_FILE = os.path.join(os.path.dirname(__file__), "active_picks.json")

def is_match_live_or_finished(commence_time_str: str, now_utc: Optional[datetime] = None) -> bool:
    """
    Comprueba si un partido ya ha comenzado en función de su fecha de inicio UTC (commence_time).
    """
    if not commence_time_str:
        return False
    try:
        utc_dt = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))
        if now_utc is None:
            now_utc = datetime.now(timezone.utc)
        elif now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)
        return now_utc >= utc_dt
    except Exception as e:
        logging.warning(f"Error comprobando commence_time '{commence_time_str}': {e}")
        return False

def load_picks_state(filepath: str = STATE_FILE) -> List[Dict[str, Any]]:
    """
    Carga la lista de picks activos desde el archivo JSON de estado.
    """
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        logging.error(f"Error leyendo archivo de estado {filepath}: {e}")
        return []

def save_picks_to_state(picks: List[Dict[str, Any]], filepath: str = STATE_FILE) -> bool:
    """
    Guarda los picks detectados en el escaneo diario para su posterior seguimiento.
    """
    try:
        state_list = []
        now_iso = datetime.now(timezone.utc).isoformat()
        
        for p in picks:
            # Determinamos la cuota objetivo: la cuota que activó el valor o la cuota justa mínima
            target_odd = p.get('offered_odd') or p.get('fair_odd')
            
            entry = {
                "match_id": p.get("match_id"),
                "sport_key": p.get("sport_key"),
                "league_name": p.get("league_name"),
                "home_team": p.get("home_team"),
                "away_team": p.get("away_team"),
                "commence_time": p.get("commence_time"),
                "local_time_formatted": p.get("local_time_formatted", ""),
                "selection": p.get("selection"),
                "selection_name": p.get("selection_name"),
                "selection_key": p.get("selection_key", "home"),
                "target_odd": target_odd,
                "fair_odd": p.get("fair_odd"),
                "fair_prob": p.get("fair_prob"),
                "ev_percent": p.get("ev_percent"),
                "initial_bookmaker": p.get("bookmaker"),
                "status": "pending",
                "alerted": False,
                "created_at": now_iso
            }
            state_list.append(entry)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state_list, f, indent=2, ensure_ascii=False)
        logging.info(f"Guardados {len(state_list)} picks en {filepath}")
        return True
    except Exception as e:
        logging.error(f"Error guardando picks en {filepath}: {e}")
        return False

def update_picks_state(picks: List[Dict[str, Any]], filepath: str = STATE_FILE) -> bool:
    """
    Sobrescribe el archivo de estado con las actualizaciones de seguimiento.
    """
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(picks, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Error actualizando picks en {filepath}: {e}")
        return False
