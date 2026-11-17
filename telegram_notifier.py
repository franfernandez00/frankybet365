import requests
from typing import List, Dict, Any, Optional
import logging

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Envía un mensaje a Telegram. Si excede 4000 caracteres, lo divide automáticamente.
        """
        if not self.bot_token or not self.chat_id:
            logging.error("TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados.")
            return False

        url = f"{self.base_url}/sendMessage"
        
        # Dividir si supera los límites de Telegram
        max_len = 4000
        chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]
        
        success = True
        for chunk in chunks:
            payload = {
                "chat_id": self.chat_id,
                "text": chunk,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            try:
                resp = requests.post(url, json=payload, timeout=15)
                res_data = resp.json()
                if not res_data.get("ok"):
                    logging.error(f"Error enviando mensaje a Telegram: {res_data}")
                    success = False
            except Exception as e:
                logging.error(f"Excepción al conectar con Telegram: {e}")
                success = False

        return success

    def format_picks_report(self, 
                            picks: List[Dict[str, Any]], 
                            date_str: str, 
                            total_matches_reviewed: int,
                            api_remaining: Optional[int] = None) -> str:
        """
        Genera el mensaje estilizado en HTML con todos los picks ordenados por EV,
        o una notificación clara cuando no se detecta valor o no hay partidos hoy.
        """
        if not picks:
            if total_matches_reviewed > 0:
                msg = (
                    f"⚽ <b>INFORME MATINAL DE VALOR ESPERADO (+EV)</b>\n"
                    f"📅 <i>{date_str}</i>\n\n"
                    f"🔍 <b>Partidos analizados hoy:</b> {total_matches_reviewed}\n"
                    f"ℹ️ <b>Resultado:</b> <b>Sin apuestas con valor positivo hoy.</b>\n\n"
                    f"📊 Se han cruzado las cuotas de Bet365 y el mercado contra el desmargen de Pinnacle, "
                    f"y ningún partido ofrece margen a nuestro favor.\n\n"
                    f"💡 <i>La regla de oro para ganar a largo plazo es la disciplina: no forzar apuestas cuando el mercado está bien ajustado. ¡Paciencia y a esperar la siguiente jornada!</i>"
                )
            else:
                msg = (
                    f"⚽ <b>INFORME MATINAL DE VALOR ESPERADO (+EV)</b>\n"
                    f"📅 <i>{date_str}</i>\n\n"
                    f"🔍 <b>Partidos hoy:</b> 0 partidos en las ligas monitorizadas.\n"
                    f"ℹ️ <b>Resultado:</b> Hoy no hay encuentros programados en las competiciones seleccionadas (jornada de descanso o parón).\n\n"
                    f"💡 <i>El bot volverá a escanear automáticamente mañana a las 09:00 AM.</i>"
                )
            if api_remaining is not None:
                msg += f"\n\n📊 <i>Consultas API restantes este mes: {api_remaining}/500</i>"
            return msg

        # Encabezado del reporte
        lines = [
            f"🎯 <b>PICKS CON VALOR ESPERADO (+EV)</b>",
            f"📅 <i>{date_str}</i>",
            f"📊 <b>Partidos revisados:</b> {total_matches_reviewed} | <b>Picks con valor:</b> {len(picks)}",
            f"━━━━━━━━━━━━━━━━━━━",
            ""
        ]

        # Listado de picks ordenados de mayor a menor EV
        for idx, p in enumerate(picks, 1):
            league = p.get('league_name', 'Fútbol')
            home = p.get('home_team')
            away = p.get('away_team')
            time_str = p.get('local_time_formatted', '')
            selection = p.get('selection')
            ev = p.get('ev_percent')
            offered = p.get('offered_odd')
            fair = p.get('fair_odd')
            fair_prob = p.get('fair_prob')
            bookie = p.get('bookmaker')
            is_bet365 = p.get('is_target_bookmaker', False)
            stake = p.get('suggested_stake_percent', 1.0)

            badge = "🔥 TOP PICK" if idx == 1 else f"#{idx}"

            block = (
                f"<b>{badge} | {home} vs {away}</b>\n"
                f"🏆 <i>{league}</i> {f'• ⏰ {time_str}h' if time_str else ''}\n"
                f"📌 <b>Apuesta:</b> <code>{selection}</code>\n"
                f"📈 <b>Valor Esperado (+EV):</b> <b>+{ev}%</b>\n"
                f"💰 <b>Cuota encontrada:</b> <b>{offered}</b> en <i>{bookie}</i>\n"
                f"⚖️ <b>Cuota Justa (Pinnacle sin margen):</b> <b>{fair}</b> (Probabilidad: {fair_prob}%)\n"
                f"💵 <b>Stake sugerido:</b> {stake}% bankroll"
            )

            if not is_bet365:
                block += f"\n💡 <i>En Bet365: Apostar si su cuota está por encima de {fair}</i>"

            lines.append(block)
            lines.append("───────────────────")

        if api_remaining is not None:
            lines.append(f"📡 <i>Consultas The Odds API restantes: {api_remaining}/500</i>")

        return "\n".join(lines)

    def format_odd_alert(self, 
                         pick: Dict[str, Any], 
                         current_odd: float, 
                         bookmaker_name: str,
                         date_str: str) -> str:
        """
        Genera el mensaje de alerta urgente cuando una cuota alcanza o supera el objetivo recomendado.
        """
        home = pick.get('home_team', '')
        away = pick.get('away_team', '')
        league = pick.get('league_name', 'Fútbol')
        time_str = pick.get('local_time_formatted', '')
        selection = pick.get('selection', '')
        target_odd = pick.get('target_odd', 0.0)
        fair_odd = pick.get('fair_odd', 0.0)
        
        current_ev = 0.0
        if fair_odd > 0:
            current_ev = round(((1.0 / fair_odd) * current_odd - 1.0) * 100.0, 2)

        return (
            f"🚨 <b>¡ALERTA DE CUOTA ALCANZADA!</b>\n"
            f"📅 <i>{date_str}</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚽ <b>{home} vs {away}</b>\n"
            f"🏆 <i>{league}</i> {f'• ⏰ <b>{time_str}h</b>' if time_str else ''}\n"
            f"📌 <b>Selección:</b> <code>{selection}</code>\n\n"
            f"🎯 <b>Cuota objetivo recomendada:</b> <b>{target_odd}</b>\n"
            f"🔥 <b>Cuota detectada en mercado:</b> <b>{current_odd}</b> en <i>{bookmaker_name}</i>\n"
            f"📈 <b>Valor actual (+EV):</b> <b>+{current_ev}%</b>\n"
            f"⚖️ <b>Cuota Justa (Pinnacle sin margen):</b> {fair_odd}\n\n"
            f"💡 <i>¡Momento idóneo para entrar en Bet365 y realizar la apuesta antes del inicio!</i>"
        )
