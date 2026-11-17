import unittest
from ev_calculator import devig_multiplicative, calculate_kelly, extract_1x2_odds, find_positive_ev_picks
from telegram_notifier import TelegramNotifier

class TestBettingBot(unittest.TestCase):

    def test_devig_multiplicative(self):
        # Cuotas típicas de Pinnacle con ~3.3% de margen
        odds = {'home': 2.10, 'draw': 3.40, 'away': 3.80}
        fair = devig_multiplicative(odds)
        
        self.assertIsNotNone(fair)
        # Las probabilidades desmargenadas deben sumar exactamente 1.0
        prob_sum = fair['home'] + fair['draw'] + fair['away']
        self.assertAlmostEqual(prob_sum, 1.0, places=4)
        
        # El overround original debe ser > 1.0
        self.assertGreater(fair['overround'], 1.0)
        self.assertLess(fair['overround'], 1.10)

    def test_calculate_kelly(self):
        # 5% EV en cuota 2.20
        stake = calculate_kelly(ev=0.05, offered_odd=2.20, fraction=0.25)
        self.assertGreater(stake, 0.0)
        self.assertLessEqual(stake, 3.5)

        # Sin valor
        zero_stake = calculate_kelly(ev=0.0, offered_odd=2.0)
        self.assertEqual(zero_stake, 0.0)

    def test_extract_1x2_odds(self):
        bookmaker_data = {
            "key": "pinnacle",
            "title": "Pinnacle",
            "markets": [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Real Madrid", "price": 1.95},
                        {"name": "Barcelona", "price": 3.80},
                        {"name": "Draw", "price": 3.60}
                    ]
                }
            ]
        }
        extracted = extract_1x2_odds(bookmaker_data, "Real Madrid", "Barcelona")
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted['home'], 1.95)
        self.assertEqual(extracted['away'], 3.80)
        self.assertEqual(extracted['draw'], 3.60)

    def test_find_positive_ev_picks(self):
        # Simulamos un partido donde Pinnacle tiene cuotas ajustadas
        # y Bet365 comete un error pagando a 2.30 al Real Madrid cuando la cuota justa es ~2.16
        mock_match = {
            "id": "match_test_001",
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "commence_time": "2026-11-16T20:00:00Z",
            "bookmakers": [
                {
                    "key": "pinnacle",
                    "title": "Pinnacle",
                    "markets": [{
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Real Madrid", "price": 2.10},
                            {"name": "Draw", "price": 3.40},
                            {"name": "Barcelona", "price": 3.80}
                        ]
                    }]
                },
                {
                    "key": "bet365",
                    "title": "Bet365",
                    "markets": [{
                        "key": "h2h",
                        "outcomes": [
                            {"name": "Real Madrid", "price": 2.30}, # ¡Cuota inflada con gran valor!
                            {"name": "Draw", "price": 3.20},
                            {"name": "Barcelona", "price": 3.50}
                        ]
                    }]
                }
            ]
        }

        picks = find_positive_ev_picks(mock_match, sharp_key="pinnacle", target_bookmaker="bet365", min_ev=0.0)
        self.assertGreaterEqual(len(picks), 1)
        top_pick = picks[0]
        self.assertIn("Real Madrid", top_pick['selection'])
        self.assertGreater(top_pick['ev_percent'], 0.0)
        self.assertEqual(top_pick['offered_odd'], 2.30)
        self.assertEqual(top_pick['bookmaker'], "Bet365")

    def test_telegram_format(self):
        notifier = TelegramNotifier("fake_token", "123456789")
        picks = [{
            "league_name": "🇪🇸 LaLiga EA Sports",
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "local_time_formatted": "21:00",
            "selection": "Real Madrid (1)",
            "ev_percent": 6.35,
            "offered_odd": 2.30,
            "fair_odd": 2.16,
            "fair_prob": 46.3,
            "bookmaker": "Bet365",
            "is_target_bookmaker": True,
            "suggested_stake_percent": 1.32
        }]
        text = notifier.format_picks_report(picks, "16/11/2026", 5, 490)
        self.assertIn("PICKS CON VALOR ESPERADO", text)
        self.assertIn("Real Madrid vs Barcelona", text)
        self.assertIn("+6.35%", text)

    def test_configured_leagues(self):
        import config
        expected_keys = [
            "soccer_belgium_first_div",
            "soccer_turkey_super_league",
            "soccer_spl",
            "soccer_switzerland_superleague",
            "soccer_sweden_allsvenskan",
            "soccer_denmark_superliga",
            "soccer_norway_eliteserien"
        ]
        for key in expected_keys:
            self.assertIn(key, config.LEAGUES)
            self.assertTrue(len(config.LEAGUES[key]) > 0)

        # Verificar que el total de ligas configuradas es exactamente 14
        self.assertEqual(len(config.LEAGUES), 14)

        # Verificar que Australia, Brasil, EEUU y las segundas divisiones fueron retiradas
        removed_keys = [
            "soccer_australia_aleague",
            "soccer_brazil_campeonato",
            "soccer_usa_mls",
            "soccer_spain_segunda_division",
            "soccer_efl_champ"
        ]
        for key in removed_keys:
            self.assertNotIn(key, config.LEAGUES)

    def test_format_odd_alert(self):
        notifier = TelegramNotifier("fake_token", "123456789")
        pick = {
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "league_name": "🇪🇸 LaLiga EA Sports",
            "local_time_formatted": "21:00",
            "selection": "Real Madrid (1)",
            "target_odd": 2.20,
            "fair_odd": 2.10
        }
        msg = notifier.format_odd_alert(pick, current_odd=2.25, bookmaker_name="William Hill", date_str="16/11/2026")
        self.assertIn("ALERTA DE CUOTA ALCANZADA", msg)
        self.assertIn("Real Madrid vs Barcelona", msg)
        self.assertIn("2.25", msg)
        self.assertIn("William Hill", msg)

    def test_picks_tracker_functions(self):
        import tempfile
        import os
        from picks_tracker import (
            is_match_live_or_finished,
            save_picks_to_state,
            load_picks_state
        )
        from datetime import datetime, timezone, timedelta

        # 1. Comprobar partidos futuros vs pasados
        future_iso = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self.assertFalse(is_match_live_or_finished(future_iso))
        self.assertTrue(is_match_live_or_finished(past_iso))

        # 2. Guardar y cargar estado
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            sample_picks = [{
                "match_id": "m123",
                "sport_key": "soccer_spain_la_liga",
                "league_name": "🇪🇸 LaLiga EA Sports",
                "home_team": "Sevilla",
                "away_team": "Betis",
                "commence_time": future_iso,
                "selection": "Sevilla (1)",
                "selection_key": "home",
                "offered_odd": 2.30,
                "fair_odd": 2.15,
                "bookmaker": "William Hill"
            }]
            save_picks_to_state(sample_picks, filepath=tmp_path)
            loaded = load_picks_state(filepath=tmp_path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["match_id"], "m123")
            self.assertEqual(loaded[0]["target_odd"], 2.30)
            self.assertEqual(loaded[0]["status"], "pending")
            self.assertFalse(loaded[0]["alerted"])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
