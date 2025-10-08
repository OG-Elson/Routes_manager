"""
Tests unitaires pour rotation_manager
Focus sur gestion état rotations
"""
import json
from pathlib import Path

import pytest

from src.engine.rotation_manager import RotationManager


class TestRotationManagerInit:
    """Tests initialisation et création rotations"""
    
    def test_init_rotation_creates_entry(self, tmp_path, monkeypatch):
        """init_rotation() crée entrée dans state"""
        # Utiliser tmp_path pour state file
        state_file = tmp_path / "rotation_state.json"
        
        # Monkeypatch le chemin du fichier
        monkeypatch.setattr('src.engine.rotation_manager.ROTATION_STATE_FILE', str(state_file))
        
        manager = RotationManager()
        manager.init_rotation("R20250101-1")
        
        # Vérifier que le fichier existe
        assert state_file.exists()
        
        # Vérifier contenu
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        assert "R20250101-1" in state['active_rotations']
        assert state['active_rotations']["R20250101-1"]['current_cycle'] == 1
    
    def test_increment_cycle(self, tmp_path, monkeypatch):
        """increment_cycle() augmente compteur"""
        state_file = tmp_path / "rotation_state.json"
        monkeypatch.setattr('src.engine.rotation_manager.ROTATION_STATE_FILE', str(state_file))
        
        manager = RotationManager()
        manager.init_rotation("R20250101-1")
        manager.increment_cycle("R20250101-1")
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        assert state['active_rotations']["R20250101-1"]['current_cycle'] == 2
    
    def test_set_loop_currency(self, tmp_path, monkeypatch):
        """set_loop_currency() enregistre devise"""
        state_file = tmp_path / "rotation_state.json"
        monkeypatch.setattr('src.engine.rotation_manager.ROTATION_STATE_FILE', str(state_file))
        
        manager = RotationManager()
        manager.init_rotation("R20250101-1")
        manager.set_loop_currency("R20250101-1", "XAF")
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        assert state['active_rotations']["R20250101-1"]['loop_currency'] == "XAF"
    
    def test_get_loop_currency(self, tmp_path, monkeypatch):
        """get_loop_currency() récupère devise"""
        state_file = tmp_path / "rotation_state.json"
        monkeypatch.setattr('src.engine.rotation_manager.ROTATION_STATE_FILE', str(state_file))
        
        manager = RotationManager()
        manager.init_rotation("R20250101-1")
        manager.set_loop_currency("R20250101-1", "XAF")
        
        loop_curr = manager.get_loop_currency("R20250101-1")
        assert loop_curr == "XAF"


class TestRotationManagerRecovery:
    """Tests récupération erreurs"""
    
    def test_corrupted_json_recovers_from_backup(self, tmp_path, monkeypatch):
        """JSON corrompu restaure backup"""
        state_file = tmp_path / "rotation_state.json"
        backup_file = tmp_path / "rotation_state.json.backup"
        
        monkeypatch.setattr('src.engine.rotation_manager.ROTATION_STATE_FILE', str(state_file))
        
        # Créer backup valide
        valid_state = {
            "active_rotations": {
                "R20250101-1": {"current_cycle": 1}
            }
        }
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(valid_state, f)
        
        # Créer fichier principal corrompu
        with open(state_file, 'w', encoding='utf-8') as f:
            f.write("{invalid json")
        
        # Manager devrait restaurer depuis backup
        manager = RotationManager()
        
        # Vérifier que le state est valide
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        assert "R20250101-1" in state['active_rotations']
    
    def test_missing_file_creates_new(self, tmp_path, monkeypatch):
        """Fichier manquant crée nouveau state"""
        state_file = tmp_path / "rotation_state.json"
        monkeypatch.setattr('src.engine.rotation_manager.ROTATION_STATE_FILE', str(state_file))
        
        # S'assurer que le fichier n'existe pas
        if state_file.exists():
            state_file.unlink()
        
        manager = RotationManager()
        manager.init_rotation("R20250101-1")
        
        assert state_file.exists()


class TestRotationManagerForcedTransactions:
    """Tests historique transactions forcées"""
    
    def test_record_forced_transaction(self, tmp_path, monkeypatch):
        """record_forced_transaction() enregistre"""
        state_file = tmp_path / "rotation_state.json"
        monkeypatch.setattr('src.engine.rotation_manager.ROTATION_STATE_FILE', str(state_file))
        
        manager = RotationManager()
        manager.init_rotation("R20250101-1")
        manager.record_forced_transaction("R20250101-1", "VENTE", "Opportunité marché")
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        forced = state['active_rotations']["R20250101-1"]['forced_transactions']
        assert len(forced) == 1
        assert forced[0]['type'] == "VENTE"
        assert forced[0]['reason'] == "Opportunité marché"
    
    def test_forced_transactions_limit_100(self, tmp_path, monkeypatch):
        """Historique forced_transactions limité à 100"""
        state_file = tmp_path / "rotation_state.json"
        monkeypatch.setattr('src.engine.rotation_manager.ROTATION_STATE_FILE', str(state_file))
        
        manager = RotationManager()
        manager.init_rotation("R20250101-1")
        
        # Ajouter 150 transactions
        for i in range(150):
            manager.record_forced_transaction("R20250101-1", "VENTE", f"Raison {i}")
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        forced = state['active_rotations']["R20250101-1"]['forced_transactions']
        # Doit être limité à 100
        assert len(forced) <= 100


class TestRotationManagerStats:
    """Tests statistiques rotations"""
    
    def test_get_rotation_stats(self, tmp_path, monkeypatch):
        """get_rotation_stats() retourne stats valides"""
        state_file = tmp_path / "rotation_state.json"
        monkeypatch.setattr('src.engine.rotation_manager.ROTATION_STATE_FILE', str(state_file))
        
        manager = RotationManager()
        manager.init_rotation("R20250101-1")
        manager.increment_cycle("R20250101-1")
        manager.set_loop_currency("R20250101-1", "XAF")
        
        stats = manager.get_rotation_stats("R20250101-1")
        
        assert stats is not None
        assert stats['current_cycle'] == 2
        assert stats['loop_currency'] == "XAF"