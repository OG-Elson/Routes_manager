# modules/interaction_simulator.py

import sys
from io import StringIO
from unittest.mock import patch

class InteractionSimulator:
    """Simule les interactions utilisateur avec le système"""
    
    def __init__(self, scenario):
        self.scenario = scenario
        self.input_queue = []
        self.prepare_inputs()
        self.input_index = 0
        
    def prepare_inputs(self):
        """Prépare tous les inputs basés sur le scénario"""
        
        # Pour la planification initiale
        if self.scenario.get('action') != 'resume':
            # Choix de route
            self.input_queue.append(str(self.scenario.get('route_choice', 1)))
            
            # Checklist pré-vol
            self.input_queue.extend(['o', 'o', 'o'])  # Partenaires, Comptes, Canari
        
        # Configuration du bouclage si nécessaire
        if self.scenario.get('loop_enabled'):
            # Cette configuration se fait via commande CLI, pas via input
            pass
        
        # Pour chaque transaction dans le scénario
        transactions = self.scenario.get('transactions', [])
        
        for trans in transactions:
            if trans['type'] == 'ACHAT' or trans['type'] == 'VENTE':
                self.input_queue.append(trans['market'])
                self.input_queue.append(str(trans['amount_usdt']))
                self.input_queue.append(str(trans['amount_local']))
                self.input_queue.append(str(trans['fee_pct']))
                self.input_queue.append(trans['payment_method'])
                self.input_queue.append(trans['counterparty_id'])
                self.input_queue.append(trans['notes'])
                
            elif trans['type'] == 'CONVERSION':
                self.input_queue.append(str(trans['amount_sent']))
                self.input_queue.append(str(trans['amount_received']))
                self.input_queue.append(trans['payment_method'])
                self.input_queue.append(trans['notes'])
                
                # Si c'est une fin de cycle et que le bouclage est activé
                if 'cloture du cycle' in trans['notes'].lower() and self.scenario.get('loop_enabled'):
                    self.input_queue.append('o')  # Accepter le bouclage
        
        # Pour les débriefings de fin de cycle
        nb_cycles = self.scenario.get('nb_cycles', 1)
        for _ in range(nb_cycles):
            self.input_queue.append(f"Test cycle completed - Scenario {self.scenario['id']}")
        
        # Pour la clôture finale
        self.input_queue.append(f"Test completed - Scenario {self.scenario['id']}")
        
    def get_next_input(self):
        """Retourne le prochain input simulé"""
        if self.input_index < len(self.input_queue):
            value = self.input_queue[self.input_index]
            self.input_index += 1
            return value
        return ''
    
    def mock_input(self, prompt=''):
        """Fonction de remplacement pour input()"""
        next_input = self.get_next_input()
        print(f"[SIMULATED INPUT] {prompt}{next_input}")
        return next_input
    
    def apply_patches(self):
        """Applique les patches pour remplacer les inputs réels"""
        # Patch pour console.input (Rich)
        self.console_input_patch = patch('rich.console.Console.input', side_effect=self.mock_input)
        
        # Patch pour input() standard
        self.builtin_input_patch = patch('builtins.input', side_effect=self.mock_input)
        
        self.console_input_patch.start()
        self.builtin_input_patch.start()
    
    def remove_patches(self):
        """Retire les patches"""
        if hasattr(self, 'console_input_patch'):
            self.console_input_patch.stop()
        if hasattr(self, 'builtin_input_patch'):
            self.builtin_input_patch.stop()