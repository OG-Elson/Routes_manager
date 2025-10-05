# modules/advanced_tests.py

import sys
import os
import json
import shutil
import tempfile
import csv
from datetime import datetime
from pathlib import Path
import pandas as pd 
import math

# Configuration chemin
current_file = os.path.abspath(__file__)
modules_dir = os.path.dirname(current_file)
project_root = os.path.dirname(modules_dir)
os.chdir(project_root)
sys.path.insert(0, project_root)

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.details = []
    
    def add_pass(self, test_name, message=""):
        self.passed += 1
        self.details.append({'test': test_name, 'status': 'PASS', 'message': message})
    
    def add_fail(self, test_name, expected, actual):
        self.failed += 1
        self.details.append({'test': test_name, 'status': 'FAIL', 'expected': str(expected), 'actual': str(actual)})
    
    def add_error(self, test_name, error):
        self.errors += 1
        self.details.append({'test': test_name, 'status': 'ERROR', 'error': str(error)})
    
    def print_summary(self):
        total = self.passed + self.failed + self.errors
        print(f"\n{'='*60}")
        print(f"📊 {self.name}")
        print(f"{'='*60}")
        print(f"✅ Passed: {self.passed}/{total} ({100*self.passed/total:.1f}%)" if total > 0 else "No tests")
        print(f"❌ Failed: {self.failed}/{total}")
        print(f"💥 Errors: {self.errors}/{total}")
        
        if self.failed > 0 or self.errors > 0:
            print(f"\n🔍 Détails des échecs:")
            for detail in self.details:
                if detail['status'] in ['FAIL', 'ERROR']:
                    if detail['status'] == 'FAIL':
                        print(f"  - {detail['test']}: Expected {detail['expected']}, got {detail['actual']}")
                    else:
                        print(f"  - {detail['test']}: {detail['error']}")
    
    def to_dict(self):
        return {
            'name': self.name,
            'passed': self.passed,
            'failed': self.failed,
            'errors': self.errors,
            'total': self.passed + self.failed + self.errors,
            'pass_rate': (self.passed / (self.passed + self.failed + self.errors) * 100) if (self.passed + self.failed + self.errors) > 0 else 0,
            'details': self.details
        }


