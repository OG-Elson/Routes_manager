# arbitrage_engine_bis.py

import json
import logging
import math

# --- CHARGEMENT DE LA CONFIGURATION ---
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    markets = config['markets']
    forex_rates = config['forex_rates']
    SEUIL_RENTABILITE_PCT = config['SEUIL_RENTABILITE_PCT']
    NB_CYCLES_PAR_ROTATION = config.get('NB_CYCLES_PAR_ROTATION', 3)
except (FileNotFoundError, KeyError) as e:
    print(f"ERREUR CRITIQUE: Le fichier 'config.json' est manquant ou invalide. DÃ©tail: {e}")
    logging.error(f"Erreur chargement config.json: {e}")
    exit()


# --- FONCTIONS UTILITAIRES ---
def validate_config_coherence(markets, forex_rates):

    """Valide la cohérence des taux de change et prix de marché"""
    alerts = []
    # ========== VALIDATION PRIX NÉGATIFS ==========
    for market in markets:
        currency = market.get('currency', 'INCONNU')

        # Vérifier buy_price
        buy_price = market.get('buy_price', 0)
        if buy_price < 0:
            alerts.append({
                'type': 'PRIX_NEGATIF',
                'severity': 'ERROR',
                'currency': currency,
                'message': f"{currency}: Prix d'achat négatif ({buy_price:.4f}) - INVALIDE. Vérifiez config.json"
            })

        # Vérifier sell_price
        sell_price = market.get('sell_price', 0)
        if sell_price < 0:
            alerts.append({
                'type': 'PRIX_NEGATIF',
                'severity': 'ERROR',
                'message': f"{currency}: Prix de vente négatif ({sell_price:.4f}) - INVALIDE. Vérifiez config.json",
                'severity': 'ERROR',
            })


        # Vérifier fee_pct
        fee_pct = market.get('fee_pct', 0)
        if fee_pct < 0:
            alerts.append({
                'type': 'FRAIS_NEGATIFS',
                'severity': 'ERROR',
                'currency': currency,
                'message': f"{currency}: Frais négatifs ({fee_pct:.2f}%) - INVALIDE. Vérifiez config.json"
            })

    # ========== VALIDATION TAUX FOREX NÉGATIFS ==========
    for pair, rate_data in forex_rates.items():
        # Support ancien format (nombre simple)
        if isinstance(rate_data, (int, float)):
            if rate_data < 0:
                alerts.append({
                    'type': 'TAUX_NEGATIF',
                    'severity': 'ERROR',
                    'currency': currency,
                    'message': f"{pair}: Taux de change négatif ({rate_data:.4f}) - INVALIDE. Vérifiez config.json"
                })
        # Nouveau format (bid/ask/bank_spread_pct)
        elif isinstance(rate_data, dict):
            if rate_data.get('bid', 0) < 0:
                alerts.append({
                    'type': 'TAUX_NEGATIF',
                    'severity': 'ERROR',
                    'currency': currency,
                    'message': f"{pair}: Taux bid négatif ({rate_data['bid']:.4f}) - INVALIDE. Vérifiez config.json"
                })
            if rate_data.get('ask', 0) < 0:
                alerts.append({
                    'type': 'TAUX_NEGATIF',
                    'severity': 'ERROR',
                    'currency': currency,
                    'message': f"{pair}: Taux ask négatif ({rate_data['ask']:.4f}) - INVALIDE. Vérifiez config.json"
                })
            if rate_data.get('bank_spread_pct', 0) < 0:
                alerts.append({
                    'type': 'SPREAD_NEGATIF',
                    'severity': 'ERROR',
                    'currency': currency,
                    'message': f"{pair}: Spread bancaire négatif ({rate_data['bank_spread_pct']:.2f}%) - INVALIDE"
                })
    # Détecter le pivot (devise la plus présente dans forex_rates)
    pivot_counts = {}
    for pair in forex_rates.keys():
        for curr in pair.split('/'):
            pivot_counts[curr] = pivot_counts.get(curr, 0) + 1

    pivot = max(pivot_counts, key=pivot_counts.get) if pivot_counts else 'EUR'

    logging.info(f"Devise pivot détectée : {pivot}")

    # Vérifier que chaque devise de marché a un taux vers le pivot
    for market in markets:
        currency = market['currency']
        if currency == pivot:
            continue

        pair_to_pivot = f"{currency}/{pivot}"
        pair_from_pivot = f"{pivot}/{currency}"

        has_rate = (pair_to_pivot in forex_rates or pair_from_pivot in forex_rates)

        if not has_rate:
            alerts.append({
                'type': 'TAUX_MANQUANT',
                'severity': 'ERROR',
                'message': f"{currency} non relié au pivot {pivot}"
            })

    # Vérifier les écarts buy/sell
    for market in markets:
        if market.get('buy_price', 0) > 0 and market.get('sell_price', 0) > 0:
            spread_pct = ((market['buy_price'] - market['sell_price']) / market['sell_price']) * 100
            print(spread_pct)
            # Spread inversé EXTRÊME (> 10%) = Erreur manifeste
            if spread_pct < -10:
                alerts.append({
                    'type': 'SPREAD_INVERSE',
                    'severity': 'ERROR',
                    'message': f"{market['currency']}: Spread inversé extrême ({spread_pct:.2f}%) - Vérifiez buy_price/sell_price dans config.json"
                })
            # Spread inversé léger (anomalie possible = opportunité)
            elif spread_pct < -0.5:
                alerts.append({
                    'type': 'ANOMALIE_SPREAD',
                    'severity': 'WARNING',
                    'message': f"{market['currency']}: Spread inversé ({spread_pct:.2f}%) - Opportunité d'arbitrage détectée"
                })
            # Spread normal mais élevé
            elif spread_pct > 15:
                alerts.append({
                    'type': 'SPREAD_ANORMAL',
                    'severity': 'WARNING',
                    'message': f"{market['currency']}: Spread élevé ({spread_pct:.2f}%)"
                })

    return alerts

