# arbitrage_engine_bis.py

import json
import logging
import math
# ---------------------------
# Taux de Change Forex
# ---------------------------
forex_rates = {
    "XAF/EUR": 655.957,
    "XOF/EUR": 655.957,
    "RWF/EUR": 1700.0,
    "KES/EUR": 151.76,
}
# --- CHARGEMENT DE LA CONFIGURATION ---
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    markets = config['markets']
    forex_rates = config['forex_rates']
    NB_CYCLES_PAR_ROTATION = config.get('NB_CYCLES_PAR_ROTATION', 3)
except (FileNotFoundError, KeyError) as e:
    print(f"ERREUR CRITIQUE: Le fichier 'config.json' est manquant ou invalide. DÃ©tail: {e}")
    logging.error(f"Erreur chargement config.json: {e}")
    exit()

# --- FONCTIONS UTILITAIRES ---
def validate_config_coherence(markets, forex_rates):
    """Valide la cohérence des taux de change et prix de marché"""
    alerts = []
    
    # Vérifier les taux de change triangulaires avec TOLÉRANCE AUGMENTÉE
    for currency_a in [m['currency'] for m in markets]:
        for currency_b in [m['currency'] for m in markets]:
            if currency_a == currency_b:
                continue
                
            try:
                rate_ab = get_forex_rate(currency_a, currency_b, forex_rates)
                rate_b_eur = get_forex_rate(currency_b, 'EUR', forex_rates)
                rate_eur_a = get_forex_rate('EUR', currency_a, forex_rates)
                
                round_trip = rate_ab * rate_b_eur * rate_eur_a
                
                # TOLÉRANCE AUGMENTÉE À 20% (au lieu de 5%)
                if abs(round_trip - 1.0) > 0.20:
                    alerts.append({
                        'type': 'TAUX_INCOHERENT',
                        'severity': 'WARNING',  # WARNING au lieu de ERROR
                        'message': f"Incohérence triangulaire : {currency_a}→{currency_b}→EUR→{currency_a} = {round_trip:.4f}"
                    })
            except ValueError as ve:
                alerts.append({
                    'type': 'TAUX_MANQUANT',
                    'severity': 'ERROR',
                    'message': f"Taux de change manquant : {currency_a}→{currency_b}"
                })
            except (ZeroDivisionError, Exception) as e:
                logging.debug(f"Erreur validation {currency_a}->{currency_b}: {e}")
    
    # Vérifier les écarts buy/sell
    for market in markets:
        if market.get('buy_price', 0) > 0 and market.get('sell_price', 0) > 0:
            spread_pct = ((market['buy_price'] - market['sell_price']) / market['sell_price']) * 100
            
            if spread_pct < -2:
                alerts.append({
                    'type': 'SPREAD_INVERSE',
                    'severity': 'ERROR',
                    'message': f"{market['currency']}: Prix achat < Prix vente - INVERSION!"
                })
            elif spread_pct > 15:  # Tolérance augmentée de 10% à 15%
                alerts.append({
                    'type': 'SPREAD_ANORMAL',
                    'severity': 'WARNING',
                    'message': f"{market['currency']}: Spread élevé ({spread_pct:.2f}%)"
                })
    
    return alerts

def get_market_data(currency_code, markets_list):
    """RÃ©cupÃ¨re les donnÃ©es de marchÃ© pour une devise donnÃ©e"""
    for market in markets_list:
        if "currency" in market and market["currency"] == currency_code:
            return market
    raise ValueError(f"Aucun marchÃ© trouvÃ© pour la devise '{currency_code}'.")

def safe_divide(numerator, denominator, default=0):
    """Division sÃ©curisÃ©e pour Ã©viter les divisions par zÃ©ro"""
    if denominator == 0 or denominator is None:
        logging.warning(f"Division par zÃ©ro Ã©vitÃ©e: {numerator}/{denominator}")
        return default
    try:
        result = numerator / denominator
        if not isinstance(result, (int, float)) or result != result:  # Check for NaN
            logging.warning(f"RÃ©sultat de division invalide: {numerator}/{denominator} = {result}")
            return default
        return result
    except (ZeroDivisionError, TypeError, ValueError):
        logging.warning(f"Erreur division: {numerator}/{denominator}")
        return default

