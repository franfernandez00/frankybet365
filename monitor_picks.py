import sys
import argparse
from datetime import datetime, timezone
import pytz
import logging
from typing import List, Dict, Any

import config
from odds_client import OddsClient
from ev_calculator import devig_multiplicative, extract_1x2_odds
from telegram_notifier import TelegramNotifier
from picks_tracker import (
    load_picks_state,
    update_picks_state,
    is_match_live_or_finished
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def monitor_active_picks(dry_run: bool = False):
    """
    Escanea las cuotas actuales para los picks pendientes y avisa si se alcanza la cuota recomendada.
    Solo realiza llamadas a la API para las ligas de los partidos pendientes que aún no han comenzado.
    """
    logging.info("Iniciando monitor horario de cuotas...")
    
    tz = pytz.timezone(config.TIMEZONE)
    today_str = datetime.now(tz).strftime("%d/%m/%Y")
    now_utc = datetime.now(timezone.utc)
    
    picks = load_picks_state()
    if not picks:
        logging.info("No hay picks en active_picks.json. Finalizando monitorización sin consumo de API.")
        return

    # 1. Descartar o marcar como expirados los partidos que ya hayan comenzado
    pending_picks: List[Dict[str, Any]] = []
    has_changes = False
    
    for p in picks:
        commence_str = p.get("commence_time")
        if is_match_live_or_finished(commence_str, now_utc):
            if p.get("status") != "expired":
                p["status"] = "expired"
                has_changes = True
                logging.info(f"Partido {p.get('home_team')} vs {p.get('away_team')} ya comenzó o ha finalizado. Marcado como expirado.")
        elif p.get("status") == "pending" and not p.get("alerted", False):
            pending_picks.append(p)

    if not pending_picks:
        logging.info("No hay picks pendientes por monitorizar. Finalizando sin consumo de API.")
        if has_changes:
            update_picks_state(picks)
        return

    # 2. Agrupar ligas que necesitan consulta
    leagues_to_check = set(p.get("sport_key") for p in pending_picks if p.get("sport_key"))
    logging.info(f"Monitorizando {len(pending_picks)} picks pendientes en {len(leagues_to_check)} liga(s): {list(leagues_to_check)}")

    odds_client = OddsClient(
        api_key=config.ODDS_API_KEY,
        regions=config.REGIONS,
        timezone=config.TIMEZONE
    )
    notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)

    alerts_sent = 0

    for sport_key in leagues_to_check:
        logging.info(f"Consultando cuotas actualizadas para {sport_key}...")
        matches, meta = odds_client.get_upcoming_matches(sport_key, markets=config.MARKETS)
        if not matches:
            logging.warning(f"No se pudieron obtener cuotas para {sport_key}")
            continue

        # Crear índice de partidos por id y por nombres de equipo
        matches_by_id = {m.get("id"): m for m in matches}
        
        for pick in pending_picks:
            if pick.get("sport_key") != sport_key:
                continue

            match_data = matches_by_id.get(pick.get("match_id"))
            if not match_data:
                # Búsqueda fallback por nombre de equipo
                match_data = next((m for m in matches if m.get("home_team") == pick.get("home_team") 
                                  and m.get("away_team") == pick.get("away_team")), None)

            if not match_data:
                logging.info(f"Partido {pick.get('home_team')} vs {pick.get('away_team')} no encontrado en el feed actual.")
                continue

            bookmakers = match_data.get("bookmakers", [])
            selection_key = pick.get("selection_key", "home")
            target_odd = float(pick.get("target_odd", 0.0))
            fair_odd = float(pick.get("fair_odd", 0.0))

            # Obtener cuota justa actualizada de Pinnacle si está presente
            sharp_bm = next((b for b in bookmakers if b.get('key') == config.SHARP_BOOKMAKER), None)
            if sharp_bm:
                sharp_odds = extract_1x2_odds(sharp_bm, pick.get("home_team"), pick.get("away_team"))
                if sharp_odds:
                    fair_data = devig_multiplicative(sharp_odds)
                    if fair_data and selection_key in fair_data:
                        fair_odd = round(1.0 / fair_data[selection_key], 2)
                        pick["fair_odd"] = fair_odd

            # Buscar la mejor cuota disponible en las casas recreativas
            best_retail_odd = 0.0
            best_bookie_name = ""

            for b in bookmakers:
                if b.get("key") == config.SHARP_BOOKMAKER:
                    continue
                b_odds = extract_1x2_odds(b, pick.get("home_team"), pick.get("away_team"))
                if b_odds and selection_key in b_odds:
                    odd_val = b_odds[selection_key]
                    if odd_val > best_retail_odd:
                        best_retail_odd = odd_val
                        best_bookie_name = b.get("title", b.get("key"))

            logging.info(f"  -> {pick.get('home_team')} vs {pick.get('away_team')} [{pick.get('selection')}]: "
                         f"Cuota actual {best_retail_odd} en {best_bookie_name} (Objetivo: {target_odd}, Justa: {fair_odd})")

            # Comprobar si ha alcanzado o superado la cuota objetivo o la cuota justa rentable
            threshold = target_odd if target_odd > 0 else fair_odd
            if best_retail_odd >= threshold and best_retail_odd > 1.0:
                logging.info(f"  🔥 ¡Cuota alcanzada! {best_retail_odd} >= {threshold}")
                
                alert_text = notifier.format_odd_alert(
                    pick=pick,
                    current_odd=best_retail_odd,
                    bookmaker_name=best_bookie_name,
                    date_str=today_str
                )

                print("\n" + "="*50)
                print("ALERTA GENERADA:")
                print("="*50)
                print(alert_text)
                print("="*50 + "\n")

                if not dry_run:
                    sent = notifier.send_message(alert_text)
                    if sent:
                        logging.info("¡Alerta entregada en Telegram!")
                        pick["alerted"] = True
                        pick["status"] = "alerted"
                        pick["alerted_at"] = datetime.now(timezone.utc).isoformat()
                        pick["alerted_odd"] = best_retail_odd
                        pick["alerted_bookmaker"] = best_bookie_name
                        has_changes = True
                        alerts_sent += 1
                else:
                    logging.info("Modo --dry-run activo. Alerta no enviada a Telegram.")

    if has_changes:
        update_picks_state(picks)
        logging.info("Estado de active_picks.json actualizado con éxito.")

    logging.info(f"Monitorización completada. Alertas enviadas: {alerts_sent}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor horario de cuotas para picks activos")
    parser.add_argument("--dry-run", action="store_true", help="Ejecuta la comprobación sin enviar mensaje a Telegram")
    args = parser.parse_args()

    monitor_active_picks(dry_run=args.dry_run)