def get_market_data(currency_code, markets_list):
    """Récupere les données de marché pour une devise donnée"""
    for market in markets_list:
        if "currency" in market and market["currency"] == currency_code:
            return market
    raise ValueError(f"Aucun marché trouvé pour la devise '{currency_code}'.")

def safe_divide(numerator, denominator, default=0):
    """Division sécurisée pour Eviter les divisions par zéro"""
    if denominator == 0 or denominator is None:
        logging.warning(f"Division par zéro évitée: {numerator}/{denominator}")
        return default
    try:
        result = numerator / denominator
        if not isinstance(result, (int, float)) or result != result:  # Check for NaN  # pylint: disable=comparison-with-itself
            logging.warning(f"Résultat de division invalide: {numerator}/{denominator} = {result}")
            return default
        return result
    except (ZeroDivisionError, TypeError, ValueError):
        logging.warning(f"Erreur division: {numerator}/{denominator}")
        return default

def get_forex_rate(from_currency, to_currency, forex_rates, conversion_method='forex'):
    """
    Récupère le taux de change avec méthode de conversion
    Convention: EUR/XAF = {bid: prix achat EUR par banque, ask: prix vente EUR par banque}
    """
    if from_currency == to_currency:
        return 1.0

    pair = f"{from_currency}/{to_currency}"
    inverse_pair = f"{to_currency}/{from_currency}"
    found_pair = None
    rate_data = None


    if pair in forex_rates:
        rate_data = forex_rates[pair]
        found_pair = pair
    elif inverse_pair in forex_rates:
        rate_data = forex_rates[inverse_pair]
        found_pair = inverse_pair
    else:
        raise ValueError(f"Taux de change manquant pour {from_currency}→{to_currency}")
        # Décomposer la paire trouvée
    base, quote = found_pair.split('/')

    # ========== ANCIEN FORMAT ==========
    if isinstance(rate_data, (int, float)):
        if rate_data <= 0:
            raise ValueError(f"Taux forex invalide: {rate_data}")

         # On veut quote→base, on a base/quote
        if from_currency == base and to_currency == quote:
            return 1.0 / rate_data
        elif from_currency == quote and to_currency == base:
            return rate_data
        else:
            raise ValueError(f"Incohérence ancien format: {found_pair}, conversion {from_currency}→{to_currency}")

    # ========== NOUVEAU FORMAT ==========
    if not isinstance(rate_data, dict):
        raise ValueError(f"Format de taux invalide: {type(rate_data)}")

    bid = rate_data.get('bid', 0)
    ask = rate_data.get('ask', 0)

    if bid <= 0 or ask <= 0:
        raise ValueError(f"Taux bid/ask invalides: bid={bid}, ask={ask}")


    # --- MÉTHODE BANQUE ---
    if conversion_method == 'bank':
        mid_rate = (bid + ask) / 2
        spread = rate_data.get('bank_spread_pct', 0) / 100.0

        if from_currency == base and to_currency == quote:
            # On veut base→quote, on a base/quote
            # Ex: XAF→EUR avec XAF/EUR bid=650
            # 650 XAF = 1 EUR, donc 1 XAF = 1/650 EUR
            # Spread défavorable : on reçoit moins
            return (1 / mid_rate) * (1 - spread)


        elif from_currency == quote and to_currency == base:
            # On veut quote→base, on a base/quote
            # Ex: EUR→XAF avec XAF/EUR bid=650
            # On vend EUR, on reçoit 650 XAF (moins le spread)
            return mid_rate * (1 - spread)

        else:
            raise ValueError(f"Incohérence: paire {found_pair}, conversion {from_currency}→{to_currency}")

    # --- MÉTHODE FOREX ---
    if from_currency == base and to_currency == quote:
        # On veut base→quote, on a base/quote
        # Ex: XAF→EUR avec XAF/EUR bid=650, ask=660
        # On vend XAF (base) pour acheter EUR (quote)
        # La banque achète EUR à bid → 650 XAF = 1 EUR
        # Donc 1 XAF = 1/650 EUR
        # Mais pour nous, c'est défavorable, donc on utilise bid (le plus bas)
        return 1.0 / ask

    elif from_currency == quote and to_currency == base:
        # On veut quote→base, on a base/quote
        # Ex: EUR→XAF avec XAF/EUR bid=650, ask=660
        # On vend EUR (quote) pour acheter XAF (base)
        # La banque achète EUR à bid → on reçoit 650 XAF par EUR
        return bid

    else:
        raise ValueError(f"Incohérence: paire {found_pair}, conversion {from_currency}→{to_currency}")


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
def calculate_profit_route(initial_usdt, sourcing_code, selling_code,conversion_method='forex'):
    """
        Args ajouté:
        conversion_method: 'forex' ou 'bank'
    """
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


        # Achat direct
    fee_multiplier = 1.0 + sourcing_market['fee_pct'] / 100.0
    cost_local = usdt_start * sourcing_market['buy_price'] * fee_multiplier

    # CORRECTION CRITIQUE : Conversion vers EUR via le taux forex

    try:
        rate_to_eur = get_forex_rate(sourcing_code, 'EUR', forex_rates,conversion_method)
        cost_in_eur = cost_local * rate_to_eur

        if cost_in_eur <= 0:
            return None
    except ValueError:
        return None

    details["Phase 1 (Sourcing)"] = f"Achat {usdt_start:.2f} USDT en {sourcing_code} = {cost_in_eur:.2f} EUR"

    # --- ÉTAPE 2 : VENTE EN selling_currency ---


    revenu_brut_B_local = usdt_for_main_cycle * selling_market["sell_price"]
    fee_multiplier_sell = 1.0 - (selling_market["fee_pct"] / 100.0)  # Frais déduits
    revenu_net_B_local = revenu_brut_B_local * fee_multiplier_sell

    if revenu_net_B_local <= 0:
        return None

    details["Phase 2 (Vente)"] = f"Vente {usdt_for_main_cycle:.2f} USDT = {revenu_net_B_local:.2f} {selling_code}"

    # --- ÉTAPE 3 : CONVERSION vers EUR ---
    try:
        rate_to_eur = get_forex_rate(selling_code, 'EUR', forex_rates,conversion_method)
        revenue_in_eur = revenu_net_B_local * rate_to_eur

        if revenue_in_eur <= 0:
            return None
    except ValueError:
        return None

    details["Phase 3 (Conversion)"] = f"{revenu_net_B_local:.2f} {selling_code} → {revenue_in_eur:.2f} EUR"

    # --- ÉTAPE 4 : RÉINVESTISSEMENT en USDT ---
    if eur_market['buy_price'] <= 0:
        return None



    cost_per_usdt = eur_market['buy_price'] * (1.0 + eur_market['fee_pct'] / 100.0)
    final_usdt_amount = revenue_in_eur / cost_per_usdt
    if final_usdt_amount <= 0:
        return None

    profit_usdt = final_usdt_amount - usdt_start
    profit_eur = revenue_in_eur - cost_in_eur
    profit_pct = (profit_eur / cost_in_eur) * 100 if cost_in_eur > 0 else 0

    details["Phase 4 (Réinvest)"] = f"{revenue_in_eur:.2f} EUR → {final_usdt_amount:.2f} USDT"

    route_str = f"{sourcing_code}'(DC)' → USDT → {selling_code} → EUR → USDT"

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
        "conversion_method": conversion_method,
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

