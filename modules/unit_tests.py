# modules/unit_tests.py

import sys
import os
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

# CORRECTION CRITIQUE : Changer le répertoire de travail AVANT tout import


# Obtenir le chemin du fichier unit_tests.py lui-même
current_file = os.path.abspath(__file__)  # C:\...\Projet Arbitrage\modules\unit_tests.py
modules_dir = os.path.dirname(current_file)  # C:\...\Projet Arbitrage\modules
project_root = os.path.dirname(modules_dir)  # C:\...\Projet Arbitrage

os.chdir(project_root)
sys.path.insert(0, project_root)
print(f"[INFO] Working directory: {os.getcwd()}\n")
print(f"[INFO] Config exists: {os.path.exists('config.json')}\n")

class TestResult:
    def __init__(self, name):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.details = []
    
    def add_pass(self, test_name, message=""):
        self.passed += 1
        self.details.append({
            'test': test_name,
            'status': 'PASS',
            'message': message
        })
    
    def add_fail(self, test_name, expected, actual):
        self.failed += 1
        self.details.append({
            'test': test_name,
            'status': 'FAIL',
            'expected': expected,
            'actual': actual
        })
    
    def add_error(self, test_name, error):
        self.errors += 1
        self.details.append({
            'test': test_name,
            'status': 'ERROR',
            'error': str(error)
        })
    
    def print_summary(self):
        total = self.passed + self.failed + self.errors
        print(f"\n{'='*60}")
        print(f"📊 {self.name}")
        print(f"{'='*60}")
        print(f"✅ Passed: {self.passed}/{total}")
        print(f"❌ Failed: {self.failed}/{total}")
        print(f"💥 Errors: {self.errors}/{total}")
        
        if self.failed > 0 or self.errors > 0:
            print(f"\n🔍 Détails des échecs:")
            for detail in self.details:
                if detail['status'] in ['FAIL', 'ERROR']:
                    print(f"  - {detail['test']}: {detail.get('error', detail.get('actual', ''))}")
    
    def to_dict(self):
        """Convertit le résultat en dictionnaire pour JSON"""
        return {
            'name': self.name,
            'passed': self.passed,
            'failed': self.failed,
            'errors': self.errors,
            'total': self.passed + self.failed + self.errors,
            'pass_rate': (self.passed / (self.passed + self.failed + self.errors) * 100) if (self.passed + self.failed + self.errors) > 0 else 0,
            'details': self.details
        }


