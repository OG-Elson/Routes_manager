# modules/scenario_generator.py

# modules/scenario_generator.py (EXTRAIT - PARTIE À CORRIGER)
import json


def calculate_transaction_amounts(capital_eur, expected_margin, nb_cycles=1):
    """Calcule les montants réels des transactions basés sur le capital et la marge"""

    # Taux de change simulés (approximatifs)
    eur_to_usdt = 1.10
    usdt_to_xaf = 620.0
    xaf_to_eur = 1 / 655.0

    transactions = []
    current_capital_eur = capital_eur

    for cycle in range(nb_cycles):
        # Phase 1 : ACHAT EUR → USDT
        amount_usdt = current_capital_eur * eur_to_usdt
        transactions.append({
            'type': 'ACHAT',
            'market': 'EUR',
            'amount_usdt': round(amount_usdt, 2),
            'amount_local': round(current_capital_eur, 2),
            'fee_pct': 0.001,
            'payment_method': 'Bank Transfer',
            'counterparty_id': 'BUYER_001',
            'notes': f'Achat USDT cycle {cycle+1}'
        })

        # Phase 2 : VENTE USDT → XAF
        amount_xaf = amount_usdt * usdt_to_xaf
        transactions.append({
            'type': 'VENTE',
            'market': 'XAF',
            'amount_usdt': round(amount_usdt, 2),
            'amount_local': round(amount_xaf, 2),
            'fee_pct': 0.001,
            'payment_method': 'Mobile Money',
            'counterparty_id': 'SELLER_001',
            'notes': f'Vente USDT cycle {cycle+1}'
        })

        # Phase 3 : CONVERSION XAF → EUR
        current_capital_eur = amount_xaf * xaf_to_eur

        # CORRECTION COMPLÈTE
        transactions.append({
            'type': 'CONVERSION',
            'market': 'XAF->EUR',  # Format pour create_transactions_csv
            'amount_usdt': round(amount_usdt, 2),  # ← CORRECTION: Montant USDT du cycle
            'amount_sent': round(amount_xaf, 2),        # Montant envoyé
            'amount_received': round(current_capital_eur, 2),  # Montant reçu
            'amount_local': round(current_capital_eur, 2),  # Pour compatibilité
            'fee_pct': 0.001,
            'payment_method': 'Forex',
            'counterparty_id': 'CONVERTER_001',
            'notes': f'Conversion XAF→EUR cycle {cycle+1}'
        })


    # Appliquer la marge attendue au capital final
    final_capital = capital_eur * (1 + expected_margin)

    return transactions, final_capital

def generate_standard_scenarios():
    """Génère les scénarios de tests standards"""
    scenarios = []
    test_id = 1

    capitals = [500, 1000, 2000, 5000]
    margins = [0.02, 0.05, 0.08]  # 2%, 5%, 8%
    cycles_list = [1, 2]

    for capital in capitals:
        for margin in margins:
            for nb_cycles in cycles_list:
                transactions, final_capital = calculate_transaction_amounts(capital, margin, nb_cycles)

                # Nombre de transactions = 3 par cycle + 1 clôture
                expected_tx_count = (nb_cycles * 3) + 1
                expected_sequence = []
                for _ in range(nb_cycles):
                    expected_sequence.extend(['ACHAT', 'VENTE', 'CONVERSION'])
                expected_sequence.append('CLOTURE')

                scenario = {
                    'id': f'STD_{test_id:03d}',
                    'name': f'Standard - Capital {capital}€, Marge {margin*100:.0f}%, {nb_cycles} cycle(s)',
                    'category': 'standard',
                    'capital_eur': capital,
                    'expected_margin': margin,
                    'nb_cycles': nb_cycles,
                    'transactions': transactions,
                    'expected_results': {
                        'tx_count': expected_tx_count,
                        'tx_sequence': expected_sequence,
                        'plan_phases': expected_tx_count,
                        'capital_invested': capital,
                        'capital_final': round(final_capital, 2),
                        'profit': round(final_capital - capital, 2),
                        'roi': margin
                    }
                }
                scenarios.append(scenario)
                test_id += 1

    return scenarios

def generate_loop_scenarios():
    """Génère les scénarios avec bouclage"""
    scenarios = []
    test_id = 1

    loop_configs = [
        {'currency': 'EUR', 'loops': 2},
        {'currency': 'EUR', 'loops': 3},
        {'currency': 'XAF', 'loops': 2},
        {'currency': 'XAF', 'loops': 3},
    ]

    capital = 1000
    margin = 0.05

    for config in loop_configs:
        nb_loops = config['loops']
        loop_currency = config['currency']

        transactions, final_capital = calculate_transaction_amounts(capital, margin, nb_loops)

        expected_tx_count = (nb_loops * 3) + 1
        expected_sequence = []
        for _ in range(nb_loops):
            expected_sequence.extend(['ACHAT', 'VENTE', 'CONVERSION'])
        expected_sequence.append('CLOTURE')

        scenario = {
            'id': f'LOOP_{test_id:03d}',
            'name': f'Bouclage sur {loop_currency} - {nb_loops} boucles',
            'category': 'loop',
            'capital_eur': capital,
            'expected_margin': margin,
            'nb_cycles': nb_loops,
            'loop_enabled': True,
            'loop_currency': loop_currency,
            'nb_loops': nb_loops,
            'transactions': transactions,
            'expected_results': {
                'tx_count': expected_tx_count,
                'plan_phases': expected_tx_count,
                'capital_invested': capital,
                'loops_completed': nb_loops
            }
        }
        scenarios.append(scenario)
        test_id += 1

    return scenarios

def generate_force_scenarios():
    """Génère les scénarios avec forçage de transactions"""
    scenarios = []

    # Scénario 1 : Forcer un ACHAT au lieu d'une VENTE
    transactions, _ = calculate_transaction_amounts(1000, 0.05, 1)
    # Modifier la 2ème transaction (normalement VENTE) en ACHAT
    transactions[1] = transactions[1].copy()
    transactions[1]['type'] = 'ACHAT'
    transactions[1]['notes'] = '[FORCÉ] Achat forcé au lieu de vente'

    scenarios.append({
        'id': 'FORCE_001',
        'name': 'Forcer ACHAT au lieu de VENTE',
        'category': 'force',
        'capital_eur': 1000,
        'expected_margin': 0.05,
        'nb_cycles': 1,
        'force_transaction': {
            'at_step': 2,
            'forced_type': 'ACHAT',
            'reason': 'Test forçage type transaction'
        },
        'transactions': transactions,
        'expected_results': {
            'tx_count': 4,
        }
    })

    # Scénario 2 : Clôture prématurée
    transactions_premature, _ = calculate_transaction_amounts(1000, 0.05, 1)
    # Garder seulement les 2 premières transactions
    transactions_premature = transactions_premature[:2]

    scenarios.append({
        'id': 'FORCE_002',
        'name': 'Clôture prématurée au cycle 1',
        'category': 'force',
        'capital_eur': 1000,
        'expected_margin': 0.05,
        'nb_cycles': 1,
        'premature_closure': True,
        'transactions': transactions_premature,
        'expected_results': {
            'tx_count': 3,  # 2 transactions + 1 CLOTURE
        }
    })

    # Scénarios 3-15 : Variations diverses
    for i in range(3, 16):
        transactions, _ = calculate_transaction_amounts(1000, 0.05, 1)

        scenarios.append({
            'id': f'FORCE_{i:03d}',
            'name': f'Forçage variation {i}',
            'category': 'force',
            'capital_eur': 1000,
            'expected_margin': 0.05,
            'nb_cycles': 1,
            'transactions': transactions,
            'expected_results': {
                'tx_count': 4,
            }
        })

    return scenarios