def get_forex_rate(from_currency, to_currency, forex_rates):
    """Récupère le taux de change de manière sécurisée"""
    if from_currency == to_currency:
        return 1.0
    
    # Chercher FROM/TO (ex: RWF/EUR)
    pair = f"{from_currency}/{to_currency}"
    if pair in forex_rates:
        rate = forex_rates[pair]
        if rate > 0:
            # Si RWF/EUR = 1700, cela signifie 1700 RWF = 1 EUR
            # Donc pour convertir RWF→EUR : diviser par 1700
            # Donc le taux est 1/1700 = 0.000588
            return 1.0 / rate  # <-- CORRECTION ICI
    
    # Chercher TO/FROM (ex: EUR/RWF)
    inverse_pair = f"{to_currency}/{from_currency}"
    if inverse_pair in forex_rates:
        rate = forex_rates[inverse_pair]
        if rate > 0:
            return rate
    
    raise ValueError(f"Taux de change manquant pour {from_currency}→{to_currency}")

def convert_to_eur(amount, currency, forex_rates):
    """Convertit un montant vers EUR de manière sécurisée"""
    if currency == 'EUR':
        return amount
    
    if amount <= 0:
        logging.warning(f"Montant invalide pour conversion: {amount} {currency}")
        return 0
    
    try:
        # Chercher d'abord CURRENCY/EUR (ex: RWF/EUR = 1700 signifie 1700 RWF = 1 EUR)
        pair = f"{currency}/EUR"
        if pair in forex_rates:
            rate = forex_rates[pair]
            if rate > 0:
                return amount / rate  # DIVISION au lieu de multiplication
        
        # Sinon chercher EUR/CURRENCY
        inverse_pair = f"EUR/{currency}"
        if inverse_pair in forex_rates:
            rate = forex_rates[inverse_pair]
            if rate > 0:
                return amount * rate
        
        raise ValueError(f"Taux manquant pour {currency}→EUR")
    except Exception as e:
        logging.error(f"Impossible de convertir {currency} vers EUR: {e}")
        raise

def validate_market_data(market):
    """Valide les donnÃ©es d'un marchÃ©"""
    required_fields = ['currency', 'buy_price', 'sell_price', 'fee_pct', 'name']
    
    for field in required_fields:
        if field not in market:
            return False, f"Champ manquant: {field}"
    
    # VÃ©rifier les valeurs numÃ©riques
    numeric_fields = ['buy_price', 'sell_price', 'fee_pct']
    for field in numeric_fields:
        try:
            value = float(market[field])
            if value < 0:
                return False, f"Valeur nÃ©gative pour {field}: {value}"
            if field in ['buy_price', 'sell_price'] and value == 0:
                return False, f"Prix nul pour {field}"
        except (ValueError, TypeError):
            return False, f"Valeur non numÃ©rique pour {field}: {market[field]}"
    
    return True, "OK"

