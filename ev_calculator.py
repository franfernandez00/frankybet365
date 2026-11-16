from typing import List, Dict, Any, Optional

def devig_multiplicative(odds: Dict[str, float]) -> Optional[Dict[str, float]]:
    """
    Calcula las probabilidades justas (fair probabilities) eliminando el margen
    (vig/overround) de la casa sharp mediante el modelo multiplicativo proporcional.
    
    odds: dict con {'home': odd, 'draw': odd, 'away': odd}
    Retorna: dict con {'home': prob, 'draw': prob, 'away': prob, 'overround': S}
    """
    try:
        home_odd = odds.get('home', 0.0)
        draw_odd = odds.get('draw', 0.0)
        away_odd = odds.get('away', 0.0)
        
        if home_odd <= 1.0 or draw_odd <= 1.0 or away_odd <= 1.0:
            return None
        
        # Probabilidades implícitas con margen
        imp_home = 1.0 / home_odd
        imp_draw = 1.0 / draw_odd
        imp_away = 1.0 / away_odd
        
        # Overround total
        overround = imp_home + imp_draw + imp_away
        if overround <= 0:
            return None
            
        # Probabilidades desmargenadas (suman exactamente 1.0)
        fair_home = imp_home / overround
        fair_draw = imp_draw / overround
        fair_away = imp_away / overround
        
        return {
            'home': fair_home,
            'draw': fair_draw,
            'away': fair_away,
            'overround': overround
        }
    except Exception:
        return None


def calculate_kelly(ev: float, offered_odd: float, fraction: float = 0.25) -> float:
    """
    Calcula el stake según el criterio de Kelly fraccional (por defecto Quarter Kelly = 25%).
    Retorna porcentaje de bankroll recomendado (ej: 1.5 para 1.5%).
    """
    if offered_odd <= 1.0 or ev <= 0:
        return 0.0
    
    b = offered_odd - 1.0
    full_kelly = ev / b
    frac_kelly = full_kelly * fraction * 100.0
    
    # Acotamos el stake para una gestión de riesgo prudente (0.5% - 3.5%)
    return round(max(0.5, min(frac_kelly, 3.5)), 2)


def extract_1x2_odds(bookmaker_data: Dict[str, Any], home_team: str, away_team: str) -> Optional[Dict[str, float]]:
    """
    Extrae las cuotas 1, X, 2 de un bookmaker para el mercado 'h2h'.
    """
    markets = bookmaker_data.get('markets', [])
    for market in markets:
        if market.get('key') == 'h2h':
            outcomes = market.get('outcomes', [])
            home_odd, draw_odd, away_odd = None, None, None
            
            for out in outcomes:
                name = out.get('name')
                price = float(out.get('price', 0.0))
                
                if name == home_team:
                    home_odd = price
                elif name == away_team:
                    away_odd = price
                elif name.lower() in ['draw', 'empate']:
                    draw_odd = price
            
            if home_odd and draw_odd and away_odd:
                return {
                    'home': home_odd,
                    'draw': draw_odd,
                    'away': away_odd
                }
    return None


def find_positive_ev_picks(match: Dict[str, Any],
                           sharp_key: str = "pinnacle",
                           target_bookmaker: str = "bet365",
                           min_ev: float = 0.0) -> List[Dict[str, Any]]:
    """
    Analiza un partido, calcula las probabilidades reales usando Pinnacle
    y busca picks con EV positivo en el target_bookmaker (o el mejor bookie recreativo disponible).
    """
    picks = []
    bookmakers = match.get('bookmakers', [])
    home_team = match.get('home_team', '')
    away_team = match.get('away_team', '')
    commence_time = match.get('commence_time', '')
    match_id = match.get('id', '')
    
    # 1. Buscar cuotas de Pinnacle (Sharp)
    sharp_bm = next((b for b in bookmakers if b.get('key') == sharp_key), None)
    if not sharp_bm:
        return picks  # Sin Pinnacle no podemos calcular probabilidad fair fiable
    
    sharp_odds = extract_1x2_odds(sharp_bm, home_team, away_team)
    if not sharp_odds:
        return picks
        
    fair_probs = devig_multiplicative(sharp_odds)
    if not fair_probs:
        return picks

    # 2. Buscar casas de apuestas a evaluar:
    # Prioridad: Target bookmaker (ej. Bet365).
    # Si Bet365 está presente, evaluamos Bet365. Si no está en el feed de The Odds API,
    # evaluamos las casas recreativas disponibles en la región.
    target_bms = [b for b in bookmakers if b.get('key') == target_bookmaker]
    
    # Si no se encuentra Bet365 directamente, buscamos las casas recreativas disponibles
    is_fallback = False
    if not target_bms:
        is_fallback = True
        target_bms = [b for b in bookmakers if b.get('key') != sharp_key]
        
    if not target_bms:
        return picks

    # Evaluamos cada casa objetivo
    for b in target_bms:
        bookie_name = b.get('title', b.get('key'))
        bookie_key = b.get('key')
        retail_odds = extract_1x2_odds(b, home_team, away_team)
        if not retail_odds:
            continue
            
        outcomes_map = [
            ('home', f"{home_team} (1)", home_team),
            ('draw', 'Empate (X)', 'Empate'),
            ('away', f"{away_team} (2)", away_team)
        ]
        
        for key, pick_label, team_name in outcomes_map:
            p_fair = fair_probs[key]
            fair_odd = 1.0 / p_fair
            offered_odd = retail_odds[key]
            
            # Cálculo de EV: (P_fair * Cuota) - 1
            ev = (p_fair * offered_odd) - 1.0
            ev_percent = ev * 100.0
            
            if ev > min_ev:
                stake = calculate_kelly(ev, offered_odd)
                picks.append({
                    'match_id': match_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'commence_time': commence_time,
                    'selection': pick_label,
                    'selection_name': team_name,
                    'bookmaker': bookie_name,
                    'bookmaker_key': bookie_key,
                    'is_target_bookmaker': (bookie_key == target_bookmaker),
                    'is_fallback': is_fallback,
                    'offered_odd': offered_odd,
                    'fair_odd': round(fair_odd, 2),
                    'fair_prob': round(p_fair * 100.0, 1),
                    'ev_percent': round(ev_percent, 2),
                    'suggested_stake_percent': stake,
                    'pinnacle_odd': sharp_odds[key],
                    'overround_pinnacle': round((fair_probs['overround'] - 1.0) * 100.0, 2)
                })

    return picks
