import os

def load_env_file():
    """Carga variables desde .env si existe, sin requerir python-dotenv obligatoriamente."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'").strip('"')
                        if k and k not in os.environ:
                            os.environ[k] = v

load_env_file()

# Credenciales de API
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Zona horaria para filtrar partidos del día
TIMEZONE = os.getenv("TIMEZONE", "Europe/Madrid")

# Umbral mínimo de Valor Esperado (EV) en decimal (0.0 = 0% de EV positivo)
MIN_EV = float(os.getenv("MIN_EV", "0.0"))

# Casa sharp de referencia para calcular cuotas justas sin margen
SHARP_BOOKMAKER = "pinnacle"

# Casa de apuestas principal del usuario
PRIMARY_TARGET_BOOKMAKER = os.getenv("TARGET_BOOKMAKER", "bet365").lower()

# Regiones a consultar en The Odds API
REGIONS = "eu,uk"

# Mercados
MARKETS = "h2h"  # 1X2

# Diccionario de ligas a analizar con sus nombres legibles
LEAGUES = {
    "soccer_spain_la_liga": "🇪🇸 LaLiga EA Sports",
    "soccer_spain_segunda_division": "🇪🇸 LaLiga Hypermotion",
    "soccer_epl": "🇬🇧 Premier League",
    "soccer_italy_serie_a": "🇮🇹 Serie A",
    "soccer_germany_bundesliga": "🇩🇪 Bundesliga",
    "soccer_france_ligue_one": "🇫🇷 Ligue 1",
    "soccer_efl_champ": "🇬🇧 Championship",
    "soccer_netherlands_eredivisie": "🇳🇱 Eredivisie",
    "soccer_portugal_primeira_liga": "🇵🇹 Liga Portugal",
}