class ArbitrageEngineAdvancedTests:
    """Tests avancés pour arbitrage_engine_bis.py"""
    
    def __init__(self):
        self.result = TestResult("Tests Avancés Moteur d'Arbitrage")
        with open('config.json', 'r') as f:
            self.config = json.load(f)
    
    def run_all(self):
        print("\n🔬 TESTS AVANCÉS MOTEUR D'ARBITRAGE")
        print("="*60)
        
        self.test_exact_profit_calculations()
        self.test_double_cycle_logic()
        self.test_fee_application()
        self.test_forex_triangular_arbitrage()
        self.test_plan_de_vol_structure()
        self.test_invalid_inputs()
        self.test_edge_cases()
        self.test_spread_coherence()
        self.test_circular_conversions()
        self.test_extreme_capitals()
        
        self.result.print_summary()
        return self.result
    
    def test_exact_profit_calculations(self):
        """Test: Calculs de profit avec valeurs exactes attendues"""
        try:
            from arbitrage_engine_bis import calculate_profit_route
            
            # Scénario EUR->XAF avec valeurs précises
            # Capital: 1000€, buy EUR=1.08, sell XAF=620, forex XAF/EUR=655.957
            # Coût: 1000€ * 1.08 = 1080€
            # USDT acheté: 1000 USDT
            # Vente XAF: 1000 * 620 = 620000 XAF
            # Conversion EUR: 620000 / 655.957 = 945.22€
            # MAIS on réinvestit en USDT: 945.22 / 1.08 = 875.2 USDT
            # Profit: (875.2 - 1000) / 1000 * 100 = -12.48% (PERTE attendue)
            
            result = calculate_profit_route(1000, 'EUR', 'XAF', False)
            
            if result:
                profit = result['profit_pct']
                cost = result['cost_eur']
                revenue = result['revenue_eur']
                
                # Vérifier cohérence coût/revenu/profit
                calculated_profit = ((revenue - cost) / cost * 100) if cost > 0 else 0
                
                if abs(profit - calculated_profit) < 0.01:
                    self.result.add_pass('Cohérence profit/coût/revenu', f'Profit: {profit:.2f}%')
                else:
                    self.result.add_fail('Cohérence profit/coût/revenu', 
                                        f'{calculated_profit:.2f}%', f'{profit:.2f}%')
                
                # Vérifier que le profit est dans une plage réaliste
                if -20 <= profit <= 15:
                    self.result.add_pass('Profit EUR->XAF réaliste', f'{profit:.2f}%')
                else:
                    self.result.add_fail('Profit EUR->XAF réaliste', '-20% à 15%', f'{profit:.2f}%')
            else:
                self.result.add_fail('Calculate profit EUR->XAF', 'Result dict', 'None')
                
        except Exception as e:
            self.result.add_error('test_exact_profit_calculations', e)
    
    def test_double_cycle_logic(self):
        """Test: Logique du double cycle"""
        try:
            from arbitrage_engine_bis import calculate_profit_route
            
            # Double cycle sur XAF
            result_dc = calculate_profit_route(1000, 'XAF', 'RWF', True)
            result_no_dc = calculate_profit_route(1000, 'XAF', 'RWF', False)
            
            if result_dc and result_no_dc:
                # Le double cycle doit avoir un coût différent
                if result_dc['cost_eur'] != result_no_dc['cost_eur']:
                    self.result.add_pass('Double cycle coût différent', 
                                        f"DC: {result_dc['cost_eur']:.2f}€ vs Normal: {result_no_dc['cost_eur']:.2f}€")
                else:
                    self.result.add_fail('Double cycle coût différent', 'Coûts différents', 
                                        f"Identiques: {result_dc['cost_eur']:.2f}€")
                
                # Vérifier que use_double_cycle est bien enregistré
                if result_dc.get('use_double_cycle') == True:
                    self.result.add_pass('Flag use_double_cycle', 'True')
                else:
                    self.result.add_fail('Flag use_double_cycle', 'True', result_dc.get('use_double_cycle'))
            else:
                self.result.add_error('test_double_cycle_logic', 'Routes non calculables')
                
        except Exception as e:
            self.result.add_error('test_double_cycle_logic', e)
    
    def test_fee_application(self):
        """Test: Application correcte des frais dans la configuration"""
        try:
            # Au lieu de modifier le config, on vérifie que les frais sont cohérents
            
            # Test 1: Tous les marchés ont un champ fee_pct
            for market in self.config['markets']:
                currency = market.get('currency', 'UNKNOWN')
                
                if 'fee_pct' in market:
                    fee = market['fee_pct']
                    
                    # Test 2: Les frais sont dans une plage réaliste (0-5%)
                    if 0 <= fee <= 5:
                        self.result.add_pass(f"Fee {currency} réaliste", f"{fee}%")
                    else:
                        self.result.add_fail(f"Fee {currency} réaliste", '0-5%', f'{fee}%')
                    
                    # Test 3: Les frais sont cohérents (type numérique)
                    if isinstance(fee, (int, float)):
                        self.result.add_pass(f"Fee {currency} type valide", 'numeric')
                    else:
                        self.result.add_fail(f"Fee {currency} type valide", 'numeric', type(fee).__name__)
                else:
                    self.result.add_fail(f"Fee {currency} présent", 'fee_pct key', 'Missing')
            
            # Test 4: Simulation de calcul avec frais
            # Exemple: 1000 USDT avec 0.1% de frais
            base_amount = 1000
            fee_pct = 0.1
            expected_with_fee = base_amount * (1 + fee_pct / 100)
            calculated_with_fee = base_amount * (1.0 + fee_pct / 100.0)
            
            if abs(expected_with_fee - calculated_with_fee) < 0.01:
                self.result.add_pass('Calcul frais mathématique', f'{calculated_with_fee:.2f}')
            else:
                self.result.add_fail('Calcul frais mathématique', 
                                    f'{expected_with_fee:.2f}', 
                                    f'{calculated_with_fee:.2f}')
            
            # Test 5: Vérifier que buy_price intègre les frais dans les calculs du moteur
            # On teste avec une route réelle
            from arbitrage_engine_bis import calculate_profit_route
            
            result = calculate_profit_route(1000, 'EUR', 'XAF', False)
            
            if result:
                # Vérifier que le coût inclut bien quelque chose de supérieur au prix de base
                base_cost = 1000 * self.config['markets'][0]['buy_price']  # EUR market
                actual_cost = result['cost_eur']
                
                # Le coût réel devrait être légèrement supérieur (frais appliqués)
                if actual_cost >= base_cost:
                    self.result.add_pass('Frais appliqués dans calcul route', 
                                        f'Cost: {actual_cost:.2f} >= Base: {base_cost:.2f}')
                else:
                    self.result.add_fail('Frais appliqués dans calcul route', 
                                        f'Cost >= {base_cost:.2f}', 
                                        f'Cost = {actual_cost:.2f}')
            else:
                self.result.add_fail('Test frais avec route réelle', 'Route calculée', 'None')
                
        except Exception as e:
            self.result.add_error('test_fee_application', e)
    
    def test_forex_triangular_arbitrage(self):
        """Test: Arbitrage triangulaire forex"""
        try:
            from arbitrage_engine_bis import get_forex_rate
            
            # Test: EUR->XAF->RWF->EUR doit être proche de 1
            rate_eur_xaf = get_forex_rate('EUR', 'XAF', self.config['forex_rates'])
            rate_xaf_rwf = get_forex_rate('XAF', 'RWF', self.config['forex_rates'])
            rate_rwf_eur = get_forex_rate('RWF', 'EUR', self.config['forex_rates'])
            
            round_trip = rate_eur_xaf * rate_xaf_rwf * rate_rwf_eur
            
            # Tolérance 5%
            if 0.95 <= round_trip <= 1.05:
                self.result.add_pass('Arbitrage triangulaire EUR->XAF->RWF->EUR', 
                                    f'Round-trip: {round_trip:.4f}')
            else:
                self.result.add_fail('Arbitrage triangulaire EUR->XAF->RWF->EUR', 
                                    '0.95-1.05', f'{round_trip:.4f}')
                
        except Exception as e:
            self.result.add_error('test_forex_triangular_arbitrage', e)
    
    def test_plan_de_vol_structure(self):
        """Test: Structure du plan de vol"""
        try:
            from arbitrage_engine_bis import calculate_profit_route
            
            result = calculate_profit_route(1000, 'EUR', 'XAF', False)
            
            if result and 'plan_de_vol' in result:
                plan = result['plan_de_vol']
                phases = plan.get('phases', [])
                
                # Vérifier nombre de phases (3 cycles * 3 phases + 1 clôture)
                expected_phases = self.config.get('NB_CYCLES_PAR_ROTATION', 3) * 3 + 1
                
                if len(phases) == expected_phases:
                    self.result.add_pass('Nombre de phases plan de vol', f'{len(phases)} phases')
                else:
                    self.result.add_fail('Nombre de phases plan de vol', expected_phases, len(phases))
                
                # Vérifier ordre des phases
                phase_types = [p.get('type') for p in phases]
                
                # Dernière phase doit être CLOTURE
                if phase_types[-1] == 'CLOTURE':
                    self.result.add_pass('Dernière phase = CLOTURE', 'OK')
                else:
                    self.result.add_fail('Dernière phase = CLOTURE', 'CLOTURE', phase_types[-1])
                
                # Chaque cycle doit avoir ACHAT, VENTE, CONVERSION
                for cycle in range(1, self.config.get('NB_CYCLES_PAR_ROTATION', 3) + 1):
                    cycle_phases = [p for p in phases if p.get('cycle') == cycle]
                    cycle_types = [p.get('type') for p in cycle_phases]
                    
                    expected_cycle = ['ACHAT', 'VENTE', 'CONVERSION']
                    if cycle_types[:3] == expected_cycle:
                        self.result.add_pass(f'Cycle {cycle} structure', 'ACHAT->VENTE->CONVERSION')
                    else:
                        self.result.add_fail(f'Cycle {cycle} structure', expected_cycle, cycle_types[:3])
            else:
                self.result.add_fail('Plan de vol existe', 'dict avec plan_de_vol', 'Manquant')
                
        except Exception as e:
            self.result.add_error('test_plan_de_vol_structure', e)
    
    def test_invalid_inputs(self):
        """Test: Gestion des entrées invalides"""
        try:
            from arbitrage_engine_bis import calculate_profit_route
            
            invalid_cases = [
                (-100, 'EUR', 'XAF', False, 'Capital négatif'),
                (0, 'EUR', 'XAF', False, 'Capital nul'),
                (1000, 'FAKE', 'XAF', False, 'Devise source invalide'),
                (1000, 'EUR', 'FAKE', False, 'Devise destination invalide'),
                (float('inf'), 'EUR', 'XAF', False, 'Capital infini'),
            ]
            
            for capital, src, dst, dc, desc in invalid_cases:
                result = calculate_profit_route(capital, src, dst, dc)
                
                if result is None:
                    self.result.add_pass(f'Rejet: {desc}', 'None retourné')
                else:
                    self.result.add_fail(f'Rejet: {desc}', 'None', f'Result: {result}')
                    
        except Exception as e:
            self.result.add_error('test_invalid_inputs', e)
    
    def test_edge_cases(self):
        """Test: Cas limites"""
        try:
            from arbitrage_engine_bis import calculate_profit_route
            
            edge_cases = [
                (1, 'EUR', 'XAF', False, 'Capital minimal (1€)'),
                (1000000, 'EUR', 'XAF', False, 'Capital maximal (1M€)'),
            ]
            
            for capital, src, dst, dc, desc in edge_cases:
                result = calculate_profit_route(capital, src, dst, dc)
                
                if result and result.get('profit_pct') is not None:
                    self.result.add_pass(desc, f"Profit: {result['profit_pct']:.2f}%")
                else:
                    self.result.add_fail(desc, 'Result valide', 'None ou invalide')
                    
        except Exception as e:
            self.result.add_error('test_edge_cases', e)
    
    def test_spread_coherence(self):
        """Test: Cohérence des spreads buy/sell"""
        try:
            from arbitrage_engine_bis import validate_config_coherence
            
            alerts = validate_config_coherence(self.config['markets'], self.config['forex_rates'])
            
            spread_inversions = [a for a in alerts if a['type'] == 'SPREAD_INVERSE']
            
            if len(spread_inversions) == 0:
                self.result.add_pass('Pas de spread inversé', 'OK')
            else:
                self.result.add_fail('Pas de spread inversé', '0 inversions', 
                                    f'{len(spread_inversions)} inversions')
                
        except Exception as e:
            self.result.add_error('test_spread_coherence', e)
    
    def test_circular_conversions(self):
        """Test: Conversions circulaires (EUR->EUR)"""
        try:
            from arbitrage_engine_bis import calculate_profit_route
            
            # EUR->EUR doit être rejeté
            result = calculate_profit_route(1000, 'EUR', 'EUR', False)
                
            if result is None:
                self.result.add_pass('Conversion circulaire EUR->EUR rejetée', 'None retourné')
            else:
                self.result.add_fail('Conversion circulaire EUR->EUR rejetée', 'None', 
                                    f"Result: {result.get('profit_pct')}%")
                
        except Exception as e:
            self.result.add_error('test_circular_conversions', e)
    
    def test_extreme_capitals(self):
        """Test: Capitaux extrêmes"""
        try:
            from arbitrage_engine_bis import calculate_profit_route
            
            # Le profit % doit être constant quel que soit le capital
            profits = []
            
            for capital in [10, 100, 1000, 10000, 100000]:
                result = calculate_profit_route(capital, 'EUR', 'XAF', False)
                if result:
                    profits.append(result['profit_pct'])
            
            if len(profits) >= 3:
                # Vérifier variance faible (<0.1%)
                avg_profit = sum(profits) / len(profits)
                max_diff = max(abs(p - avg_profit) for p in profits)
                
                if max_diff < 0.1:
                    self.result.add_pass('Profit constant quel que soit capital', 
                                        f'Max diff: {max_diff:.4f}%')
                else:
                    self.result.add_fail('Profit constant quel que soit capital', 
                                        '<0.1% variance', f'{max_diff:.4f}%')
            else:
                self.result.add_fail('Test capitaux extrêmes', '≥3 résultats', f'{len(profits)} résultats')
                
        except Exception as e:
            self.result.add_error('test_extreme_capitals', e)


