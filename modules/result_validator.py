# modules/result_validator.py

import pandas as pd
import json
import os
from pathlib import Path

class ResultValidator:
    """Valide que les résultats correspondent aux attentes du scénario"""
    
    def __init__(self, scenario):
        self.scenario = scenario
        self.checks = []
        
    def validate_all(self):
        """Exécute toutes les validations"""
        
        # 1. Valider le fichier transactions.csv
        if os.path.exists('test_output/transactions.csv'):
            self.validate_transactions_file()
        else:
            self.checks.append({
                'name': 'Fichier transactions.csv existe',
                'expected': True,
                'actual': False,
                'passed': False
            })
        
        # 2. Valider le plan de vol
        rotation_id = self.get_rotation_id()
        if rotation_id:
            self.validate_plan_de_vol(rotation_id)
        
        # 3. Valider les KPIs (si la rotation est terminée)
        if self.scenario['category'] != 'error':
            self.validate_kpis()
        
        # 4. Valider le rotation_state.json (si bouclage)
        if self.scenario.get('loop_enabled'):
            self.validate_rotation_state()
        
        # 5. Vérifier l'absence d'erreurs Python non gérées
        self.validate_no_crashes()
        
        # Calculer le résultat global
        all_passed = all(check['passed'] for check in self.checks)
        
        return {
            'all_passed': all_passed,
            'checks': self.checks,
            'passed_count': sum(1 for c in self.checks if c['passed']),
            'total_count': len(self.checks)
        }
    
    def get_rotation_id(self):
        """Récupère l'ID de rotation depuis transactions.csv"""
        try:
            df = pd.read_csv('test_output/transactions.csv', sep=';')
            if not df.empty and 'Rotation_ID' in df.columns:
                return df['Rotation_ID'].iloc[0]
        except:
            pass
        return None
    
    def validate_transactions_file(self):
        """Valide le contenu de transactions.csv"""
        try:
            df = pd.read_csv('test_output/transactions.csv', sep=';')
            
            # Check 1: Nombre de transactions
            expected_count = self.scenario.get('expected_transaction_count')
            if expected_count:
                actual_count = len(df)
                self.checks.append({
                    'name': 'Nombre de transactions',
                    'expected': expected_count,
                    'actual': actual_count,
                    'passed': expected_count == actual_count,
                    'category': 'transactions'
                })
            
            # Check 2: Rotation_ID unique
            rotation_ids = df['Rotation_ID'].unique()
            self.checks.append({
                'name': 'Rotation_ID unique',
                'expected': 1,
                'actual': len(rotation_ids),
                'passed': len(rotation_ids) == 1,
                'category': 'transactions'
            })
            
            # Check 3: Séquence de types de transactions
            expected_sequence = self.scenario.get('expected_transaction_sequence')
            if expected_sequence:
                actual_sequence = df['Type'].tolist()
                self.checks.append({
                    'name': 'Séquence de transactions correcte',
                    'expected': expected_sequence,
                    'actual': actual_sequence,
                    'passed': actual_sequence == expected_sequence,
                    'category': 'transactions'
                })
            
            # Check 4: Pas de montants négatifs ou nuls (sauf CLOTURE)
            df_non_cloture = df[df['Type'] != 'CLOTURE']
            invalid_usdt = df_non_cloture[df_non_cloture['Amount_USDT'].astype(float) <= 0]
            invalid_local = df_non_cloture[df_non_cloture['Amount_Local'].astype(float) <= 0]
            
            self.checks.append({
                'name': 'Montants USDT valides (> 0)',
                'expected': 0,
                'actual': len(invalid_usdt),
                'passed': len(invalid_usdt) == 0,
                'category': 'transactions'
            })
            
            self.checks.append({
                'name': 'Montants locaux valides (> 0)',
                'expected': 0,
                'actual': len(invalid_local),
                'passed': len(invalid_local) == 0,
                'category': 'transactions'
            })
            
            # Check 5: Tous les champs requis sont remplis
            required_fields = ['Date', 'Rotation_ID', 'Type', 'Market', 'Currency']
            for field in required_fields:
                null_count = df[field].isna().sum()
                self.checks.append({
                    'name': f'Champ {field} rempli',
                    'expected': 0,
                    'actual': null_count,
                    'passed': null_count == 0,
                    'category': 'transactions'
                })
            
        except Exception as e:
            self.checks.append({
                'name': 'Validation transactions.csv',
                'expected': 'Success',
                'actual': f'Error: {str(e)}',
                'passed': False,
                'category': 'transactions'
            })
    
    def validate_plan_de_vol(self, rotation_id):
        """Valide le plan de vol"""
        plan_file = f'rotation_plan_{rotation_id}.json'
        
        if not os.path.exists(plan_file):
            self.checks.append({
                'name': 'Plan de vol existe',
                'expected': True,
                'actual': False,
                'passed': False,
                'category': 'plan'
            })
            return
        
        try:
            with open(plan_file, 'r', encoding='utf-8') as f:
                plan = json.load(f)
            
            phases = plan.get('plan_de_vol', {}).get('phases', [])
            
            # Check 1: Nombre de phases
            expected_phases = self.scenario.get('expected_phase_count')
            if expected_phases:
                actual_phases = len(phases)
                self.checks.append({
                    'name': 'Nombre de phases dans le plan',
                    'expected': expected_phases,
                    'actual': actual_phases,
                    'passed': expected_phases == actual_phases,
                    'category': 'plan'
                })
            
            # Check 2: Alternance correcte des types
            phase_types = [p['type'] for p in phases[:-1]]  # Exclure CLOTURE
            expected_pattern = ['ACHAT', 'VENTE', 'CONVERSION']
            
            valid_pattern = True
            for i in range(0, len(phase_types), 3):
                chunk = phase_types[i:i+3]
                if chunk != expected_pattern[:len(chunk)]:
                    valid_pattern = False
                    break
            
            self.checks.append({
                'name': 'Alternance ACHAT/VENTE/CONVERSION correcte',
                'expected': expected_pattern,
                'actual': phase_types[:3] if len(phase_types) >= 3 else phase_types,
                'passed': valid_pattern,
                'category': 'plan'
            })
            
            # Check 3: Dernière phase est CLOTURE
            last_phase_type = phases[-1]['type'] if phases else None
            self.checks.append({
                'name': 'Dernière phase est CLOTURE',
                'expected': 'CLOTURE',
                'actual': last_phase_type,
                'passed': last_phase_type == 'CLOTURE',
                'category': 'plan'
            })
            
        except Exception as e:
            self.checks.append({
                'name': 'Validation plan de vol',
                'expected': 'Success',
                'actual': f'Error: {str(e)}',
                'passed': False,
                'category': 'plan'
            })
    
    def validate_kpis(self):
        """Valide les KPIs calculés"""
        kpis_file = None
        
        # Chercher le fichier KPIs le plus récent
        reports_path = Path('reports_detailed')
        if reports_path.exists():
            for year_dir in reports_path.iterdir():
                for month_dir in year_dir.iterdir():
                    kpis_monthly = month_dir / 'kpis_monthly.json'
                    if kpis_monthly.exists():
                        kpis_file = kpis_monthly
                        break
        
        if not kpis_file:
            self.checks.append({
                'name': 'Fichier KPIs existe',
                'expected': True,
                'actual': False,
                'passed': False,
                'category': 'kpis'
            })
            return
        
        try:
            with open(kpis_file, 'r', encoding='utf-8') as f:
                kpis_data = json.load(f)
            
            kpis = kpis_data.get('kpis', {})
            tolerance = 0.01  # 1 centime de tolérance
            
            # Check 1: Capital investi
            expected_invested = self.scenario.get('expected_capital_invested')
            if expected_invested:
                actual_invested = kpis.get('total_invested', 0)
                diff = abs(expected_invested - actual_invested)
                
                self.checks.append({
                    'name': 'Capital investi correct',
                    'expected': f'{expected_invested:.2f} EUR',
                    'actual': f'{actual_invested:.2f} EUR',
                    'passed': diff <= tolerance,
                    'category': 'kpis'
                })
            
            # Check 2: Capital final
            expected_final = self.scenario.get('expected_capital_final')
            if expected_final:
                actual_final = kpis.get('total_final', 0)
                diff = abs(expected_final - actual_final)
                
                self.checks.append({
                    'name': 'Capital final correct',
                    'expected': f'{expected_final:.2f} EUR',
                    'actual': f'{actual_final:.2f} EUR',
                    'passed': diff <= tolerance,
                    'category': 'kpis'
                })
            
            # Check 3: Profit cohérent
            if expected_invested and expected_final:
                expected_profit = expected_final - expected_invested
                actual_profit = kpis.get('total_profit', 0)
                diff = abs(expected_profit - actual_profit)
                
                self.checks.append({
                    'name': 'Profit cohérent',
                    'expected': f'{expected_profit:.2f} EUR',
                    'actual': f'{actual_profit:.2f} EUR',
                    'passed': diff <= tolerance,
                    'category': 'kpis'
                })
            
            # Check 4: ROI cohérent
            if expected_invested and expected_invested > 0:
                expected_roi = ((expected_final - expected_invested) / expected_invested) * 100
                actual_roi = kpis.get('roi_global', 0)
                diff = abs(expected_roi - actual_roi)
                
                self.checks.append({
                    'name': 'ROI cohérent',
                    'expected': f'{expected_roi:.2f}%',
                    'actual': f'{actual_roi:.2f}%',
                    'passed': diff <= 0.1,  # 0.1% de tolérance
                    'category': 'kpis'
                })
            
        except Exception as e:
            self.checks.append({
                'name': 'Validation KPIs',
                'expected': 'Success',
                'actual': f'Error: {str(e)}',
                'passed': False,
                'category': 'kpis'
            })
    
    def validate_rotation_state(self):
        """Valide rotation_state.json pour les scénarios de bouclage"""
        if not os.path.exists('test_output/rotation_state.json'):
            self.checks.append({
                'name': 'Fichier rotation_state.json existe',
                'expected': True,
                'actual': False,
                'passed': False,
                'category': 'bouclage'
            })
            return
        
        try:
            with open('test_output/rotation_state.json', 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            rotation_id = self.get_rotation_id()
            if not rotation_id:
                return
            
            rotation_data = state.get('active_rotations', {}).get(rotation_id, {})
            
            # Check: Devise de bouclage configurée
            expected_currency = self.scenario.get('loop_currency')
            actual_currency = rotation_data.get('loop_currency')
            
            self.checks.append({
                'name': 'Devise de bouclage configurée',
                'expected': expected_currency,
                'actual': actual_currency,
                'passed': expected_currency == actual_currency,
                'category': 'bouclage'
            })
            
            # Check: Nombre de cycles complétés
            expected_loops = self.scenario.get('nb_loops', 0)
            actual_loops = rotation_data.get('cycles_completed', 0)
            
            self.checks.append({
                'name': 'Nombre de boucles complétées',
                'expected': expected_loops,
                'actual': actual_loops,
                'passed': expected_loops == actual_loops,
                'category': 'bouclage'
            })
            
        except Exception as e:
            self.checks.append({
                'name': 'Validation rotation_state',
                'expected': 'Success',
                'actual': f'Error: {str(e)}',
                'passed': False,
                'category': 'bouclage'
            })
    
    def validate_no_crashes(self):
        """Vérifie qu'aucune erreur Python non gérée n'est survenue"""
        # Cette validation se fait au niveau du test_runner
        # On vérifie simplement que tous les fichiers attendus existent
        
        expected_files = ['test_output/transactions.csv']
        if self.scenario['category'] != 'error':
            expected_files.append('test_output/debriefing.csv')
        
        for file in expected_files:
            exists = os.path.exists(file)
            self.checks.append({
                'name': f'Fichier {file} créé',
                'expected': True,
                'actual': exists,
                'passed': exists,
                'category': 'système'
            })