class ArbitrageEngineTests:
    """Tests unitaires pour arbitrage_engine_bis.py"""
    
    def __init__(self):
        self.result = TestResult("Tests Moteur d'Arbitrage")
    
    def run_all(self):
        print("\n🔬 TESTS DU MOTEUR D'ARBITRAGE")
        print("="*60)
        
        self.test_find_best_routes()
        self.test_calculate_profit_route()
        self.test_forex_conversions()
        self.test_validation_coherence()
        self.test_margin_ranges()
        
        self.result.print_summary()
        return self.result
    
    def test_find_best_routes(self):
        """Test: find_best_routes() retourne des routes valides"""
        try:
            from arbitrage_engine_bis import find_best_routes
            
            routes = find_best_routes(top_n=5)
            
            if len(routes) >= 3:
                self.result.add_pass('find_best_routes - count', f'{len(routes)} routes')
            else:
                self.result.add_fail('find_best_routes - count', '≥3', len(routes))
            
            for route in routes:
                profit = route.get('profit_pct', 0)
                if -10 <= profit <= 20:
                    self.result.add_pass(f"Marge {route['detailed_route']}", f"{profit:.2f}%")
                else:
                    self.result.add_fail(f"Marge {route['detailed_route']}", "-10% à 20%", f"{profit:.2f}%")
            
        except Exception as e:
            self.result.add_error('find_best_routes', e)
    
    def test_calculate_profit_route(self):
        try:
            from arbitrage_engine_bis import calculate_profit_route
            
            test_cases = [
                (1000, 'EUR', 'XAF', False, 'EUR->XAF direct'),
                (1000, 'KES', 'XAF', False, 'KES->XAF direct'),
            ]
            
            for initial, src, dst, dc, desc in test_cases:
                result = calculate_profit_route(initial, src, dst, dc)
                
                if result:
                    profit = result.get('profit_pct', 0)
                    
                    if -10 <= profit <= 20:
                        self.result.add_pass(desc, f"Profit: {profit:.2f}%")
                    else:
                        self.result.add_fail(desc, "-10% à 20%", f"{profit:.2f}%")
                else:
                    self.result.add_fail(desc, "Route valide", "None")
                    
        except Exception as e:
            self.result.add_error('calculate_profit_route', e)
    
    def test_forex_conversions(self):
        try:
            from arbitrage_engine_bis import get_forex_rate
            
            with open('config.json', 'r') as f:
                config = json.load(f)
                forex_rates = config['forex_rates']
            
            test_pairs = [
                ('XAF', 'EUR', 655.957),
                ('EUR', 'XAF', 655.957),
                ('RWF', 'EUR', 1700.0),
            ]
            
            for from_curr, to_curr, base_rate in test_pairs:
                rate = get_forex_rate(from_curr, to_curr, forex_rates)
                
                if from_curr == 'EUR':
                    expected = base_rate
                else:
                    expected = 1.0 / base_rate
                
                diff_pct = abs((rate - expected) / expected * 100)
                
                if diff_pct < 1:
                    self.result.add_pass(f"Forex {from_curr}->{to_curr}", f"Rate: {rate:.6f}")
                else:
                    self.result.add_fail(f"Forex {from_curr}->{to_curr}", f"{expected:.6f}", f"{rate:.6f}")
                    
        except Exception as e:
            self.result.add_error('get_forex_rate', e)
    
    def test_validation_coherence(self):
        try:
            from arbitrage_engine_bis import validate_config_coherence
            
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            alerts = validate_config_coherence(config['markets'], config['forex_rates'])
            critical = [a for a in alerts if a['severity'] == 'ERROR']
            
            if len(critical) == 0:
                self.result.add_pass('Validation config', 'Aucune erreur critique')
            else:
                self.result.add_fail('Validation config', '0 erreurs', f"{len(critical)} erreurs")
                
        except Exception as e:
            self.result.add_error('validate_config_coherence', e)
    
    def test_margin_ranges(self):
        try:
            from arbitrage_engine_bis import calculate_profit_route
            
            for capital_eur in [100, 1000, 10000]:
                result = calculate_profit_route(capital_eur / 1.08, 'EUR', 'XAF', False)
                
                if result:
                    profit = result.get('profit_pct', 0)
                    
                    if -10 <= profit <= 20:
                        self.result.add_pass(f"Capital {capital_eur}€", f"Marge: {profit:.2f}%")
                    else:
                        self.result.add_fail(f"Capital {capital_eur}€", "Marge cohérente", f"{profit:.2f}%")
                        
        except Exception as e:
            self.result.add_error('test_margin_ranges', e)