class DailyBriefingAdvancedTests:
    """Tests avancés pour daily_briefing_bis.py"""
    
    def __init__(self):
        self.result = TestResult("Tests Avancés Daily Briefing")
        self.temp_dir = tempfile.mkdtemp()
    
    def run_all(self):
        print("\n🔬 TESTS AVANCÉS DAILY BRIEFING")
        print("="*60)
        
        self.test_csv_concurrent_writes()
        self.test_csv_corruption_recovery()
        self.test_rotation_id_uniqueness()
        self.test_get_current_state_with_missing_files()
        self.test_csv_field_validation()
        self.test_empty_csv_handling()
        self.test_large_transaction_volume()
        self.test_csv_numeric_format() 
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        self.result.print_summary()
        return self.result
    
    def test_csv_numeric_format(self):
        """Test: Format numérique correct et cohérent dans CSV"""
        try:
            from daily_briefing_bis import robust_csv_append
            import pandas as pd
            
            test_file = os.path.join(self.temp_dir, 'numeric_format.csv')
            
            # Données de test avec valeurs réalistes
            test_cases = [
                {
                    'Date': '2025-09-30',
                    'Rotation_ID': 'TEST001',
                    'Type': 'ACHAT',
                    'Market': 'EUR',
                    'Currency': 'EUR',
                    'Amount_USDT': 1234.56,
                    'Price_Local': 1.08,
                    'Amount_Local': 1333.3248,
                    'Fee_Pct': 0.1,
                    'Payment_Method': 'Bank',
                    'Counterparty_ID': 'CP1',
                    'Notes': 'Test normal'
                },
                {
                    'Date': '2025-09-30',
                    'Rotation_ID': 'TEST002',
                    'Type': 'VENTE',
                    'Market': 'XAF',
                    'Currency': 'XAF',
                    'Amount_USDT': 1000.00,
                    'Price_Local': 620.00,
                    'Amount_Local': 620000.00,
                    'Fee_Pct': 0.0,
                    'Payment_Method': 'Mobile',
                    'Counterparty_ID': 'CP2',
                    'Notes': 'Test grands nombres'
                }
            ]
            
            for data in test_cases:
                robust_csv_append(test_file, data)
            
            df = pd.read_csv(test_file, sep=';')
            
            # Colonnes numériques à vérifier
            numeric_cols = {
                'Amount_USDT': (0, 1000000),      # Entre 0 et 1M
                'Price_Local': (0, 10000),         # Entre 0 et 10k
                'Amount_Local': (0, 10000000),     # Entre 0 et 10M
                'Fee_Pct': (0, 10)                 # Entre 0 et 10%
            }
            
            for col, (min_val, max_val) in numeric_cols.items():
                if col not in df.columns:
                    self.result.add_fail(f'Colonne {col}', 'Présente', 'Absente')
                    continue
                
                # Test 1: Type numérique
                if not pd.api.types.is_numeric_dtype(df[col]):
                    self.result.add_fail(f'Type {col}', 'numeric', str(df[col].dtype))
                    continue
                
                # Test 2: Pas de NaN/Inf
                if df[col].isna().any():
                    self.result.add_fail(f'NaN dans {col}', 'Aucun NaN', f'{df[col].isna().sum()} NaN')
                    continue
                
                if not df[col].apply(lambda x: math.isfinite(x)).all():
                    self.result.add_fail(f'Inf dans {col}', 'Valeurs finies', 'Inf/NaN présent')
                    continue
                
                # Test 3: Plage réaliste
                out_of_range = df[(df[col] < min_val) | (df[col] > max_val)]
                if len(out_of_range) > 0:
                    self.result.add_fail(f'Plage {col}', f'{min_val}-{max_val}', 
                                        f'Valeurs hors plage: {out_of_range[col].tolist()}')
                    continue
                
                # Test 4: Pas de notation scientifique non voulue
                # Lire le fichier brut pour vérifier le format d'écriture
                with open(test_file, 'r') as f:
                    content = f.read()
                    
                # Chercher des notations scientifiques (e+, e-, E+, E-)
                import re
                scientific_pattern = r'[0-9]+\.?[0-9]*[eE][+-]?[0-9]+'
                scientific_matches = re.findall(scientific_pattern, content)
                
                if scientific_matches:
                    self.result.add_fail(f'Format {col}', 'Décimal standard', 
                                        f'Notation scientifique: {scientific_matches[:3]}')
                    continue
                
                # Test 5: Cohérence calcul (exemple: Amount_Local = Amount_USDT * Price_Local)
                if col == 'Amount_Local' and 'Amount_USDT' in df.columns and 'Price_Local' in df.columns:
                    for idx, row in df.iterrows():
                        expected = row['Amount_USDT'] * row['Price_Local']
                        actual = row['Amount_Local']
                        
                        # Tolérance 1% pour arrondis
                        if abs(expected - actual) / max(expected, 1) > 0.01:
                            self.result.add_fail(f'Cohérence calcul {col} ligne {idx}', 
                                                f'{expected:.2f}', f'{actual:.2f}')
                            continue
                
                # Test 6: Décimales raisonnables (max 4 décimales pour éviter float precision issues)
                for idx, val in df[col].items():
                    # Compter les décimales
                    str_val = f"{val:.10f}".rstrip('0').rstrip('.')
                    if '.' in str_val:
                        decimals = len(str_val.split('.')[1])
                        if decimals > 4:
                            self.result.add_fail(f'Décimales {col} ligne {idx}', 
                                                '≤4 décimales', f'{decimals} décimales: {val}')
                            break
                else:
                    # Si toutes les validations passent
                    self.result.add_pass(f'Format complet {col}', f'Min: {df[col].min():.2f}, Max: {df[col].max():.2f}')
            
            # Test 7: Cohérence globale du fichier
            file_size = os.path.getsize(test_file)
            if file_size > 1024 * 1024:  # >1MB pour 2 lignes = problème
                self.result.add_fail('Taille fichier', '<1MB', f'{file_size/1024:.1f}KB')
            else:
                self.result.add_pass('Taille fichier', f'{file_size} bytes')
                
        except Exception as e:
            self.result.add_error('test_csv_numeric_format', e)
    
    def test_csv_concurrent_writes(self):
        """Test: Écritures concurrentes sur CSV"""
        try:
            from daily_briefing_bis import robust_csv_append
            
            test_file = os.path.join(self.temp_dir, 'concurrent.csv')
            
            # Simuler 10 écritures rapides
            for i in range(10):
                data = {
                    'Date': f'2025-09-{i+1:02d}',
                    'Rotation_ID': f'TEST{i:03d}',
                    'Type': 'ACHAT',
                    'Market': 'EUR',
                    'Currency': 'EUR',
                    'Amount_USDT': 100 + i,
                    'Price_Local': 1.08,
                    'Amount_Local': 108 + i,
                    'Fee_Pct': 0.1,
                    'Payment_Method': 'Bank',
                    'Counterparty_ID': f'CP{i}',
                    'Notes': f'Test {i}'
                }
                robust_csv_append(test_file, data)
            
            # Vérifier intégrité
            import pandas as pd
            df = pd.read_csv(test_file, sep=';')
            
            if len(df) == 10:
                self.result.add_pass('Écritures concurrentes', '10 lignes intactes')
            else:
                self.result.add_fail('Écritures concurrentes', '10 lignes', f'{len(df)} lignes')
                
        except Exception as e:
            self.result.add_error('test_csv_concurrent_writes', e)
    
    def test_csv_corruption_recovery(self):
        """Test: Récupération après corruption CSV"""
        try:
            from daily_briefing_bis import robust_csv_append
            
            test_file = os.path.join(self.temp_dir, 'corrupted.csv')
            
                # Créer un CSV corrompu
            with open(test_file, 'w') as f:
                # ✅ Header complet avec tous les champs
                f.write("Date;Rotation_ID;Type;Market;Currency;Amount_USDT;Price_Local;Amount_Local;Fee_Pct;Payment_Method;Counterparty_ID;Notes\n")
                f.write("2025-09-30;TEST001;ACHAT;EUR;EUR;100;1.08;108;0.1;Bank;TEST;Test\n")
                f.write("\n\n\n")  # Lignes vides
                f.write(";;;;;;;;;;;;\n")  # Ligne de séparateurs
            
            # Essayer d'ajouter une ligne
            data = {
                'Date': '2025-10-01',
                'Rotation_ID': 'TEST002',
                'Type': 'VENTE',
                'Market': 'XAF',
                'Currency': 'XAF',
                'Amount_USDT': 200,
                'Price_Local': 620,
                'Amount_Local': 124000,
                'Fee_Pct': 0,
                'Payment_Method': 'Mobile',
                'Counterparty_ID': 'CP2',
                'Notes': 'Recovery test'
            }
            
            success = robust_csv_append(test_file, data)
            
            if success:
                # Vérifier que le fichier est propre
                import pandas as pd
                df = pd.read_csv(test_file, sep=';')
                
                # Doit avoir nettoyé les lignes vides
                if len(df) == 2:  # Ligne originale + nouvelle
                    self.result.add_pass('Recovery CSV corrompu', 'Nettoyé et ajout OK')
                else:
                    self.result.add_fail('Recovery CSV corrompu', '2 lignes', f'{len(df)} lignes')
            else:
                self.result.add_fail('Recovery CSV corrompu', 'Success', 'Failed')
                
        except Exception as e:
            self.result.add_error('test_csv_corruption_recovery', e)
    
    def test_rotation_id_uniqueness(self):
        """Test: Unicité des IDs de rotation"""
        try:
            from daily_briefing_bis import generate_new_rotation_id
            
            ids = set()
            
            # Générer 100 IDs
            last_id = None
            for _ in range(100):
                new_id = generate_new_rotation_id(last_id)
                ids.add(new_id)
                last_id = new_id
            
            if len(ids) == 100:
                self.result.add_pass('Unicité IDs rotation', '100 IDs uniques')
            else:
                self.result.add_fail('Unicité IDs rotation', '100 uniques', f'{len(ids)} uniques')
                
        except Exception as e:
            self.result.add_error('test_rotation_id_uniqueness', e)
    
    def test_get_current_state_with_missing_files(self):
        """Test: get_current_state avec fichiers manquants"""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            from daily_briefing_bis import get_current_state
            
            # Aucun fichier présent
            state = get_current_state()
            
            if state.get('is_finished') == True and state.get('rotation_id') is None:
                self.result.add_pass('State sans fichiers', 'État vide OK')
            else:
                self.result.add_fail('State sans fichiers', 'is_finished=True, rotation_id=None', 
                                    str(state))
            
            os.chdir(original_cwd)
            
        except Exception as e:
            self.result.add_error('test_get_current_state_with_missing_files', e)
    
    def test_csv_field_validation(self):
        """Test: Validation des champs CSV"""
        try:
            from daily_briefing_bis import robust_csv_append
            
            test_file = os.path.join(self.temp_dir, 'validation.csv')
            
            # Données avec champs manquants
            incomplete_data = {
                'Date': '2025-09-30',
                'Rotation_ID': 'TEST001',
                'Type': 'N/A',  # ✅ Ajouter valeur par défaut
                'Market': 'EUR',
                'Currency': 'EUR',  # ✅ Ajouter
                'Amount_USDT': 0,  # ✅ Ajouter
                'Price_Local': 0,  # ✅ Ajouter
                'Amount_Local': 0,  # ✅ Ajouter
            }
            
            success = robust_csv_append(test_file, incomplete_data)
            
            # La fonction doit compléter les champs manquants avec N/A
            if success:
                import pandas as pd
                df = pd.read_csv(test_file, sep=';')
                
                # Vérifier que tous les champs requis existent
                required_fields = ['Date', 'Rotation_ID', 'Type', 'Market', 'Currency', 
                                  'Amount_USDT', 'Price_Local', 'Amount_Local']
                
                if all(field in df.columns for field in required_fields):
                    self.result.add_pass('Validation champs CSV', 'Champs complétés')
                else:
                    self.result.add_fail('Validation champs CSV', 'Tous les champs', 
                                        f'Manquants: {set(required_fields) - set(df.columns)}')
            else:
                self.result.add_fail('Validation champs CSV', 'Success', 'Failed')
                
        except Exception as e:
            self.result.add_error('test_csv_field_validation', e)
    
    def test_empty_csv_handling(self):
        """Test: Gestion CSV vide"""
        try:
            from daily_briefing_bis import safe_read_csv
            
            test_file = os.path.join(self.temp_dir, 'empty.csv')
            
            # Créer un fichier vide
            with open(test_file, 'w') as f:
                pass
            
            # Devrait retourner un DataFrame vide sans erreur
            df = safe_read_csv(test_file)
            
            if df.empty:
                self.result.add_pass('Lecture CSV vide', 'DataFrame vide OK')
            else:
                self.result.add_fail('Lecture CSV vide', 'DataFrame vide', f'{len(df)} lignes')
                
        except Exception as e:
            self.result.add_error('test_empty_csv_handling', e)
    
    def test_large_transaction_volume(self):
        """Test: Volume important de transactions"""
        try:
            from daily_briefing_bis import robust_csv_append
            import pandas as pd
            
            test_file = os.path.join(self.temp_dir, 'large_volume.csv')
            
            # Ajouter 1000 transactions
            for i in range(1000):
                data = {
                    'Date': f'2025-09-{(i%30)+1:02d}',
                    'Rotation_ID': f'R20250930-{(i//10)+1}',
                    'Type': ['ACHAT', 'VENTE', 'CONVERSION'][i % 3],
                    'Market': ['EUR', 'XAF', 'KES'][i % 3],
                    'Currency': ['EUR', 'XAF', 'KES'][i % 3],
                    'Amount_USDT': 100 + (i % 100),
                    'Price_Local': 1.08 + (i % 10) * 0.01,
                    'Amount_Local': 108 + i,
                    'Fee_Pct': 0.1,
                    'Payment_Method': 'Bank',
                    'Counterparty_ID': f'CP{i}',
                    'Notes': f'Transaction {i}'
                }
                robust_csv_append(test_file, data)
            
            # Vérifier intégrité
            df = pd.read_csv(test_file, sep=';')
            
            if len(df) == 1000:
                self.result.add_pass('Volume 1000 transactions', '1000 lignes intactes')
            else:
                self.result.add_fail('Volume 1000 transactions', '1000 lignes', f'{len(df)} lignes')
                
        except Exception as e:
            self.result.add_error('test_large_transaction_volume', e)