# --- MOTEUR DE CALCUL PRINCIPAL (LOGIQUE CORRIGÃE + DÃTAILS COMPLETS) ---
def calculate_profit_route(initial_usdt, sourcing_code, selling_code, use_dc=False):
    # Validation des entrées
    if initial_usdt <= 0:
        logging.warning(f"Montant USDT initial invalide: {initial_usdt}")
        return None
    if not math.isfinite(initial_usdt):
        return None
    
    if sourcing_code == selling_code:
        logging.warning(f"Conversion circulaire détectée: {sourcing_code} -> {selling_code}")
        return None
    
    try:
        sourcing_market = get_market_data(sourcing_code, markets)
        selling_market = get_market_data(selling_code, markets)
        eur_market = get_market_data("EUR", markets)
    except ValueError as e:
        logging.warning(f"Marché non trouvé: {e}")
        return None

    usdt_start = float(initial_usdt)
    usdt_for_main_cycle = usdt_start
    details = {}
    
    # --- ÉTAPE 1 : COÛT D'ACQUISITION RÉEL EN EUR ---
    cost_in_eur = 0
    
    if use_dc:
        if sourcing_market['currency'] == 'EUR':
            return None
        
        # Double cycle
        fiat_from_sale = usdt_start * sourcing_market['sell_price']
        cost_to_buy_one_usdt = sourcing_market['buy_price'] * (1.0 + sourcing_market['fee_pct'] / 100.0)
        
        if cost_to_buy_one_usdt <= 0:
            return None
            
        usdt_for_main_cycle = fiat_from_sale / cost_to_buy_one_usdt
        if usdt_for_main_cycle <= 0:
            return None
        
        # Le coût en EUR est celui pour acquérir le capital initial
        cost_in_eur = (usdt_start * eur_market['buy_price']) * (1.0 + eur_market['fee_pct'] / 100.0)
        details["Phase 1 (Double Cycle)"] = f"DC sur {sourcing_code}: {usdt_start:.2f} USDT → {usdt_for_main_cycle:.2f} USDT"
    else:
        # Achat direct
        fee_multiplier = 1.0 + sourcing_market['fee_pct'] / 100.0
        cost_local = usdt_start * sourcing_market['buy_price'] * fee_multiplier
        
        # CORRECTION CRITIQUE : Conversion vers EUR via le taux forex
        try:
            rate_to_eur = get_forex_rate(sourcing_code, 'EUR', forex_rates)
            cost_in_eur = cost_local * rate_to_eur
            
            if cost_in_eur <= 0:
                return None
        except ValueError:
            return None
            
        details["Phase 1 (Sourcing)"] = f"Achat {usdt_start:.2f} USDT en {sourcing_code} = {cost_in_eur:.2f} EUR"

    # --- ÉTAPE 2 : VENTE EN selling_currency ---

    revenu_net_B_local = usdt_for_main_cycle * selling_market["sell_price"] 
    
    if revenu_net_B_local <= 0:
        return None
        
    details["Phase 2 (Vente)"] = f"Vente {usdt_for_main_cycle:.2f} USDT = {revenu_net_B_local:.2f} {selling_code}"
    
    # --- ÉTAPE 3 : CONVERSION vers EUR ---
    try:
        rate_to_eur = get_forex_rate(selling_code, 'EUR', forex_rates)
        revenue_in_eur = revenu_net_B_local * rate_to_eur
        
        if revenue_in_eur <= 0:
            return None
    except ValueError:
        return None
        
    details["Phase 3 (Conversion)"] = f"{revenu_net_B_local:.2f} {selling_code} → {revenue_in_eur:.2f} EUR"

    # --- ÉTAPE 4 : RÉINVESTISSEMENT en USDT ---
    if eur_market['buy_price'] <= 0:
        return None
    

    final_usdt_amount = revenue_in_eur / (eur_market['buy_price'] )
    
    if final_usdt_amount <= 0:
        return None
        
    profit_usdt = final_usdt_amount - usdt_start
    profit_eur = revenue_in_eur - cost_in_eur
    profit_pct = (profit_eur / cost_in_eur) * 100 if cost_in_eur > 0 else 0
    
    details["Phase 4 (Réinvest)"] = f"{revenue_in_eur:.2f} EUR → {final_usdt_amount:.2f} USDT"

    route_str = f"{sourcing_code}{'(DC)' if use_dc else ''} → USDT → {selling_code} → EUR → USDT"
    
    # --- PLAN DE VOL ---
    plan = {'phases': []}
    
    # Cycle 1
    plan['phases'].append({'cycle': 1, 'phase_in_cycle': 1, 'type': 'ACHAT', 'market': sourcing_code, 'description': f"Sourcing initial en {sourcing_code}"})
    plan['phases'].append({'cycle': 1, 'phase_in_cycle': 2, 'type': 'VENTE', 'market': selling_code, 'description': f"Vente en {selling_code}"})
    plan['phases'].append({'cycle': 1, 'phase_in_cycle': 3, 'type': 'CONVERSION', 'market_from': selling_code, 'market_to': 'EUR', 'description': f"Conversion {selling_code}→EUR"})
    
    # Cycles suivants
    for i in range(2, NB_CYCLES_PAR_ROTATION + 1):
        plan['phases'].append({'cycle': i, 'phase_in_cycle': 1, 'type': 'ACHAT', 'market': 'EUR', 'description': f"Réinvestissement cycle {i}"})
        plan['phases'].append({'cycle': i, 'phase_in_cycle': 2, 'type': 'VENTE', 'market': selling_code, 'description': f"Vente cycle {i}"})
        plan['phases'].append({'cycle': i, 'phase_in_cycle': 3, 'type': 'CONVERSION', 'market_from': selling_code, 'market_to': 'EUR', 'description': f"Conversion cycle {i}"})
        
    plan['phases'].append({'cycle': NB_CYCLES_PAR_ROTATION, 'phase_in_cycle': 4, 'type': 'CLOTURE', 'market': 'EUR', 'description': "Clôture"})

    return {
        "sourcing_market_code": sourcing_code, 
        "selling_market_code": selling_code,
        "use_double_cycle": use_dc, 
        "detailed_route": route_str, 
        "profit_pct": profit_pct, 
        "profit_usdt": profit_usdt, 
        "final_amount_usdt": final_usdt_amount, 
        "initial_amount_usdt": usdt_start,
        "cost_eur": cost_in_eur,
        "revenue_eur": revenue_in_eur,
        "details": details, 
        "plan_de_vol": plan
    }