class DailyBriefingTests:
    def __init__(self):
        self.result = TestResult("Tests Daily Briefing")
        self.temp_dir = tempfile.mkdtemp()
    
    def run_all(self):
        print("\n🔬 TESTS DAILY BRIEFING")
        print("="*60)
        
        self.test_file_creation()
        self.test_rotation_id_generation()
        self.test_csv_append()
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        self.result.print_summary()
        return self.result
    
    def test_file_creation(self):
        try:
            from daily_briefing_bis import robust_csv_append
            
            test_file = os.path.join(self.temp_dir, 'test_transactions.csv')
            
            data = {
                'Date': '2025-09-30',
                'Rotation_ID': 'TEST001',
                'Type': 'ACHAT',
                'Market': 'EUR',
                'Currency': 'EUR',
                'Amount_USDT': 100,
                'Price_Local': 1.08,
                'Amount_Local': 108,
                'Fee_Pct': 0.1,
                'Payment_Method': 'Bank',
                'Counterparty_ID': 'TEST',
                'Notes': 'Test'
            }
            
            success = robust_csv_append(test_file, data)
            
            if success and os.path.exists(test_file):
                self.result.add_pass('CSV creation', 'Fichier créé')
            else:
                self.result.add_fail('CSV creation', 'Fichier créé', 'Échec')
                
        except Exception as e:
            self.result.add_error('test_file_creation', e)
    
    def test_rotation_id_generation(self):
        try:
            from daily_briefing_bis import generate_new_rotation_id
            
            new_id = generate_new_rotation_id(None)
            today = datetime.now().strftime("%Y%m%d")
            
            if new_id.startswith(f"R{today}"):
                self.result.add_pass('ID generation - new', new_id)
            else:
                self.result.add_fail('ID generation - new', f"R{today}-*", new_id)
            
            new_id2 = generate_new_rotation_id(new_id)
            
            if new_id2 != new_id and new_id2.startswith(f"R{today}"):
                self.result.add_pass('ID generation - increment', new_id2)
            else:
                self.result.add_fail('ID generation - increment', 'ID différent', new_id2)
                
        except Exception as e:
            self.result.add_error('test_rotation_id_generation', e)
    
    def test_csv_append(self):
        try:
            from daily_briefing_bis import robust_csv_append
            import pandas as pd
            
            test_file = os.path.join(self.temp_dir, 'test_append.csv')
            
            for i in range(3):
                data = {
                    'Date': f'2025-09-{30-i}',
                    'Rotation_ID': f'TEST{i:03d}',
                    'Type': 'ACHAT',
                    'Market': 'EUR',
                    'Currency': 'EUR',
                    'Amount_USDT': 100 + i,
                    'Price_Local': 1.08,
                    'Amount_Local': 108,
                    'Fee_Pct': 0.1,
                    'Payment_Method': 'Bank',
                    'Counterparty_ID': 'TEST',
                    'Notes': f'Test {i}'
                }
                robust_csv_append(test_file, data)
            
            df = pd.read_csv(test_file, sep=';')
            
            if len(df) == 3:
                self.result.add_pass('CSV append - no empty lines', '3 lignes valides')
            else:
                self.result.add_fail('CSV append - no empty lines', '3 lignes', f'{len(df)} lignes')
                
        except Exception as e:
            self.result.add_error('test_csv_append', e)


class UpdateKPIsTests:
    def __init__(self):
        self.result = TestResult("Tests Update KPIs")
        self.temp_dir = tempfile.mkdtemp()
    
    def run_all(self):
        print("\n🔬 TESTS UPDATE KPIS")
        print("="*60)
        
        self.test_report_structure()
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        self.result.print_summary()
        return self.result
    
    def test_report_structure(self):
        try:
            from update_kpis_v4_bis import create_detailed_reports_structure
            
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            dirs = create_detailed_reports_structure()
            
            os.chdir(original_cwd)
            
            expected_keys = ['base_dir', 'year_dir', 'month_dir', 'daily_dir']
            
            if all(key in dirs for key in expected_keys):
                self.result.add_pass('Report structure', 'Tous les dossiers créés')
            else:
                self.result.add_fail('Report structure', str(expected_keys), str(dirs.keys()))
                
        except Exception as e:
            self.result.add_error('test_report_structure', e)


class RotationManagerTests:
    def __init__(self):
        self.result = TestResult("Tests Rotation Manager")
        self.temp_dir = tempfile.mkdtemp()
    
    def run_all(self):
        print("\n🔬 TESTS ROTATION MANAGER")
        print("="*60)
        
        self.test_state_persistence()
        self.test_loop_currency()
        self.test_cycle_increment()
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        self.result.print_summary()
        return self.result
    
    def test_state_persistence(self):
        try:
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            from rotation_manager import RotationManager
            
            manager = RotationManager()
            manager.init_rotation('TEST001')
            
            if os.path.exists('rotation_state.json'):
                self.result.add_pass('State persistence - save', 'Fichier créé')
            else:
                self.result.add_fail('State persistence - save', 'Fichier créé', 'Aucun fichier')
            
            manager2 = RotationManager()
            rotation = manager2.get_rotation('TEST001')
            
            if rotation and rotation['rotation_id'] == 'TEST001':
                self.result.add_pass('State persistence - load', 'État rechargé')
            else:
                self.result.add_fail('State persistence - load', 'TEST001', str(rotation))
            
            os.chdir(original_cwd)
            
        except Exception as e:
            self.result.add_error('test_state_persistence', e)
    
    def test_loop_currency(self):
        try:
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            from rotation_manager import RotationManager
            
            manager = RotationManager()
            manager.init_rotation('TEST002')
            manager.set_loop_currency('TEST002', 'XAF')
            
            currency = manager.get_loop_currency('TEST002')
            
            if currency == 'XAF':
                self.result.add_pass('Loop currency', 'XAF configuré')
            else:
                self.result.add_fail('Loop currency', 'XAF', str(currency))
            
            os.chdir(original_cwd)
            
        except Exception as e:
            self.result.add_error('test_loop_currency', e)
    
    def test_cycle_increment(self):
        try:
            original_cwd = os.getcwd()
            os.chdir(self.temp_dir)
            
            from rotation_manager import RotationManager
            
            manager = RotationManager()
            manager.init_rotation('TEST003')
            
            cycle1 = manager.increment_cycle('TEST003')
            cycle2 = manager.increment_cycle('TEST003')
            
            if cycle1 == 1 and cycle2 == 2:
                self.result.add_pass('Cycle increment', '1 -> 2')
            else:
                self.result.add_fail('Cycle increment', '1, 2', f'{cycle1}, {cycle2}')
            
            os.chdir(original_cwd)
            
        except Exception as e:
            self.result.add_error('test_cycle_increment', e)