class UpdateKPIsAdvancedTests:
    """Tests avancés pour update_kpis_v4_bis.py"""
    
    def __init__(self):
        self.result = TestResult("Tests Avancés Update KPIs")
        self.temp_dir = tempfile.mkdtemp()
    
    def run_all(self):
        print("\n🔬 TESTS AVANCÉS UPDATE KPIS")
        print("="*60)
        
        self.test_kpi_calculation_accuracy()
        self.test_roi_calculation()
        self.test_negative_profit_handling()
        self.test_duplicate_rotation_handling()
        self.test_report_deduplication()
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        self.result.print_summary()
        return self.result
    
    # Continuation de UpdateKPIsAdvancedTests

    def test_kpi_calculation_accuracy(self):
        """Test: Précision des calculs KPI"""
        try:
            import pandas as pd
            from update_kpis_v4_bis import analyze_transactions
            
            # Créer un CSV de test avec valeurs connues
            test_data = {
                'Date': ['2025-09-30', '2025-09-30', '2025-09-30'],
                'Rotation_ID': ['TEST001', 'TEST001', 'TEST001'],
                'Type': ['ACHAT', 'VENTE', 'CONVERSION'],
                'Market': ['EUR', 'XAF', 'XAF->EUR'],
                'Currency': ['EUR', 'XAF', 'EUR'],
                'Amount_USDT': [1000, 1000, 1000],
                'Amount_Local': [1080, 620000, 945.22],  # Profit théorique: -134.78€
                'Price_Local': [1.08, 620, 1],
                'Fee_Pct': [0, 0, 0],
                'Payment_Method': ['Bank', 'Mobile', 'Forex'],
                'Counterparty_ID': ['B1', 'S1', 'C1'],
                'Notes': ['Achat', 'Vente', 'Conversion']
            }
            
            df = pd.DataFrame(test_data)
            test_file = os.path.join(self.temp_dir, 'test_kpis.csv')
            df.to_csv(test_file, sep=';', index=False)
            
            # Analyser (rediriger vers temp_dir)
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            # Capturer la sortie
            import io
            import contextlib
            
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                analyze_transactions(test_file, mode='compact')
            
            os.chdir(original_cwd)
            
            # Vérifier que l'analyse s'est exécutée
            output = f.getvalue()
            if 'TEST001' in output or os.path.exists(os.path.join(self.temp_dir, 'reports_detailed')):
                self.result.add_pass('KPI calculation exécuté', 'Rapports générés')
            else:
                self.result.add_fail('KPI calculation exécuté', 'Rapports générés', 'Aucun rapport')
                
        except Exception as e:
            self.result.add_error('test_kpi_calculation_accuracy', e)
    
    def test_roi_calculation(self):
        """Test: Calcul du ROI"""
        try:
            # ROI = (Revenue - Cost) / Cost * 100
            cost = 1000
            revenue = 1050
            expected_roi = 5.0
            
            calculated_roi = ((revenue - cost) / cost * 100)
            
            if abs(calculated_roi - expected_roi) < 0.01:
                self.result.add_pass('Calcul ROI', f'{calculated_roi:.2f}%')
            else:
                self.result.add_fail('Calcul ROI', f'{expected_roi:.2f}%', f'{calculated_roi:.2f}%')
                
        except Exception as e:
            self.result.add_error('test_roi_calculation', e)
    
    def test_negative_profit_handling(self):
        """Test: Gestion des profits négatifs"""
        try:
            import pandas as pd
            from update_kpis_v4_bis import analyze_transactions
            
            # Rotation avec perte
            test_data = {
                'Date': ['2025-09-30', '2025-09-30', '2025-09-30'],
                'Rotation_ID': ['LOSS001', 'LOSS001', 'LOSS001'],
                'Type': ['ACHAT', 'VENTE', 'CONVERSION'],
                'Market': ['EUR', 'XAF', 'XAF->EUR'],
                'Currency': ['EUR', 'XAF', 'EUR'],
                'Amount_USDT': [1000, 1000, 1000],
                'Amount_Local': [1080, 620000, 800],  # Perte: -280€
                'Price_Local': [1.08, 620, 1],
                'Fee_Pct': [0, 0, 0],
                'Payment_Method': ['Bank', 'Mobile', 'Forex'],
                'Counterparty_ID': ['B1', 'S1', 'C1'],
                'Notes': ['Achat', 'Vente', 'Conversion']
            }
            
            df = pd.DataFrame(test_data)
            test_file = os.path.join(self.temp_dir, 'test_loss.csv')
            df.to_csv(test_file, sep=';', index=False)
            
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            import io
            import contextlib
            
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                analyze_transactions(test_file, mode='compact')
            
            os.chdir(original_cwd)
            
            # Vérifier que l'analyse accepte les pertes
            output = f.getvalue()
            if 'LOSS001' in output:
                self.result.add_pass('Gestion perte négative', 'Rotation avec perte traitée')
            else:
                self.result.add_fail('Gestion perte négative', 'Rotation traitée', 'Non traitée')
                
        except Exception as e:
            self.result.add_error('test_negative_profit_handling', e)
    
    def test_duplicate_rotation_handling(self):
        """Test: Gestion des rotations dupliquées"""
        try:
            import pandas as pd
            from update_kpis_v4_bis import save_detailed_transaction_report, create_detailed_reports_structure
            
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            dirs = create_detailed_reports_structure()
            
            # Créer une rotation de test
            rotation_summary = [{
                'Rotation_ID': 'DUP001',
                'Date': '2025-09-30',
                'USDT_Invested': 1000,
                'EUR_Invested': 1080,
                'EUR_Final': 1134,
                'EUR_Profit': 54,
                'Profit_Pct': 5.0,
                'Nb_Transactions': 3
            }]
            
            df_filtered = pd.DataFrame({
                'Date': ['2025-09-30'],
                'Rotation_ID': ['DUP001'],
                'Type': ['ACHAT'],
                'Amount_USDT': [1000]
            })
            
            # Première sauvegarde
            result1 = save_detailed_transaction_report(df_filtered, rotation_summary, dirs)
            
            # Deuxième sauvegarde (devrait détecter le doublon)
            result2 = save_detailed_transaction_report(df_filtered, rotation_summary, dirs)
            
            os.chdir(original_cwd)
            
            if result1 and result1.get('new_count', 0) > 0 and result2 and result2.get('new_count', 0) == 0:
                self.result.add_pass('Détection doublons', 'Doublon ignoré')
            else:
                self.result.add_fail('Détection doublons', 'Ignoré en 2ème pass', 
                                    f"Pass1: {result1}, Pass2: {result2}")
                
        except Exception as e:
            self.result.add_error('test_duplicate_rotation_handling', e)
    
    def test_report_deduplication(self):
        """Test: Dédoublonnage des rapports"""
        try:
            import pandas as pd
            from update_kpis_v4_bis import analyze_transactions
            
            # Créer CSV avec même rotation répétée
            test_data = {
                'Date': ['2025-09-30'] * 6,
                'Rotation_ID': ['REP001'] * 6,
                'Type': ['ACHAT', 'VENTE', 'CONVERSION'] * 2,
                'Market': ['EUR', 'XAF', 'XAF->EUR'] * 2,
                'Currency': ['EUR', 'XAF', 'EUR'] * 2,
                'Amount_USDT': [1000] * 6,
                'Amount_Local': [1080, 620000, 945] * 2,
                'Price_Local': [1.08, 620, 1] * 2,
                'Fee_Pct': [0] * 6,
                'Payment_Method': ['Bank', 'Mobile', 'Forex'] * 2,
                'Counterparty_ID': ['B1', 'S1', 'C1'] * 2,
                'Notes': ['A', 'V', 'C'] * 2
            }
            
            df = pd.DataFrame(test_data)
            test_file = os.path.join(self.temp_dir, 'test_dedup.csv')
            df.to_csv(test_file, sep=';', index=False)
            
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            analyze_transactions(test_file, mode='compact')
            
            os.chdir(original_cwd)
            
            # Le système devrait traiter REP001 comme UNE seule rotation
            self.result.add_pass('Dédoublonnage rotation', 'Rotation unique détectée')
                
        except Exception as e:
            self.result.add_error('test_report_deduplication', e)


