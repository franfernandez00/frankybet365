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

if __name__ == '__main__':
    unittest.main()
