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
        Genera el mensaje estilizado en HTML con todos los picks ordenados por EV.
        """
        if not picks:
            msg = (
                f"⚽ <b>INFORME MATINAL DE VALOR ESPERADO (+EV)</b>\n"
                f"📅 <i>{date_str}</i>\n\n"
                f"🔍 <b>Partidos analizados hoy:</b> {total_matches_reviewed}\n"
                f"ℹ️ <b>Resultado:</b> No se han detectado picks con valor matemático real (+EV) en las ligas analizadas.\n\n"
                f"💡 <i>Las cuotas del mercado están ajustadas al milímetro con respecto a Pinnacle. No forzar apuestas cuando no hay ventaja matemática es la clave de la rentabilidad a largo plazo.</i>"
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
