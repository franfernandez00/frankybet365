import sys
import argparse
from datetime import datetime
import pytz
import logging

import config
from odds_client import OddsClient
from ev_calculator import find_positive_ev_picks
from telegram_notifier import TelegramNotifier
from picks_tracker import save_picks_to_state

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def deduplicate_picks(picks):
    """
    Si varias casas ofrecen cuota con valor para la misma selección del mismo partido,
    conservamos únicamente la casa que ofrezca la cuota más alta (mayor EV).
    """
    best_picks = {}
    for p in picks:
        key = (p['match_id'], p['selection'])
        if key not in best_picks:
            best_picks[key] = p
        else:
            if p['ev_percent'] > best_picks[key]['ev_percent']:
                best_picks[key] = p
    return list(best_picks.values())

def run_pipeline(dry_run: bool = False, specific_league: str = None):
    logging.info("Iniciando escáner de apuestas con valor (+EV)...")
    
    tz = pytz.timezone(config.TIMEZONE)
    today_str = datetime.now(tz).strftime("%d/%m/%Y")
    
    odds_client = OddsClient(
        api_key=config.ODDS_API_KEY,
        regions=config.REGIONS,
        timezone=config.TIMEZONE
    )
    
    all_picks = []
    total_matches_reviewed = 0
    leagues_scanned = 0

    target_leagues = (
        {specific_league: config.LEAGUES.get(specific_league, specific_league)}
        if specific_league else config.LEAGUES
    )

    for sport_key, league_name in target_leagues.items():
        logging.info(f"Analizando {league_name} ({sport_key})...")
        matches, meta = odds_client.get_upcoming_matches(sport_key, markets=config.MARKETS)
        
        if not matches:
            logging.info(f"  -> Sin partidos próximos o error al consultar {league_name}")
            continue

        leagues_scanned += 1
        matches_today = odds_client.filter_matches_for_today(matches)
        total_matches_today_league = len(matches_today)
        total_matches_reviewed += total_matches_today_league
        
        logging.info(f"  -> {total_matches_today_league} partidos programados para hoy")

        for match in matches_today:
            match_picks = find_positive_ev_picks(
                match=match,
                sharp_key=config.SHARP_BOOKMAKER,
                target_bookmaker=config.PRIMARY_TARGET_BOOKMAKER,
                min_ev=config.MIN_EV
            )
            
            for p in match_picks:
                p['league_name'] = league_name
                p['sport_key'] = sport_key
                p['local_time_formatted'] = match.get('local_time_formatted', '')
                all_picks.append(p)

    # Eliminar duplicados quedándonos con la mejor cuota disponible
    unique_picks = deduplicate_picks(all_picks)

    # Ordenar estrictamente de mayor a menor Valor Esperado (+EV)
    unique_picks.sort(key=lambda x: x['ev_percent'], reverse=True)

    logging.info(f"Escaneo finalizado. Total partidos revisados hoy: {total_matches_reviewed}")
    logging.info(f"Total picks detectados con EV > {config.MIN_EV}%: {len(unique_picks)}")

    # Formatear reporte para Telegram
    remaining_api = odds_client.last_remaining_requests
    notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
    report_text = notifier.format_picks_report(
        picks=unique_picks,
        date_str=today_str,
        total_matches_reviewed=total_matches_reviewed,
        api_remaining=remaining_api
    )

    print("\n" + "="*50)
    print("REPORTE GENERADO:")
    print("="*50)
    print(report_text)
    print("="*50 + "\n")

    if dry_run:
        logging.info("Modo --dry-run activo. No se envía mensaje a Telegram.")
        return

    # Guardar picks activos en caso de estar disponible el módulo de seguimiento
    try:
        save_picks_to_state(unique_picks)
        logging.info(f"Picks guardados en active_picks.json.")
    except Exception as e:
        logging.debug(f"No se pudo guardar active_picks.json: {e}")

    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        logging.info("Enviando reporte a Telegram...")
        success = notifier.send_message(report_text)
        if success:
            logging.info("¡Mensaje enviado con éxito a Telegram!")
        else:
            logging.error("No se pudo entregar el mensaje a Telegram.")
    else:
        logging.warning("TELEGRAM_CHAT_ID no está configurado en .env. El mensaje no se pudo enviar.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot de Apuestas de Valor (+EV)")
    parser.add_argument("--dry-run", action="store_true", help="Ejecuta el escáner sin enviar mensaje a Telegram")
    parser.add_argument("--league", type=str, default=None, help="Escanear solo una liga específica (ej: soccer_spain_la_liga)")
    args = parser.parse_args()

    run_pipeline(dry_run=args.dry_run, specific_league=args.league)