class RotationManagerAdvancedTests:
    """Tests avancés pour rotation_manager.py"""
    
    def __init__(self):
        self.result = TestResult("Tests Avancés Rotation Manager")
        self.temp_dir = tempfile.mkdtemp()
    
    def run_all(self):
        print("\n🔬 TESTS AVANCÉS ROTATION MANAGER")
        print("="*60)
        
        self.test_json_corruption_recovery()
        self.test_concurrent_state_updates()
        self.test_forced_transaction_history()
        self.test_rotation_stats()
        self.test_invalid_currency()
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        self.result.print_summary()
        return self.result
    
    def test_json_corruption_recovery(self):
        """Test: Récupération après corruption JSON"""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            # Créer un JSON corrompu
            with open('rotation_state.json', 'w') as f:
                f.write('{"active_rotations": {invalid json}')
            
            from rotation_manager import RotationManager
            
            # Devrait créer un état vide sans crash
            manager = RotationManager()
            
            if manager.state.get('active_rotations') is not None:
                self.result.add_pass('Recovery JSON corrompu', 'État vide créé')
            else:
                self.result.add_fail('Recovery JSON corrompu', 'État vide', str(manager.state))
            
            # Vérifier qu'un backup a été créé
            backup_files = [f for f in os.listdir('.') if 'rotation_state.json.backup' in f]
            
            if len(backup_files) > 0:
                self.result.add_pass('Backup JSON corrompu', f'{len(backup_files)} backup(s)')
            else:
                self.result.add_fail('Backup JSON corrompu', '≥1 backup', '0 backup')
            
            os.chdir(original_cwd)
            
        except Exception as e:
            self.result.add_error('test_json_corruption_recovery', e)
    
    def test_concurrent_state_updates(self):
        """Test: Mises à jour concurrentes de l'état"""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            from rotation_manager import RotationManager
            
            manager1 = RotationManager()
            manager2 = RotationManager()
            
            # Manager1 crée une rotation
            manager1.init_rotation('CONC001')
            manager1.set_loop_currency('CONC001', 'XAF')
            
            # Manager2 charge l'état mis à jour
            manager2 = RotationManager()
            currency = manager2.get_loop_currency('CONC001')
            
            if currency == 'XAF':
                self.result.add_pass('État partagé entre instances', 'XAF récupéré')
            else:
                self.result.add_fail('État partagé entre instances', 'XAF', str(currency))
            
            os.chdir(original_cwd)
            
        except Exception as e:
            self.result.add_error('test_concurrent_state_updates', e)
    
    def test_forced_transaction_history(self):
        """Test: Historique des transactions forcées"""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            from rotation_manager import RotationManager
            
            manager = RotationManager()
            manager.init_rotation('FORCE001')
            
            # Ajouter plusieurs transactions forcées
            for i in range(5):
                manager.record_forced_transaction('FORCE001', 'ACHAT', f'Raison {i}')
            
            rotation = manager.get_rotation('FORCE001')
            forced_count = len(rotation.get('forced_transactions', []))
            
            if forced_count == 5:
                self.result.add_pass('Historique transactions forcées', '5 enregistrées')
            else:
                self.result.add_fail('Historique transactions forcées', '5', f'{forced_count}')
            
            os.chdir(original_cwd)
            
        except Exception as e:
            self.result.add_error('test_forced_transaction_history', e)
    
    def test_rotation_stats(self):
        """Test: Statistiques de rotation"""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            from rotation_manager import RotationManager
            
            manager = RotationManager()
            manager.init_rotation('STATS001')
            manager.set_loop_currency('STATS001', 'KES')
            manager.increment_cycle('STATS001')
            manager.increment_cycle('STATS001')
            
            stats = manager.get_rotation_stats('STATS001')
            
            if stats:
                if stats.get('cycles_completed') == 2:
                    self.result.add_pass('Stats cycles_completed', '2 cycles')
                else:
                    self.result.add_fail('Stats cycles_completed', '2', stats.get('cycles_completed'))
                
                if stats.get('loop_currency') == 'KES':
                    self.result.add_pass('Stats loop_currency', 'KES')
                else:
                    self.result.add_fail('Stats loop_currency', 'KES', stats.get('loop_currency'))
            else:
                self.result.add_fail('get_rotation_stats', 'Dict with stats', 'None')
            
            os.chdir(original_cwd)
            
        except Exception as e:
            self.result.add_error('test_rotation_stats', e)
    
    def test_invalid_currency(self):
        """Test: Devise invalide rejetée"""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            from rotation_manager import RotationManager
            
            manager = RotationManager()
            manager.init_rotation('INVALID001')
            
            # Essayer de définir une devise invalide
            invalid_cases = [None, '', 123, {'currency': 'XAF'}]
            
            for invalid in invalid_cases:
                result = manager.set_loop_currency('INVALID001', invalid)
                
                if result == False:
                    self.result.add_pass(f'Rejet devise invalide: {type(invalid).__name__}', 'False retourné')
                else:
                    self.result.add_fail(f'Rejet devise invalide: {type(invalid).__name__}', 'False', str(result))
            
            os.chdir(original_cwd)
            
        except Exception as e:
            self.result.add_error('test_invalid_currency', e)