def generate_edge_scenarios():
    """Génère les scénarios de cas limites"""
    scenarios = []


    # Scénario 1 : Capital minimum
    transactions, final_capital = calculate_transaction_amounts(200, 0.05, 1)
    scenarios.append({
        'id': 'EDGE_001',
        'name': 'Capital minimum - 200€',
        'category': 'edge',
        'capital_eur': 200,
        'expected_margin': 0.05,
        'nb_cycles': 1,
        'transactions': transactions,
        'expected_results': {
            'capital_invested': 200,
            'capital_final': round(final_capital, 2),
            'profit': round(final_capital - 200, 2),
            'roi': 0.05
        }
    })

    # Scénario 2 : Capital élevé
    transactions, final_capital = calculate_transaction_amounts(50000, 0.03, 1)
    scenarios.append({
        'id': 'EDGE_002',
        'name': 'Capital élevé - 50,000€',
        'category': 'edge',
        'capital_eur': 50000,
        'expected_margin': 0.03,
        'nb_cycles': 1,
        'transactions': transactions,
        'expected_results': {
            'capital_invested': 50000,
            'capital_final': round(final_capital, 2),
            'profit': round(final_capital - 50000, 2),
            'roi': 0.03
        }
    })

    # Scénario 3 : Perte
    capital = 1000
    loss_margin = -0.02
    transactions, _ = calculate_transaction_amounts(capital, 0.05, 1)
    final_capital = capital * (1 + loss_margin)

    scenarios.append({
        'id': 'EDGE_003',
        'name': 'Scénario avec perte - -2%',
        'category': 'edge',
        'capital_eur': capital,
        'expected_margin': loss_margin,
        'nb_cycles': 1,
        'transactions': transactions,
        'expected_results': {
            'capital_invested': capital,
            'capital_final': round(final_capital, 2),
            'profit': round(final_capital - capital, 2),
            'roi': loss_margin
        }
    })

    # Scénarios 4-20 : Différents capitaux
    test_capitals = range(1400, 3100, 100)
    for idx, cap in enumerate(test_capitals, start=4):
        margin = 0.03 + (idx % 5) * 0.005  # Marges variables
        transactions, final_capital = calculate_transaction_amounts(cap, margin, 1)

        scenarios.append({
            'id': f'EDGE_{idx:03d}',
            'name': f'Edge case {idx} - {cap}€',
            'category': 'edge',
            'capital_eur': cap,
            'expected_margin': margin,
            'nb_cycles': 1,
            'transactions': transactions,
            'expected_results': {
                'capital_invested': cap,
                'capital_final': round(final_capital, 2),
                'profit': round(final_capital - cap, 2),
                'roi': margin
            }
        })

    return scenarios

# Dans scenario_generator.py, remplace generate_error_scenarios() par :
def generate_error_scenarios():
    """Génère les scénarios d'erreurs attendues"""
    scenarios = []

    # Charger le vrai config
    with open('config.json', 'r') as f:
        real_config = json.load(f)

    for i in range(1, 16):
        # Créer une config INVALIDE en inversant buy/sell
        broken_markets = []
        for m in real_config['markets'][:3]:  # Prendre 3 marchés
            broken = m.copy()
            if i % 2 == 0:
                # Inverser buy/sell (spread négatif)
                broken['buy_price'], broken['sell_price'] = broken['sell_price'], broken['buy_price']
            broken_markets.append(broken)

        scenario = {
            'id': f'ERROR_{i:03d}',
            'name': f'Config invalide {i}',
            'category': 'error',
            'expected_error': True,
            'config_override': {
                'markets': broken_markets
            }
        }
        scenarios.append(scenario)

    return scenarios

def generate_all_scenarios():
    """Génère tous les scénarios de tests"""
    all_scenarios = []

    all_scenarios.extend(generate_standard_scenarios())
    all_scenarios.extend(generate_loop_scenarios())
    all_scenarios.extend(generate_force_scenarios())
    all_scenarios.extend(generate_edge_scenarios())
    all_scenarios.extend(generate_error_scenarios())

    return all_scenarios


class ScenarioGenerator:
    """Classe pour générer les scénarios de tests"""

    def __init__(self):
        self.scenarios = generate_all_scenarios()

    def get_all_scenarios(self):
        """Retourne tous les scénarios"""
        return self.scenarios

    def get_scenarios_by_category(self, category):
        """Retourne les scénarios d'une catégorie spécifique"""
        return [s for s in self.scenarios if s.get('category') == category]

    def get_scenario_by_id(self, scenario_id):
        """Retourne un scénario par son ID"""
        for scenario in self.scenarios:
            if scenario['id'] == scenario_id:
                return scenario
        return None