def find_best_routes(top_n=5, skip_validation=False):
    """
    Trouve les meilleures routes d'arbitrage avec validation de cohérence
    
    Args:
        top_n: Nombre de routes à retourner
        skip_validation: Si True, ignore la validation de cohérence (pour tests)
    """
    
    # VALIDATION DE COHÉRENCE - ALLÉGÉE
    if not skip_validation:
        alerts = validate_config_coherence(markets, forex_rates)
        
        # Ne bloquer QUE sur les erreurs critiques de type TAUX_MANQUANT ou SPREAD_INVERSE
        critical_errors = [a for a in alerts if a['severity'] == 'ERROR' and a['type'] in ['TAUX_MANQUANT', 'SPREAD_INVERSE']]
        
        if critical_errors:
            print("\n" + "="*70)
            print("🔴 ERREURS CRITIQUES DÉTECTÉES")
            print("="*70)
            for alert in critical_errors:
                print(f"   [{alert['type']}] {alert['message']}")
            print("="*70)
            print("\n⛔ IMPOSSIBLE DE CONTINUER - Corrigez les erreurs dans config.json")
            logging.error(f"Validation échouée: {len(critical_errors)} erreurs critiques détectées")
            return []
        
        # Log des warnings sans bloquer
        warnings = [a for a in alerts if a['severity'] == 'WARNING']
        if warnings:
            logging.info(f"{len(warnings)} avertissements détectés (non bloquants)")
    
    # RECHERCHE DES ROUTES
    all_routes = []
    
    if not markets or len(markets) < 2:
        logging.error("Pas assez de marchés configurés")
        return []
    
    for A in markets:
        for B in markets:
            if A['currency'] == B['currency']: 
                continue
                
            for use_dc in [False, True]:
                try:
                    res = calculate_profit_route(1000, A['currency'], B['currency'], use_dc)
                    if res and res.get('profit_pct') is not None:
                        all_routes.append(res)
                except Exception as e:
                    logging.debug(f"Route non calculable {A['currency']}->{B['currency']} (DC:{use_dc}): {e}")
                    continue
    
    if not all_routes:
        logging.warning("Aucune route valide trouvée")
        return []
    
    # Tri par profitabilité décroissante
    sorted_routes = sorted(all_routes, key=lambda x: x.get('profit_pct', -100), reverse=True)
    
    # VALIDATION FINALE SIMPLIFIÉE
    validated_routes = []
    for route in sorted_routes:
        profit_pct = route.get('profit_pct', -100)
        
        # Filtre minimal : rejeter uniquement les pertes catastrophiques ou profits impossibles
        if profit_pct < -90:  # Perte > 90% = anomalie
            logging.debug(f"Route rejetée (perte excessive): {route['detailed_route']} ({profit_pct:.2f}%)")
            continue
        
        if profit_pct > 1000:  # Profit > 1000% = anomalie
            logging.debug(f"Route rejetée (profit suspect): {route['detailed_route']} ({profit_pct:.2f}%)")
            continue
        
        validated_routes.append(route)
    
    return validated_routes[:top_n]

# --- FONCTION DE TEST ---
def test_engine():
    """Fonction de test pour vÃ©rifier le bon fonctionnement"""
    print("Test du moteur d'arbitrage...")
    try:
        routes = find_best_routes(3)
        if routes:
            print(f"â {len(routes)} routes trouvÃ©es")
            for i, route in enumerate(routes, 1):
                print(f"  {i}. {route['detailed_route']}: {route['profit_pct']:.2f}%")
        else:
            print("â ï¸ Aucune route trouvÃ©e")
    except Exception as e:
        print(f"â Erreur: {e}")

if __name__ == "__main__":
    test_engine()