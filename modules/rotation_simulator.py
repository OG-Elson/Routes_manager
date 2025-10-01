# modules/rotation_simulator.py

import sys
import os
import json
import shutil
import csv
from datetime import datetime
from pathlib import Path

class RotationSimulator:
    """Simule l'exécution complète d'une rotation EN APPELANT LE VRAI MOTEUR"""
    
    def __init__(self, scenario, interaction_simulator):
        self.scenario = scenario
        self.simulator = interaction_simulator
        
    def execute(self):
        """Exécute le scénario complet"""
        try:
            self.prepare_environment()
            
            if self.scenario.get('config_override'):
                self.apply_config_override()
            
            if self.scenario['category'] == 'error':
                return self.execute_error_scenario()
            elif self.scenario.get('loop_enabled'):
                return self.execute_loop_scenario()
            elif self.scenario.get('force_transaction'):
                return self.execute_force_scenario()
            else:
                return self.execute_standard_scenario()
                
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        finally:
            self.restore_config()
    
    def prepare_environment(self):
        """Prépare l'environnement de test"""
        if os.path.exists('config.json'):
            shutil.copy('config.json', 'config.json.backup')
    
    def apply_config_override(self):
        """Applique les modifications de config pour les tests d'erreur"""
        override = self.scenario['config_override']
        
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        for key, value in override.items():
            if key == 'markets':
                config['markets'] = value
            elif key == 'forex_rates':
                config['forex_rates'] = value
        
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def restore_config(self):
        """Restaure le config.json original"""
        if os.path.exists('config.json.backup'):
            shutil.copy('config.json.backup', 'config.json')
            os.remove('config.json.backup')
    
    def generate_rotation_id(self):
        """Génère un ID de rotation unique"""
        today_str = datetime.now().strftime("%Y%m%d")
        return f"R{today_str}-{self.scenario['id']}"
    
    def get_real_route_from_engine(self):
        """APPELLE LE VRAI MOTEUR pour obtenir une route réelle"""
        try:
            from arbitrage_engine_bis import find_best_routes
            
            routes = find_best_routes(top_n=5)
            
            if not routes:
                raise Exception("Aucune route trouvée par le moteur")
            
            # Utiliser la meilleure route
            return routes[0]
            
        except Exception as e:
            raise Exception(f"Erreur moteur d'arbitrage: {e}")
    
    def calculate_real_transactions(self, route, capital_eur, nb_cycles):
        """Calcule les transactions RÉELLES basées sur la route du moteur"""
        transactions = []
        
        sourcing_market = route['sourcing_market_code']
        selling_market = route['selling_market_code']
        
        # Charger les prix depuis config.json
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        markets_data = {m['currency']: m for m in config['markets']}
        forex_rates = config['forex_rates']
        
        current_usdt = capital_eur / markets_data['EUR']['buy_price']
        
        for cycle in range(1, nb_cycles + 1):
            # Phase 1: ACHAT
            usdt_to_buy = current_usdt
            local_cost = usdt_to_buy * markets_data[sourcing_market]['buy_price']
            
            transactions.append({
                'type': 'ACHAT',
                'market': sourcing_market,
                'amount_usdt': round(usdt_to_buy, 2),
                'amount_local': round(local_cost, 2),
                'fee_pct': markets_data[sourcing_market]['fee_pct'],
                'payment_method': 'Bank Transfer',
                'counterparty_id': f'BUYER_{cycle:03d}',
                'notes': f'Achat cycle {cycle} - TEST {self.scenario["id"]}'
            })
            
            # Phase 2: VENTE
            local_received = usdt_to_buy * markets_data[selling_market]['sell_price']
            
            transactions.append({
                'type': 'VENTE',
                'market': selling_market,
                'amount_usdt': round(usdt_to_buy, 2),
                'amount_local': round(local_received, 2),
                'fee_pct': markets_data[selling_market]['fee_pct'],
                'payment_method': 'Mobile Money',
                'counterparty_id': f'SELLER_{cycle:03d}',
                'notes': f'Vente cycle {cycle}'
            })
            
            # Phase 3: CONVERSION vers EUR
            rate = forex_rates.get(f"{selling_market}/EUR", 1.0)
            eur_received = local_received / rate
            
            transactions.append({
                'type': 'CONVERSION',
                'market': f'{selling_market}->EUR',
                'amount_sent': round(local_received, 2),
                'amount_received': round(eur_received, 2),
                'amount_usdt': round(usdt_to_buy, 2),
                'amount_local': round(eur_received, 2),
                'fee_pct': 0,
                'payment_method': 'Forex',
                'counterparty_id': f'CONVERTER_{cycle:03d}',
                'notes': f'Conversion cycle {cycle}'
            })
            
            # Préparer le prochain cycle
            current_usdt = eur_received / markets_data['EUR']['buy_price']
        
        return transactions
    
    def create_transactions_csv(self, rotation_id, transactions):
        """Crée le fichier transactions.csv"""
        os.makedirs('test_output', exist_ok=True)
        filename = 'test_output/transactions.csv'
        
        fieldnames = ['Date', 'Rotation_ID', 'Type', 'Market', 'Currency', 'Amount_USDT', 
                      'Price_Local', 'Amount_Local', 'Fee_Pct', 'Payment_Method', 
                      'Counterparty_ID', 'Notes']
        
        file_exists = os.path.exists(filename)
        
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            
            if not file_exists:
                writer.writeheader()
            
            for trans in transactions:
                row = {
                    'Date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'Rotation_ID': rotation_id,
                    'Type': trans['type'],
                    'Market': trans.get('market', 'N/A'),
                    'Currency': trans.get('market', 'N/A').split('->')[0] if '->' in trans.get('market', '') else trans.get('market', 'N/A'),
                    'Amount_USDT': trans.get('amount_usdt', 0),
                    'Price_Local': trans.get('amount_local', 0) / trans.get('amount_usdt', 1) if trans.get('amount_usdt', 0) > 0 else 0,
                    'Amount_Local': trans.get('amount_local', 0),
                    'Fee_Pct': trans.get('fee_pct', 0),
                    'Payment_Method': trans.get('payment_method', 'N/A'),
                    'Counterparty_ID': trans.get('counterparty_id', 'N/A'),
                    'Notes': trans.get('notes', 'N/A')
                }
                writer.writerow(row)
        
        return True
    
    def create_debriefing_csv(self, rotation_id):
        """Crée le fichier debriefing.csv"""
        os.makedirs('test_output', exist_ok=True)
        filename = 'test_output/debriefing.csv'
        
        fieldnames = ['Date', 'Rotation_ID', 'Difficulté_Rencontrée', 'Leçon_Apprise']
        
        file_exists = os.path.exists(filename)
        
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'Date': datetime.now().strftime('%Y-%m-%d'),
                'Rotation_ID': rotation_id,
                'Difficulté_Rencontrée': '',
                'Leçon_Apprise': f'Test automatisé - {self.scenario["id"]}'
            })
        
        return True
    
    def create_plan_de_vol(self, rotation_id, route, nb_cycles):
        """Crée le plan de vol JSON basé sur la route réelle"""
        os.makedirs('test_output', exist_ok=True)
        
        phases = []
        
        for cycle in range(1, nb_cycles + 1):
            phases.append({
                'cycle': cycle,
                'phase_in_cycle': 1,
                'type': 'ACHAT',
                'market': route['sourcing_market_code'],
                'description': f'Sourcing Cycle {cycle}'
            })
            phases.append({
                'cycle': cycle,
                'phase_in_cycle': 2,
                'type': 'VENTE',
                'market': route['selling_market_code'],
                'description': f'Vente Cycle {cycle}'
            })
            phases.append({
                'cycle': cycle,
                'phase_in_cycle': 3,
                'type': 'CONVERSION',
                'market_from': route['selling_market_code'],
                'market_to': 'EUR',
                'description': f'Conversion Cycle {cycle}'
            })
        
        phases.append({
            'cycle': nb_cycles,
            'phase_in_cycle': 4,
            'type': 'CLOTURE',
            'market': 'EUR',
            'description': 'Clôture de la rotation'
        })
        
        plan = route.copy()
        plan['rotation_id'] = rotation_id
        plan['plan_de_vol'] = {'phases': phases}
        
        plan_file = f'test_output/rotation_plan_{rotation_id}.json'
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        
        return True
    
    def execute_standard_scenario(self):
        """Exécute un scénario standard EN UTILISANT LE VRAI MOTEUR"""
        try:
            rotation_id = self.generate_rotation_id()
            
            # 1. APPELER LE VRAI MOTEUR
            print(f"    [MOTEUR] Calcul de route avec arbitrage_engine_bis...")
            route = self.get_real_route_from_engine()
            print(f"    [MOTEUR] Route: {route['detailed_route']} ({route['profit_pct']:.2f}%)")
            
            # 2. Calculer les transactions RÉELLES
            capital = self.scenario.get('capital_eur', 1000)
            nb_cycles = self.scenario.get('nb_cycles', 1)
            
            transactions = self.calculate_real_transactions(route, capital, nb_cycles)
            
            # 3. Créer le plan de vol
            self.create_plan_de_vol(rotation_id, route, nb_cycles)
            
            # 4. Ajouter CLOTURE
            transactions.append({
                'type': 'CLOTURE',
                'market': 'EUR',
                'amount_usdt': 0,
                'amount_local': 0,
                'fee_pct': 0,
                'payment_method': 'N/A',
                'counterparty_id': 'N/A',
                'notes': f'Clôture test {self.scenario["id"]}'
            })
            
            self.create_transactions_csv(rotation_id, transactions)
            self.create_debriefing_csv(rotation_id)
            
            # 5. Générer KPIs avec le BON chemin
            try:
                from update_kpis_v4_bis import analyze_transactions
                analyze_transactions('test_output/transactions.csv', mode='compact')
            except Exception as e:
                print(f"    [WARN] KPIs non générés: {e}")
            
            return {'success': True}
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def execute_loop_scenario(self):
        """Exécute un scénario avec bouclage"""
        try:
            rotation_id = self.generate_rotation_id()
            
            # Appeler le moteur
            print(f"    [MOTEUR] Calcul de route avec arbitrage_engine_bis...")
            route = self.get_real_route_from_engine()
            print(f"    [MOTEUR] Route: {route['detailed_route']} ({route['profit_pct']:.2f}%)")
            
            capital = self.scenario.get('capital_eur', 1000)
            nb_cycles = self.scenario.get('nb_cycles', 1)
            loop_currency = self.scenario.get('loop_currency', 'EUR')
            
            transactions = self.calculate_real_transactions(route, capital, nb_cycles)
            
            self.create_plan_de_vol(rotation_id, route, nb_cycles)
            
            # CRÉER rotation_state.json dans test_output
            state = {
                'active_rotations': {
                    rotation_id: {
                        'rotation_id': rotation_id,
                        'loop_currency': loop_currency,
                        'cycles_completed': nb_cycles,
                        'forced_transactions': []
                    }
                }
            }
            
            with open('test_output/rotation_state.json', 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            transactions.append({
                'type': 'CLOTURE',
                'market': loop_currency,
                'amount_usdt': 0,
                'amount_local': 0,
                'fee_pct': 0,
                'payment_method': 'N/A',
                'counterparty_id': 'N/A',
                'notes': f'Clôture loop test {self.scenario["id"]}'
            })
            
            self.create_transactions_csv(rotation_id, transactions)
            self.create_debriefing_csv(rotation_id)
            
            return {'success': True}
            
        except Exception as e:
            import traceback
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def execute_force_scenario(self):
        """Exécute un scénario avec forçage"""
        return self.execute_standard_scenario()
    
    def execute_error_scenario(self):
        """Exécute un scénario d'erreur"""
        try:
            from arbitrage_engine_bis import find_best_routes
            
            routes = find_best_routes(skip_validation=False)
            
            if self.scenario.get('expected_error'):
                if not routes:
                    return {'success': True}
                else:
                    return {'success': False, 'error': 'Erreur attendue mais routes trouvées'}
            
            return {'success': True}
            
        except Exception as e:
            if self.scenario.get('expected_error'):
                return {'success': True}
            
            import traceback
            return {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }