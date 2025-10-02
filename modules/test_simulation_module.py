# modules/test_simulation_module.py

import sys
import os
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
import unittest
import math
from unittest.mock import patch, MagicMock

# Configuration chemin
current_file = os.path.abspath(__file__)
modules_dir = os.path.dirname(current_file)
project_root = os.path.dirname(modules_dir)
# S'ASSURER qu'on est dans le bon répertoire AVANT d'importer
if not os.path.exists(os.path.join(project_root, 'config.json')):
    print(f"ERREUR: config.json introuvable dans {project_root}")
    sys.exit(1)

os.chdir(project_root)
sys.path.insert(0, project_root)

from simulation_module import SimulationEngine


class TestSimulationEngine(unittest.TestCase):
    """Tests complets pour le moteur de simulation"""
    
    def setUp(self):
        """Préparation avant chaque test - Approche simplifiée"""
        # Créer un dossier temporaire pour les simulations de test
        self.temp_sim_dir = tempfile.mkdtemp(prefix='test_sim_')
        
        # Sauvegarder le vrai dossier simulations s'il existe
        self.real_sim_backup = None
        if os.path.exists('simulations'):
            self.real_sim_backup = 'simulations_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.move('simulations', self.real_sim_backup)       
        # Créer le moteur (utilise le vrai config.json du projet)
        self.engine = SimulationEngine()        

        

    
    def tearDown(self):
        """Nettoyage après chaque test"""
        # Supprimer le dossier simulations de test
        if os.path.exists('simulations'):
            shutil.rmtree('simulations', ignore_errors=True)
        
        # Restaurer le vrai dossier simulations
        if self.real_sim_backup and os.path.exists(self.real_sim_backup):
            shutil.move(self.real_sim_backup, 'simulations')
        
        # Nettoyer le temp dir
        shutil.rmtree(self.temp_sim_dir, ignore_errors=True)
    # ==================== TESTS INITIALISATION ====================
    
    def test_engine_initialization(self):
        """Test: Initialisation correcte du moteur"""
        self.assertIsNotNone(self.engine)
        self.assertIsNone(self.engine.simulation_id)
        self.assertIsNone(self.engine.simulation_dir)
        self.assertGreaterEqual(len(self.engine.config['markets']), 3)
    
    def test_load_config_missing_file(self):
        """Test: Gestion fichier config manquant"""
        # Backup config
        shutil.copy('config.json', 'config.json.backup_test')
        
        os.remove('config.json')
        with self.assertRaises(FileNotFoundError):
            SimulationEngine()
        
        # Restore config
        shutil.move('config.json.backup_test', 'config.json')
    
    def test_load_config_invalid_json(self):
        """Test: Gestion JSON corrompu"""
        # Backup config
        shutil.copy('config.json', 'config.json.backup_test')
        
        with open('config.json', 'w') as f:
            f.write('{invalid json}')
        with self.assertRaises(json.JSONDecodeError):
            SimulationEngine()
        
        # Restore config
        shutil.move('config.json.backup_test', 'config.json')
    
    # ==================== TESTS CRÉATION DOSSIERS ====================
    
    def test_create_simulation_dirs(self):
        """Test: Création structure dossiers"""
        sim_dir = self.engine._create_simulation_dirs()
        
        self.assertTrue(sim_dir.exists())
        self.assertIsNotNone(self.engine.simulation_id)
        self.assertTrue(self.engine.simulation_id.startswith('SIM_'))
    
    def test_create_simulation_dirs_multiple_calls(self):
        """Test: Plusieurs appels créent dossiers différents"""
        dir1 = self.engine._create_simulation_dirs()
        
        # Petit délai pour différencier les timestamps
        import time
        time.sleep(1.1)
        
        engine2 = SimulationEngine()
        dir2 = engine2._create_simulation_dirs()
        
        self.assertNotEqual(dir1, dir2)
        self.assertTrue(dir1.exists())
        self.assertTrue(dir2.exists())
    
    # ==================== TESTS CONVERSION USDT ====================
    
    def test_convert_to_usdt_eur(self):
        """Test: Conversion EUR → USDT"""
        usdt = self.engine._convert_to_usdt(1000, 'EUR')
        
        # 1000 EUR / (1.08 * 1.001) ≈ 924 USDT
        self.assertGreater(usdt, 1100)
        self.assertLess(usdt, 1200)
    
    def test_convert_to_usdt_xaf(self):
        """Test: Conversion XAF → USDT"""
        usdt = self.engine._convert_to_usdt(625000, 'XAF')
        
        # 625000 XAF / 625 = 1000 USDT
        self.assertAlmostEqual(usdt, 1000, delta=50)
    
    def test_convert_to_usdt_invalid_currency(self):
        """Test: Devise invalide retourne montant inchangé"""
        usdt = self.engine._convert_to_usdt(1000, 'INVALID')
        self.assertEqual(usdt, 1000)
    
    def test_convert_to_usdt_zero_amount(self):
        """Test: Montant nul"""
        usdt = self.engine._convert_to_usdt(0, 'EUR')
        self.assertEqual(usdt, 0)
    
    def test_convert_to_usdt_negative_amount(self):
        """Test: Montant négatif"""
        usdt = self.engine._convert_to_usdt(-1000, 'EUR')
        self.assertLess(usdt, 0)
    
    # ==================== TESTS PRIX MARCHÉ ====================
    
    def test_get_market_price_buy(self):
        """Test: Récupération prix achat"""
        first_market = self.engine.config['markets'][0]
        currency = first_market['currency']
        expected_price = first_market['buy_price']
        
        price = self.engine._get_market_price(currency, 'buy')
        self.assertEqual(price, expected_price)
    
    def test_get_market_price_sell(self):
        """Test: Récupération prix vente"""
        price = self.engine._get_market_price('XAF', 'sell')
        self.assertEqual(price, 620)
    
    def test_get_market_price_invalid_currency(self):
        """Test: Devise invalide retourne 0"""
        price = self.engine._get_market_price('INVALID', 'buy')
        self.assertEqual(price, 0)
    
    def test_get_market_fee(self):
        """Test: Récupération frais"""
        fee = self.engine._get_market_fee('KES')
        self.assertEqual(fee, 1.0)
    
    def test_get_market_fee_zero(self):
        """Test: Frais zéro"""
        fee = self.engine._get_market_fee('XAF')
        self.assertEqual(fee, 0.0)
    
    # ==================== TESTS RECHERCHE ROUTE OPTIMALE ====================
    
    @patch('simulation_module.calculate_profit_route')
    def test_find_optimal_route_basic(self, mock_calc):
        """Test: Recherche route optimale basique"""
        mock_calc.return_value = {
            'detailed_route': 'EUR → USDT → XAF → EUR',
            'profit_pct': 5.5,
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False,
            'plan_de_vol': {'phases': []}
        }
        
        route = self.engine._find_optimal_route('EUR', [], None)
        
        self.assertIsNotNone(route)
        self.assertEqual(route['profit_pct'], 5.5)
        self.assertEqual(route['selling_market_code'], 'XAF')
    
    @patch('simulation_module.calculate_profit_route')
    def test_find_optimal_route_with_exclusion(self, mock_calc):
        """Test: Route avec marché exclu"""
        def calc_side_effect(capital, sourcing, selling, dc):
            if selling == 'XAF':
                return None  # XAF exclu
            return {
                'detailed_route': f'{sourcing} → USDT → {selling}',
                'profit_pct': 3.0,
                'sourcing_market_code': sourcing,
                'selling_market_code': selling,
                'use_double_cycle': dc,
                'plan_de_vol': {'phases': []}
            }
        
        mock_calc.side_effect = calc_side_effect
        
        route = self.engine._find_optimal_route('EUR', ['XAF'], None)
        
        self.assertIsNotNone(route)
        self.assertNotEqual(route['selling_market_code'], 'XAF')
    
    @patch('simulation_module.calculate_profit_route')
    def test_find_optimal_route_exclusion_override_by_loop(self, mock_calc):
        """Test: Exclusion overridée par bouclage forcé"""
        mock_calc.return_value = {
            'detailed_route': 'EUR → USDT → XAF',
            'profit_pct': 5.0,
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False,
            'plan_de_vol': {'phases': []}
        }
        
        # XAF exclu MAIS forcé comme bouclage → doit être accepté
        route = self.engine._find_optimal_route('EUR', ['XAF'], 'XAF')
        
        self.assertIsNotNone(route)
        self.assertEqual(route['selling_market_code'], 'XAF')
    
    @patch('simulation_module.calculate_profit_route')
    def test_find_optimal_route_no_valid_routes(self, mock_calc):
        """Test: Aucune route valide"""
        mock_calc.return_value = None
        
        route = self.engine._find_optimal_route('EUR', [], None)
        
        self.assertIsNone(route)
    
    @patch('simulation_module.calculate_profit_route')
    def test_find_optimal_route_all_excluded(self, mock_calc):
        """Test: Tous marchés exclus sauf sourcing"""
        mock_calc.return_value = None
        route = self.engine._find_optimal_route('EUR', ['XAF', 'KES'], None)
        
        self.assertIsNone(route)
    
    # ==================== TESTS GÉNÉRATION TRANSACTIONS ====================
    
    @patch('simulation_module.calculate_profit_route')
    def test_generate_transactions_single_cycle(self, mock_calc):
        """Test: Génération transactions pour 1 cycle"""
        mock_calc.return_value = {
            'detailed_route': 'EUR → USDT → XAF',
            'profit_pct': 5.0,
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False,
            'final_amount_usdt': 1050,
            'revenue_eur': 945,
            'plan_de_vol': {'phases': []}
        }
        
        params = {
            'sourcing_currency': 'EUR',
            'nb_cycles': 1,
            'loop_currency': None,
            'soft_excluded': [],
            'initial_capital': 1000
        }
        
        best_route = mock_calc.return_value
        
        transactions, rotation_id, final_usdt = self.engine._generate_simulated_transactions(
            params, best_route
        )
        
        # 1 cycle = 3 transactions (ACHAT, VENTE, CONVERSION)
        self.assertEqual(len(transactions), 3)
        self.assertTrue(rotation_id.startswith('R'))
        self.assertEqual(final_usdt, 1050)
    
    @patch('simulation_module.calculate_profit_route')
    def test_generate_transactions_multiple_cycles(self, mock_calc):
        """Test: Génération transactions pour 3 cycles"""
        mock_calc.return_value = {
            'detailed_route': 'EUR → USDT → XAF',
            'profit_pct': 5.0,
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False,
            'final_amount_usdt': 1050,
            'revenue_eur': 945,
            'plan_de_vol': {'phases': []}
        }
        
        params = {
            'sourcing_currency': 'EUR',
            'nb_cycles': 3,
            'loop_currency': 'EUR',
            'soft_excluded': [],
            'initial_capital': 1000
        }
        
        best_route = mock_calc.return_value
        
        transactions, rotation_id, final_usdt = self.engine._generate_simulated_transactions(
            params, best_route
        )
        
        # 3 cycles = 9 transactions
        self.assertEqual(len(transactions), 9)
        
        # Vérifier types de transactions
        types = [t['Type'] for t in transactions]
        self.assertEqual(types.count('ACHAT'), 3)
        self.assertEqual(types.count('VENTE'), 3)
        self.assertEqual(types.count('CONVERSION'), 3)
    
    @patch('simulation_module.calculate_profit_route')
    def test_generate_transactions_with_loop_currency(self, mock_calc):
        """Test: Génération avec monnaie de bouclage"""
        mock_calc.return_value = {
            'detailed_route': 'EUR → USDT → XAF',
            'profit_pct': 5.0,
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False,
            'final_amount_usdt': 1050,
            'revenue_eur': 945,
            'plan_de_vol': {'phases': []}
        }
        
        params = {
            'sourcing_currency': 'EUR',
            'nb_cycles': 2,
            'loop_currency': 'XAF',
            'soft_excluded': [],
            'initial_capital': 1000
        }
        
        best_route = mock_calc.return_value
        
        transactions, _, _ = self.engine._generate_simulated_transactions(params, best_route)
        
        # Vérifier que les conversions vont vers XAF
        conversions = [t for t in transactions if t['Type'] == 'CONVERSION']
        for conv in conversions:
            self.assertEqual(conv['Currency'], 'XAF')
    
    @patch('simulation_module.calculate_profit_route')
    def test_generate_transactions_fails_mid_cycle(self, mock_calc):
        """Test: Échec calcul en cours de route"""
        call_count = [0]
        
        def calc_side_effect(*args):
            call_count[0] += 1
            if call_count[0] > 2:
                return None  # Échec au 3e cycle
            return {
                'detailed_route': 'EUR → USDT → XAF',
                'profit_pct': 5.0,
                'sourcing_market_code': 'EUR',
                'selling_market_code': 'XAF',
                'use_double_cycle': False,
                'final_amount_usdt': 1050,
                'revenue_eur': 945,
                'plan_de_vol': {'phases': []}
            }
        
        mock_calc.side_effect = calc_side_effect
        
        params = {
            'sourcing_currency': 'EUR',
            'nb_cycles': 5,
            'loop_currency': None,
            'soft_excluded': [],
            'initial_capital': 1000
        }
        
        best_route = {
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False
        }
        
        transactions, _, _ = self.engine._generate_simulated_transactions(params, best_route)
        
        # Doit s'arrêter après 2 cycles (6 transactions)
        self.assertEqual(len(transactions), 6)
    
    # ==================== TESTS SAUVEGARDE DONNÉES ====================
    
    @patch('simulation_module.calculate_profit_route')
    def test_save_simulation_data_creates_files(self, mock_calc):
        """Test: Sauvegarde crée tous les fichiers"""
        self.engine._create_simulation_dirs()
        
        mock_calc.return_value = {
            'detailed_route': 'EUR → USDT → XAF',
            'profit_pct': 5.0,
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False,
            'final_amount_usdt': 1050,
            'revenue_eur': 945,
            'plan_de_vol': {'phases': [
                {'cycle': 1, 'type': 'ACHAT'},
                {'cycle': 1, 'type': 'VENTE'},
                {'cycle': 1, 'type': 'CONVERSION'}
            ]}
        }
        
        params = {
            'sourcing_currency': 'EUR',
            'nb_cycles': 1,
            'loop_currency': None,
            'soft_excluded': [],
            'initial_capital': 1000
        }
        
        best_route = mock_calc.return_value
        
        transactions, _, final_usdt = self.engine._generate_simulated_transactions(
            params, best_route
        )
        
        self.engine._save_simulation_data(transactions, params, best_route, final_usdt)
        
        # Vérifier existence des 4 fichiers
        self.assertTrue((self.engine.simulation_dir / 'transactions.csv').exists())
        self.assertTrue((self.engine.simulation_dir / 'plan_de_vol.json').exists())
        self.assertTrue((self.engine.simulation_dir / 'simulation_config.json').exists())
        self.assertTrue((self.engine.simulation_dir / 'simulation_report.txt').exists())
    
    @patch('simulation_module.calculate_profit_route')
    def test_save_simulation_config_content(self, mock_calc):
        """Test: Contenu du fichier config"""
        self.engine._create_simulation_dirs()
        
        mock_calc.return_value = {
            'detailed_route': 'EUR → USDT → XAF',
            'profit_pct': 5.0,
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False,
            'final_amount_usdt': 1050,
            'revenue_eur': 945,
            'plan_de_vol': {'phases': []}
        }
        
        params = {
            'sourcing_currency': 'EUR',
            'nb_cycles': 1,
            'loop_currency': 'EUR',
            'soft_excluded': ['XAF'],
            'initial_capital': 1000
        }
        
        best_route = mock_calc.return_value
        transactions, _, final_usdt = self.engine._generate_simulated_transactions(
            params, best_route
        )
        
        self.engine._save_simulation_data(transactions, params, best_route, final_usdt)
        
        # Lire et vérifier le contenu
        config_file = self.engine.simulation_dir / 'simulation_config.json'
        with open(config_file, 'r') as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config['parameters']['sourcing_currency'], 'EUR')
        self.assertEqual(saved_config['parameters']['nb_cycles'], 1)
        self.assertEqual(saved_config['parameters']['loop_currency'], 'EUR')
        self.assertIn('XAF', saved_config['parameters']['soft_excluded'])
    
    # ==================== TESTS CAS LIMITES ====================
    
    def test_extreme_capital_zero(self):
        """Test: Capital zéro"""
        usdt = self.engine._convert_to_usdt(0, 'EUR')
        self.assertEqual(usdt, 0)
    
    def test_extreme_capital_very_large(self):
        """Test: Capital très élevé"""
        usdt = self.engine._convert_to_usdt(1000000, 'EUR')
        self.assertGreater(usdt, 900000)
    
    def test_extreme_capital_negative(self):
        """Test: Capital négatif (cas invalide mais testé)"""
        usdt = self.engine._convert_to_usdt(-1000, 'EUR')
        self.assertLess(usdt, 0)
    # ==================== TESTS SAISIE DONNÉES ====================

    def test_get_numeric_input_valid(self):
        """Test: Saisie numérique valide"""
        with patch('builtins.input', return_value='1000'):
            with patch('simulation_module.Confirm.ask', return_value=False):
                result = self.engine._get_numeric_input("Montant", float, 0)
                self.assertEqual(result, 1000.0)

    def test_get_numeric_input_empty_string(self):
        """Test: Chaîne vide refusée"""
        with patch('builtins.input', side_effect=['', 'annuler']):
            with patch('simulation_module.Confirm.ask', return_value=True):
                result = self.engine._get_numeric_input("Montant", float, 0)
                self.assertIsNone(result)

    def test_get_numeric_input_only_spaces(self):
        """Test: Espaces seulement refusés"""
        with patch('builtins.input', side_effect=['   ', 'annuler']):
            with patch('simulation_module.Confirm.ask', return_value=True):
                result = self.engine._get_numeric_input("Montant", float, 0)
                self.assertIsNone(result)

    def test_get_numeric_input_nan(self):
        """Test: NaN détecté et refusé"""
        with patch('builtins.input', side_effect=['nan', 'annuler']):
            with patch('simulation_module.Confirm.ask', return_value=True):
                result = self.engine._get_numeric_input("Montant", float, 0)
                self.assertIsNone(result)

    def test_get_numeric_input_infinity(self):
        """Test: Infinity détecté et refusé"""
        with patch('builtins.input', side_effect=['inf', 'annuler']):
            with patch('simulation_module.Confirm.ask', return_value=True):
                result = self.engine._get_numeric_input("Montant", float, 0)
                self.assertIsNone(result)

    def test_get_numeric_input_negative_below_min(self):
        """Test: Valeur sous le minimum refusée"""
        with patch('builtins.input', side_effect=['-100', 'annuler']):
            with patch('simulation_module.Confirm.ask', return_value=True):
                result = self.engine._get_numeric_input("Montant", float, 0)
                self.assertIsNone(result)

    def test_get_numeric_input_above_max(self):
        """Test: Valeur au-dessus du maximum refusée"""
        with patch('builtins.input', side_effect=['2000000', 'annuler']):
            with patch('simulation_module.Confirm.ask', return_value=True):
                result = self.engine._get_numeric_input("Montant", float, 0)
                self.assertIsNone(result)

    def test_get_numeric_input_with_comma(self):
        """Test: Virgule comme séparateur décimal acceptée"""
        with patch('builtins.input', return_value='1000,50'):
            with patch('simulation_module.Confirm.ask', return_value=False):
                result = self.engine._get_numeric_input("Montant", float, 0)
                self.assertEqual(result, 1000.5)

    def test_get_numeric_input_cancel(self):
        """Test: Annulation utilisateur"""
        with patch('builtins.input', return_value='annuler'):
            with patch('simulation_module.Confirm.ask', return_value=True):
                result = self.engine._get_numeric_input("Montant", float, 0)
                self.assertIsNone(result)

    def test_get_numeric_input_keyboard_interrupt(self):
        """Test: Ctrl+C interrompt proprement"""
        with patch('builtins.input', side_effect=KeyboardInterrupt):
            result = self.engine._get_numeric_input("Montant", float, 0)
            self.assertIsNone(result)

    def test_get_confirmed_input_valid(self):
        """Test: Saisie confirmée valide"""
        with patch('builtins.input', return_value='EUR'):
            result = self.engine._get_confirmed_input("Devise", lambda x: x in ['EUR', 'XAF'])
            self.assertEqual(result, 'EUR')

    def test_get_confirmed_input_invalid_then_valid(self):
        """Test: Saisie invalide puis valide"""
        with patch('builtins.input', side_effect=['INVALID', 'EUR']):
            result = self.engine._get_confirmed_input("Devise", lambda x: x in ['EUR', 'XAF'])
            self.assertEqual(result, 'EUR')

    def test_get_confirmed_input_cancel_confirmed(self):
        """Test: Annulation confirmée"""
        with patch('builtins.input', return_value='annuler'):
            with patch('simulation_module.Confirm.ask', return_value=True):
                result = self.engine._get_confirmed_input("Devise")
                self.assertIsNone(result)

    def test_get_confirmed_input_cancel_rejected(self):
        """Test: Annulation rejetée puis saisie valide"""
        with patch('builtins.input', side_effect=['annuler', 'EUR']):
            with patch('simulation_module.Confirm.ask', return_value=False):
                result = self.engine._get_confirmed_input("Devise", lambda x: x == 'EUR')
                self.assertEqual(result, 'EUR')
    
    @patch('simulation_module.calculate_profit_route')
    def test_zero_cycles(self, mock_calc):
        """Test: Zéro cycles"""
        mock_calc.return_value = {
            'detailed_route': 'EUR → USDT → XAF',
            'profit_pct': 5.0,
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False,
            'final_amount_usdt': 1050,
            'revenue_eur': 945,
            'plan_de_vol': {'phases': []}
        }
        
        params = {
            'sourcing_currency': 'EUR',
            'nb_cycles': 0,
            'loop_currency': None,
            'soft_excluded': [],
            'initial_capital': 1000
        }
        
        best_route = mock_calc.return_value
        
        transactions, _, _ = self.engine._generate_simulated_transactions(params, best_route)
        
        self.assertEqual(len(transactions), 0)
    
    # ==================== TESTS INTÉGRATION ====================
    
    @patch('simulation_module.Prompt.ask')
    @patch('simulation_module.Confirm.ask')
    @patch('simulation_module.IntPrompt.ask')
    @patch('simulation_module.FloatPrompt.ask')
    @patch('simulation_module.calculate_profit_route')
    def test_full_simulation_workflow(self, mock_calc, mock_float, mock_int, mock_confirm, mock_prompt):
        """Test: Workflow complet de simulation"""
        # Mock des inputs utilisateur
        mock_prompt.side_effect = ['EUR', 'EUR', '']  # sourcing, loop, exclusions
        mock_float.return_value = 1000.0
        mock_int.return_value = 1
        mock_confirm.side_effect = [True, False]  # loop_currency, exclusion
        
        mock_calc.return_value = {
            'detailed_route': 'EUR → USDT → XAF',
            'profit_pct': 5.0,
            'sourcing_market_code': 'EUR',
            'selling_market_code': 'XAF',
            'use_double_cycle': False,
            'final_amount_usdt': 1050,
            'revenue_eur': 945,
            'plan_de_vol': {'phases': [
                {'cycle': 1, 'type': 'ACHAT'},
                {'cycle': 1, 'type': 'VENTE'},
                {'cycle': 1, 'type': 'CONVERSION'}
            ]}
        }
        
        result = self.engine.run_simulation()
        
        self.assertTrue(result)
        self.assertTrue(Path('simulations').exists())


# ==================== TEST RUNNER ====================

def run_simulation_tests():
    """Lance tous les tests avec rapport détaillé"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSimulationEngine)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Sauvegarder rapport
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs('test_reports', exist_ok=True)
    
    report_file = f'test_reports/simulation_tests_{timestamp}.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("RAPPORT DE TESTS - MODULE SIMULATION\n")
        f.write(f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Tests exécutés: {result.testsRun}\n")
        f.write(f"Réussites: {result.testsRun - len(result.failures) - len(result.errors)}\n")
        f.write(f"Échecs: {len(result.failures)}\n")
        f.write(f"Erreurs: {len(result.errors)}\n\n")
        
        if result.failures:
            f.write("ÉCHECS:\n")
            for test, traceback in result.failures:
                f.write(f"\n{test}:\n{traceback}\n")
        
        if result.errors:
            f.write("\nERREURS:\n")
            for test, traceback in result.errors:
                f.write(f"\n{test}:\n{traceback}\n")
    
    print(f"\n✓ Rapport sauvegardé: {report_file}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_simulation_tests()
    sys.exit(0 if success else 1)