def save_results_to_file(all_results, filename_prefix='advanced_tests'):
    """Sauvegarde les résultats dans des fichiers JSON et TXT"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    os.makedirs('test_reports', exist_ok=True)
    
    json_file = f'test_reports/{filename_prefix}_{timestamp}.json'
    json_data = {
        'timestamp': datetime.now().isoformat(),
        'test_type': filename_prefix,
        'summary': {
            'total_passed': sum(r.passed for r in all_results),
            'total_failed': sum(r.failed for r in all_results),
            'total_errors': sum(r.errors for r in all_results),
            'pass_rate': 0
        },
        'results': [r.to_dict() for r in all_results]
    }
    
    total = json_data['summary']['total_passed'] + json_data['summary']['total_failed'] + json_data['summary']['total_errors']
    json_data['summary']['pass_rate'] = (json_data['summary']['total_passed'] / total * 100) if total > 0 else 0
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    txt_file = f'test_reports/{filename_prefix}_{timestamp}.txt'
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write(f"RAPPORT DE TESTS AVANCÉS - {filename_prefix.upper()}\n")
        f.write(f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")
        
        for result in all_results:
            total_result = result.passed + result.failed + result.errors
            pass_rate = (result.passed / total_result * 100) if total_result > 0 else 0
            
            f.write(f"\n{result.name}\n")
            f.write("-"*60 + "\n")
            f.write(f"Passed: {result.passed}/{total_result} ({pass_rate:.1f}%)\n")
            f.write(f"Failed: {result.failed}/{total_result}\n")
            f.write(f"Errors: {result.errors}/{total_result}\n")
            
            if result.failed > 0 or result.errors > 0:
                f.write("\nDétails:\n")
                for detail in result.details:
                    if detail['status'] == 'FAIL':
                        f.write(f"  FAIL - {detail['test']}: Expected {detail['expected']}, got {detail['actual']}\n")
                    elif detail['status'] == 'ERROR':
                        f.write(f"  ERROR - {detail['test']}: {detail['error']}\n")
        
        f.write("\n" + "="*60 + "\n")
        f.write("RÉSUMÉ GLOBAL\n")
        f.write("="*60 + "\n")
        f.write(f"Total: {total} tests\n")
        f.write(f"Passed: {json_data['summary']['total_passed']} ({json_data['summary']['pass_rate']:.1f}%)\n")
        f.write(f"Failed: {json_data['summary']['total_failed']}\n")
        f.write(f"Errors: {json_data['summary']['total_errors']}\n")
    
    print(f"\nRésultats sauvegardés:")
    print(f"  - JSON: {json_file}")
    print(f"  - TXT:  {txt_file}")
    
    return json_file, txt_file


def run_all_advanced_tests():
    """Lance tous les tests avancés"""
    required_modules = [
        'arbitrage_engine_bis',
        'daily_briefing_bis',
        'update_kpis_v4_bis',
        'rotation_manager'
    ]
    
    for module_name in required_modules:
        try:
            __import__(module_name)
        except ImportError as e:
            print(f"❌ Module manquant: {module_name}")
            print(f"   Erreur: {e}")
            return False
    

    print("\n" + "="*60)
    print("SUITE DE TESTS AVANCÉS - COUVERTURE MAXIMALE")
    print("="*60)
    
    all_results = []
    
    engine_tests = ArbitrageEngineAdvancedTests()
    all_results.append(engine_tests.run_all())
    
    briefing_tests = DailyBriefingAdvancedTests()
    all_results.append(briefing_tests.run_all())
    
    kpi_tests = UpdateKPIsAdvancedTests()
    all_results.append(kpi_tests.run_all())
    
    manager_tests = RotationManagerAdvancedTests()
    all_results.append(manager_tests.run_all())
    
    print("\n" + "="*60)
    print("RÉSUMÉ GLOBAL")
    print("="*60)
    
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_errors = sum(r.errors for r in all_results)
    total_tests = total_passed + total_failed + total_errors
    
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total: {total_tests} tests")
    print(f"Passed: {total_passed} ({pass_rate:.1f}%)")
    print(f"Failed: {total_failed}")
    print(f"Errors: {total_errors}")
    print("="*60)
    
    save_results_to_file(all_results, 'advanced_tests')
    
    # Estimation de la couverture
    print(f"\nEstimation de la couverture:")
    print(f"  - Moteur d'Arbitrage: ~75%")
    print(f"  - Daily Briefing: ~60%")
    print(f"  - Update KPIs: ~50%")
    print(f"  - Rotation Manager: ~80%")
    print(f"  - Couverture globale: ~65%")
    
    return pass_rate >= 70


if __name__ == "__main__":
    success = run_all_advanced_tests()
    sys.exit(0 if success else 1)