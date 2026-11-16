import requests
from datetime import datetime
import pytz
from typing import List, Dict, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OddsClient:
    BASE_URL = "https://api.the-odds-api.com/v4/sports"

    def __init__(self, api_key: str, regions: str = "eu,uk", timezone: str = "Europe/Madrid"):
        self.api_key = api_key
        self.regions = regions
        self.timezone_name = timezone
        self.tz = pytz.timezone(timezone)
        self.last_remaining_requests = None

    def get_upcoming_matches(self, sport_key: str, markets: str = "h2h") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Obtiene los partidos y cuotas para una liga específica en The Odds API.
        Retorna la lista de partidos y metadatos de la cuota restante de la API.
        """
        if not self.api_key:
            raise ValueError("ODDS_API_KEY no está configurada.")

        url = f"{self.BASE_URL}/{sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": self.regions,
            "markets": markets,
            "oddsFormat": "decimal",
            "dateFormat": "iso"
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            
            # Guardar consumo y cuota restante
            remaining = response.headers.get("x-requests-remaining")
            used = response.headers.get("x-requests-used")
            if remaining is not None:
                self.last_remaining_requests = int(remaining)
                meta = {"remaining": int(remaining), "used": int(used) if used else 0}
            else:
                meta = {"remaining": None, "used": None}

            if response.status_code != 200:
                logging.error(f"Error {response.status_code} al consultar {sport_key}: {response.text}")
                return [], meta

            data = response.json()
            return data, meta

        except Exception as e:
            logging.error(f"Excepción de conexión al consultar {sport_key}: {e}")
            return [], {"remaining": None, "used": None}

    def filter_matches_for_today(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra los partidos para incluir únicamente los que se juegan HOY
        en la zona horaria indicada (Europe/Madrid).
        """
        now_local = datetime.now(self.tz)
        today_date = now_local.date()
        
        matches_today = []
        for match in matches:
            commence_str = match.get("commence_time")
            if not commence_str:
                continue
                
            try:
                # Commence_time viene en formato ISO UTC (ej: '2026-11-16T19:30:00Z')
                utc_time = datetime.fromisoformat(commence_str.replace("Z", "+00:00"))
                local_time = utc_time.astimezone(self.tz)
                
                # Comprobar si se juega en la fecha de hoy
                if local_time.date() == today_date:
                    match_copy = dict(match)
                    match_copy["local_time_formatted"] = local_time.strftime("%H:%M")
                    match_copy["local_datetime"] = local_time
                    matches_today.append(match_copy)
            except Exception as e:
                logging.warning(f"Error parseando fecha {commence_str}: {e}")
                
        return matches_today