def save_results_to_file(all_results):
    """Sauvegarde les résultats dans un fichier JSON et TXT"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Créer le dossier test_reports s'il n'existe pas
    os.makedirs('test_reports', exist_ok=True)
    
    # JSON détaillé
    json_file = f'test_reports/unit_tests_{timestamp}.json'
    json_data = {
        'timestamp': datetime.now().isoformat(),
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
    
    # TXT lisible
    txt_file = f'test_reports/unit_tests_{timestamp}.txt'
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("RAPPORT DE TESTS UNITAIRES\n")
        f.write(f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
        f.write("="*60 + "\n\n")
        
        for result in all_results:
            f.write(f"\n{result.name}\n")
            f.write("-"*60 + "\n")
            f.write(f"✅ Passed: {result.passed}\n")
            f.write(f"❌ Failed: {result.failed}\n")
            f.write(f"💥 Errors: {result.errors}\n")
            
            if result.failed > 0 or result.errors > 0:
                f.write("\nDétails:\n")
                for detail in result.details:
                    if detail['status'] in ['FAIL', 'ERROR']:
                        f.write(f"  - {detail['test']}: {detail.get('error', detail.get('actual', ''))}\n")
        
        f.write("\n" + "="*60 + "\n")
        f.write("RÉSUMÉ GLOBAL\n")
        f.write("="*60 + "\n")
        f.write(f"Total: {total} tests\n")
        f.write(f"✅ Passed: {json_data['summary']['total_passed']} ({json_data['summary']['pass_rate']:.1f}%)\n")
        f.write(f"❌ Failed: {json_data['summary']['total_failed']}\n")
        f.write(f"💥 Errors: {json_data['summary']['total_errors']}\n")
    
    print(f"\n📄 Résultats sauvegardés:")
    print(f"  - JSON: {json_file}")
    print(f"  - TXT:  {txt_file}")
    
    return json_file, txt_file


def run_all_unit_tests():
    """Lance tous les tests unitaires"""
    print("\n" + "="*60)
    print("🧪 SUITE DE TESTS UNITAIRES COMPLÈTE")
    print("="*60)
    
    all_results = []
    
    engine_tests = ArbitrageEngineTests()
    all_results.append(engine_tests.run_all())
    
    briefing_tests = DailyBriefingTests()
    all_results.append(briefing_tests.run_all())
    
    kpi_tests = UpdateKPIsTests()
    all_results.append(kpi_tests.run_all())
    
    manager_tests = RotationManagerTests()
    all_results.append(manager_tests.run_all())
    
    print("\n" + "="*60)
    print("📊 RÉSUMÉ GLOBAL")
    print("="*60)
    
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_errors = sum(r.errors for r in all_results)
    total_tests = total_passed + total_failed + total_errors
    
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total: {total_tests} tests")
    print(f"✅ Passed: {total_passed} ({pass_rate:.1f}%)")
    print(f"❌ Failed: {total_failed}")
    print(f"💥 Errors: {total_errors}")
    print("="*60)
    
    # SAUVEGARDE DES RÉSULTATS
    save_results_to_file(all_results)
    
    return pass_rate >= 80


if __name__ == "__main__":
    success = run_all_unit_tests()
    sys.exit(0 if success else 1)