def find_routes_with_filters(
    top_n=5,
    skip_validation=False,
    apply_threshold=True,
    sourcing_currency=None,
    excluded_markets=None,
    loop_currency=None,
    conversion_method='forex'
):
    """
    Fonction CENTRALE pour trouver routes d'arbitrage avec filtres avancés

    Args:
        top_n: Nombre de routes à retourner
        skip_validation: Ignorer validation cohérence (tests uniquement)
        apply_threshold: Appliquer seuil de rentabilité
        sourcing_currency: Forcer devise de sourcing (ex: 'EUR')
        excluded_markets: Liste devises exclues comme marché de VENTE
        loop_currency: Devise de bouclage (prioritaire sur excluded_markets)

    Returns:
        Liste de routes triées par profitabilité décroissante
    """

    # ========== VALIDATION DE COHÉRENCE - ALLÉGÉE ==========
    if not skip_validation:
        alerts = validate_config_coherence(markets, forex_rates)

        # Ne bloquer QUE sur erreurs critiques
        critical_errors = [a for a in alerts if a['severity'] == 'ERROR' and
                          a['type'] in ['TAUX_MANQUANT', 'SPREAD_INVERSE']]

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

    # ========== RECHERCHE DES ROUTES ==========
    all_routes = []

    if not markets or len(markets) < 2:
        logging.error("Pas assez de marchés configurés")
        return []

    # Normaliser les paramètres
    excluded_markets = excluded_markets or []

    for market_a in markets:
        # Filtre sourcing (nouveau)
        if sourcing_currency and market_a['currency'] != sourcing_currency:
            continue

        for market_b in markets:
            if market_a['currency'] == market_b['currency']:
                continue

            # Filtre exclusions (nouveau)
            if market_b['currency'] in excluded_markets:
                # Exception : bouclage forcé prioritaire
                if not (loop_currency and market_b['currency'] == loop_currency):
                    logging.debug(f"Route {market_a['currency']}→{market_b['currency']} exclue")
                    continue

            route = calculate_profit_route(
                    initial_usdt=1000,
                    sourcing_code=market_a['currency'],
                    selling_code=market_b['currency'],
                    conversion_method=conversion_method
            )

            if route:
                    all_routes.append(route)



    if not all_routes:
        logging.warning("Aucune route valide trouvée")
        return []

    # ========== TRI PAR PROFITABILITÉ ==========
    sorted_routes = sorted(all_routes, key=lambda x: x.get('profit_pct', -100), reverse=True)

    # ========== VALIDATION FINALE SIMPLIFIÉE ==========
    validated_routes = []
    for route in sorted_routes:
        profit_pct = route.get('profit_pct', -100)

        # Filtre anomalies : rejeter pertes catastrophiques ou profits impossibles
        if profit_pct < -90:  # Perte > 90% = anomalie
            logging.debug(f"Route rejetée (perte excessive): {route['detailed_route']} ({profit_pct:.2f}%)")
            continue

        if profit_pct > 1000:  # Profit > 1000% = anomalie
            logging.debug(f"Route rejetée (profit suspect): {route['detailed_route']} ({profit_pct:.2f}%)")
            continue

        # Filtre seuil de rentabilité
        if apply_threshold and profit_pct < SEUIL_RENTABILITE_PCT:
            logging.debug(f"Route rejetée (sous seuil): {route['detailed_route']} ({profit_pct:.2f}%)")
            continue

        validated_routes.append(route)

    return validated_routes[:top_n]


# ========== FONCTION LEGACY (compatibilité) ==========
def find_best_routes(top_n=5, skip_validation=False, apply_threshold=True,conversion_method='forex'):
    """
    LEGACY - Wrapper pour compatibilité avec daily_briefing.py
    Utilise find_routes_with_filters() en interne
    """
    return find_routes_with_filters(
        top_n=top_n,
        skip_validation=skip_validation,
        apply_threshold=apply_threshold,
        conversion_method=conversion_method
    )

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
