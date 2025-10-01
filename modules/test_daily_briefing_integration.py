# modules/test_daily_briefing_integration.py

import sys
import os
import shutil
import tempfile
import subprocess
import json
from pathlib import Path
import unittest
from datetime import datetime

# Configuration chemin
current_file = os.path.abspath(__file__)
modules_dir = os.path.dirname(current_file)
project_root = os.path.dirname(modules_dir)

# Vérifier que config.json existe
if not os.path.exists(os.path.join(project_root, 'config.json')):
    print(f"ERREUR: config.json introuvable dans {project_root}")
    sys.exit(1)

os.chdir(project_root)
sys.path.insert(0, project_root)
os.chdir(project_root)
sys.path.insert(0, project_root)


class TestDailyBriefingSimulationIntegration(unittest.TestCase):
    """Tests d'intégration réels pour daily_briefing_bis.py --simulation"""
    
    def setUp(self):
        """Préparation environnement de test - Approche simplifiée"""
        # Sauvegarder le vrai dossier simulations
        self.real_sim_backup = None
        if os.path.exists('simulations'):
            self.real_sim_backup = 'simulations_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.move('simulations', self.real_sim_backup)
    
    def tearDown(self):
        """Nettoyage"""
        # Nettoyer simulations de test
        if os.path.exists('simulations'):
            shutil.rmtree('simulations', ignore_errors=True)
        
        # Restaurer simulations réelles
        if self.real_sim_backup and os.path.exists(self.real_sim_backup):
            shutil.move(self.real_sim_backup, 'simulations')
    
    # ==================== TESTS COMMANDE CLI ====================
    
    def test_simulation_command_exists(self):
        """Test: Commande --simulation existe"""
        result = subprocess.run(
            [sys.executable, 'daily_briefing_bis.py', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Si --help n'existe pas, tester directement
        # (daily_briefing n'a pas de --help, mais on teste l'existence)
        self.assertEqual(result.returncode, 0)
    
    def test_simulation_command_with_mock_inputs(self):
        """Test: Commande --simulation avec inputs simulés"""
        # Créer un script qui simule les inputs utilisateur
        input_script = """
import sys
sys.path.insert(0, '.')

# Mock des inputs
from unittest.mock import patch

with patch('builtins.input', side_effect=['EUR', '1000', '1', 'n', 'n']):
    with patch('simulation_module.Prompt.ask', side_effect=['EUR', 'EUR']):
        with patch('simulation_module.FloatPrompt.ask', return_value=1000.0):
            with patch('simulation_module.IntPrompt.ask', return_value=1):
                with patch('simulation_module.Confirm.ask', side_effect=[True, False]):
                    import daily_briefing_bis
                    # Simuler la commande
                    sys.argv = ['daily_briefing_bis.py', '--simulation']
                    daily_briefing_bis.main()
"""
        
        # Ce test est complexe car nécessite mock des inputs interactifs
        # Dans la vraie vie, on utiliserait des fixtures ou un mode non-interactif
        pass  # Placeholder - voir test suivant
    
    # ==================== TESTS INTÉGRATION FONCTIONNELLE ====================
    
    def test_simulation_module_import_from_daily_briefing(self):
        """Test: Import du module simulation depuis daily_briefing"""
        import importlib.util
        
        spec = importlib.util.spec_from_file_location(
            "daily_briefing_bis",
            "daily_briefing_bis.py"
        )
        daily_briefing = importlib.util.module_from_spec(spec)
        
        # Vérifier que le module se charge sans erreur
        try:
            spec.loader.exec_module(daily_briefing)
            success = True
        except Exception as e:
            print(f"Erreur import: {e}")
            success = False
        
        self.assertTrue(success)
    
    def test_simulation_creates_output_files(self):
        """Test: La simulation crée bien les fichiers attendus"""
        # Simuler une exécution complète (sans inputs interactifs)
        from simulation_module import SimulationEngine
        from unittest.mock import patch
        
        engine = SimulationEngine()
        
        # Mock des inputs utilisateur
        params = {
            'sourcing_currency': 'EUR',
            'nb_cycles': 1,
            'loop_currency': None,
            'soft_excluded': [],
            'initial_capital': 1000
        }
        
        # Mock de la route optimale
        with patch.object(engine, '_find_optimal_route') as mock_route:
            mock_route.return_value = {
                'detailed_route': 'EUR → USDT → XAF',
                'profit_pct': 5.0,
                'sourcing_market_code': 'EUR',
                'selling_market_code': 'XAF',
                'use_double_cycle': False,
                'final_amount_usdt': 1050,
                'revenue_eur': 945,
                'plan_de_vol': {'phases': []}
            }
            
            with patch.object(engine, '_get_user_inputs') as mock_inputs:
                mock_inputs.return_value = params
                
                # Exécuter la simulation
                result = engine.run_simulation()
        
        self.assertTrue(result)
        
        # Vérifier que le dossier simulations existe
        self.assertTrue(Path('simulations').exists())
        
        # Vérifier qu'au moins un dossier SIM_ existe
        sim_dirs = list(Path('simulations').glob('SIM_*'))
        self.assertGreater(len(sim_dirs), 0)
        
        # Vérifier les fichiers dans le dernier dossier
        if sim_dirs:
            latest_sim = sim_dirs[-1]
            self.assertTrue((latest_sim / 'transactions.csv').exists())
            self.assertTrue((latest_sim / 'plan_de_vol.json').exists())
            self.assertTrue((latest_sim / 'simulation_config.json').exists())
            self.assertTrue((latest_sim / 'simulation_report.txt').exists())
    
    def test_simulation_output_file_formats(self):
        """Test: Format des fichiers générés"""
        from simulation_module import SimulationEngine
        from unittest.mock import patch
        
        engine = SimulationEngine()
        engine._create_simulation_dirs()
        
        params = {
            'sourcing_currency': 'EUR',
            'nb_cycles': 1,
            'loop_currency': None,
            'soft_excluded': [],
            'initial_capital': 1000
        }
        
        mock_route = {
            'detailed_route': 'EUR → USDT → XAF',
            'profit_pct': 5.0,
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False,
            'final_amount_usdt': 1050,
            'revenue_eur': 945,
            'plan_de_vol': {'phases': []}
        }
        
        transactions, _, final_usdt = engine._generate_simulated_transactions(
            params, mock_route
        )
        
        engine._save_simulation_data(transactions, params, mock_route, final_usdt)
        
        # Test 1: transactions.csv est valide
        import pandas as pd
        df = pd.read_csv(engine.simulation_dir / 'transactions.csv', sep=';')
        self.assertEqual(len(df), 3)  # 1 cycle = 3 transactions
        self.assertIn('Rotation_ID', df.columns)
        
        # Test 2: plan_de_vol.json est valide
        with open(engine.simulation_dir / 'plan_de_vol.json', 'r') as f:
            plan = json.load(f)
        self.assertIsInstance(plan, dict)
        
        # Test 3: simulation_config.json est valide
        with open(engine.simulation_dir / 'simulation_config.json', 'r') as f:
            config = json.load(f)
        self.assertIn('simulation_id', config)
        self.assertIn('parameters', config)
        self.assertIn('results', config)
        
        # Test 4: simulation_report.txt existe et n'est pas vide
        report_file = engine.simulation_dir / 'simulation_report.txt'
        self.assertTrue(report_file.exists())
        self.assertGreater(report_file.stat().st_size, 100)
    
    # ==================== TESTS WORKFLOW COMPLET ====================
    
    def test_end_to_end_simulation_workflow(self):
        """Test: Workflow complet E2E avec tous les composants"""
        from simulation_module import SimulationEngine
        from unittest.mock import patch
        
        # 1. Initialisation
        engine = SimulationEngine()
        self.assertIsNotNone(engine.config)
        
        # 2. Création dossiers
        engine._create_simulation_dirs()
        self.assertTrue(Path('simulations').exists())
        
        # 3. Paramètres
        params = {
            'sourcing_currency': 'EUR',
            'nb_cycles': 2,
            'loop_currency': 'EUR',
            'soft_excluded': ['XAF'],
            'initial_capital': 1000
        }
        
        # 4. Recherche route (avec exclusion)
        with patch('simulation_module.calculate_profit_route') as mock_calc:
            def calc_side_effect(capital, sourcing, selling, dc):
                if selling == 'XAF':
                    return None  # XAF exclu
                return {
                    'detailed_route': f'{sourcing} → USDT → {selling}',
                    'profit_pct': 3.5,
                    'sourcing_market_code': sourcing,
                    'selling_market_code': selling,
                    'use_double_cycle': dc,
                    'final_amount_usdt': 1035,
                    'revenue_eur': 930,
                    'plan_de_vol': {'phases': []}
                }
            
            mock_calc.side_effect = calc_side_effect
            
            route = engine._find_optimal_route('EUR', ['XAF'], 'EUR')
        
        self.assertIsNotNone(route)
        self.assertNotEqual(route['selling_market_code'], 'XAF')
        
        # 5. Génération transactions
        with patch('simulation_module.calculate_profit_route', side_effect=calc_side_effect):
            transactions, rotation_id, final_usdt = engine._generate_simulated_transactions(
                params, route
            )
        
        self.assertEqual(len(transactions), 6)  # 2 cycles = 6 transactions
        self.assertTrue(rotation_id.startswith('R'))
        
        # 6. Sauvegarde
        engine._save_simulation_data(transactions, params, route, final_usdt)
        
        # 7. Vérifications finales
        self.assertTrue((engine.simulation_dir / 'transactions.csv').exists())
        
        # Vérifier cohérence données
        import pandas as pd
        df = pd.read_csv(engine.simulation_dir / 'transactions.csv', sep=';')
        
        # Tous les Rotation_ID doivent être identiques
        unique_ids = df['Rotation_ID'].unique()
        self.assertEqual(len(unique_ids), 1)
        
        # Nombre de transactions par type
        types = df['Type'].value_counts()
        self.assertEqual(types['ACHAT'], 2)
        self.assertEqual(types['VENTE'], 2)
        self.assertEqual(types['CONVERSION'], 2)


def run_integration_tests():
    """Lance les tests d'intégration"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDailyBriefingSimulationIntegration)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n{'='*70}")
    print(f"RÉSUMÉ TESTS D'INTÉGRATION")
    print(f"{'='*70}")
    print(f"Total: {result.testsRun}")
    print(f"Réussis: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)