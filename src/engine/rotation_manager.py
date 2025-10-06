# rotation_manager.py - VERSION CORRIGÉE

import json
import os
import logging
import shutil
from datetime import datetime

ROTATION_STATE_FILE = 'rotation_state.json'
BACKUP_FILE = ROTATION_STATE_FILE + '.bak' # <- NOUVELLE CONSTANTE
class RotationManager:
    """Gestionnaire pour choisir la devise de bouclage de cycle"""
    
    def __init__(self):
        self.state = self.load_state()

    def _load_from_backup(self):
            """Tente de charger un état valide à partir du fichier de backup."""
            if os.path.exists(BACKUP_FILE):
                try:
                    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    
                    if not isinstance(state, dict) or 'active_rotations' not in state:
                        logging.error("Fichier de backup mal formé. Création d'un nouvel état.")
                        return {"active_rotations": {}}

                    # Restaurer le fichier principal à partir du backup (.bak -> .json)
                    shutil.copy2(BACKUP_FILE, ROTATION_STATE_FILE)
                    logging.info(f"État restauré avec succès à partir de {BACKUP_FILE}")
                    return state
                    
                except (json.JSONDecodeError, Exception) as e:
                    logging.error(f"Erreur lors du chargement ou de la restauration du backup: {e}")
                    # Le backup est corrompu, on le supprime
                    try:
                        os.remove(BACKUP_FILE)
                        logging.warning(f"{BACKUP_FILE} corrompu et supprimé.")
                    except:
                        pass
                    return {"active_rotations": {}}
            
            logging.warning("Aucun fichier de backup valide trouvé.")
            return {"active_rotations": {}}
    
    def load_state(self):
        """✅ CORRECTION : Validation du JSON"""
        if os.path.exists(ROTATION_STATE_FILE):
            try:
                with open(ROTATION_STATE_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    
                    if not content:
                        logging.warning("rotation_state.json vide, création d'un nouvel état")
                        return {"active_rotations": {}}
                    
                    state = json.loads(content)
                    
                    if not isinstance(state, dict):
                        logging.error("rotation_state.json mal formé (pas un dict)")
                        return {"active_rotations": {}}
                    
                    if 'active_rotations' not in state:
                        logging.warning("Clé 'active_rotations' manquante, ajout")
                        state['active_rotations'] = {}
                    
                    return state  # ← Return du state valide
                    
            except json.JSONDecodeError as e:
                logging.error(f"JSON corrompu dans {ROTATION_STATE_FILE}: {e}")
                backup_name = f"{ROTATION_STATE_FILE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    os.rename(ROTATION_STATE_FILE, backup_name)
                    logging.info(f"Fichier corrompu sauvegardé sous {backup_name}")
                except:
                    pass
                
                new_state = {"active_rotations": {}}
                try:
                    with open(ROTATION_STATE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(new_state, f, indent=2, ensure_ascii=False)
                    logging.info(f"Nouveau {ROTATION_STATE_FILE} créé")
                except Exception as write_error:
                    logging.error(f"Échec création nouveau fichier: {write_error}")
                
                return new_state
            
            except Exception as e:
                logging.error(f"Erreur lecture {ROTATION_STATE_FILE}: {e}")
                return {"active_rotations": {}}
        
        # ← Si fichier n'existe PAS (en dehors du if)
        return {"active_rotations": {}}
    
    def save_state(self):
        """✅ AMÉLIORATION : Sauvegarde atomique avec backup"""
        temp_file = f"{ROTATION_STATE_FILE}.tmp"
        backup_file = f"{ROTATION_STATE_FILE}.backup"
        
        try:
            # Écrire dans un fichier temporaire
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            
            # Backup de l'ancien fichier si il existe
            if os.path.exists(ROTATION_STATE_FILE):
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(ROTATION_STATE_FILE, backup_file)
            
            # Renommer le fichier temporaire
            os.rename(temp_file, ROTATION_STATE_FILE)
            
            # Nettoyer le backup après succès
            if os.path.exists(backup_file):
                os.remove(backup_file)
            
            return True
            
        except Exception as e:
            logging.error(f"Erreur sauvegarde état: {e}")
            
            # Restaurer le backup en cas d'échec
            if os.path.exists(backup_file):
                if os.path.exists(ROTATION_STATE_FILE):
                    os.remove(ROTATION_STATE_FILE)
                os.rename(backup_file, ROTATION_STATE_FILE)
            
            # Nettoyer le fichier temporaire
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            return False
    
    def init_rotation(self, rotation_id):
        """✅ AJOUT : Validation de l'ID de rotation"""
        if not rotation_id or not isinstance(rotation_id, str):
            logging.error(f"ID de rotation invalide: {rotation_id}")
            return False
        
        self.state['active_rotations'][rotation_id] = {
            "rotation_id": rotation_id,
            'current_cycle': 1,
            "loop_currency": None,
            "forced_transactions": [],
            "created_at": datetime.now().isoformat()
        }
        return self.save_state()
    
    def get_rotation(self, rotation_id):
        return self.state['active_rotations'].get(rotation_id)
    
    def set_loop_currency(self, rotation_id, currency):
        """Définit la devise sur laquelle on veut boucler"""
        if rotation_id not in self.state['active_rotations']:
            if not self.init_rotation(rotation_id):
                return False
        
        # ✅ AJOUT : Validation de la devise
        if not currency or not isinstance(currency, str):
            logging.error(f"Devise invalide: {currency}")
            return False
        
        self.state['active_rotations'][rotation_id]['loop_currency'] = currency.upper()
        self.state['active_rotations'][rotation_id]['loop_currency_set_at'] = datetime.now().isoformat()
        
        return self.save_state()
    
    def get_loop_currency(self, rotation_id):
        """Récupère la devise de bouclage"""
        rotation = self.get_rotation(rotation_id)
        if rotation:
            return rotation.get('loop_currency')
        return None
    
    def increment_cycle(self, rotation_id):
        """✅ AMÉLIORATION : Retourne le nombre de cycles"""
        if rotation_id in self.state['active_rotations']:
            self.state['active_rotations'][rotation_id]['current_cycle'] += 1
            cycles = self.state['active_rotations'][rotation_id]['current_cycle']  # ← LIRE current
            
            if self.save_state():
                logging.info(f"Rotation {rotation_id}: {cycles} cycles complétés")
                return cycles
        
        return 0
    
    def record_forced_transaction(self, rotation_id, trans_type, reason):
        """✅ AMÉLIORATION : Validation + limite d'historique"""
        if rotation_id not in self.state['active_rotations']:
            if not self.init_rotation(rotation_id):
                return False
        
        forced_record = {
            "type": trans_type,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        self.state['active_rotations'][rotation_id]['forced_transactions'].append(forced_record)
        
        # ✅ AJOUT : Limiter l'historique à 100 entrées max
        if len(self.state['active_rotations'][rotation_id]['forced_transactions']) > 100:
            self.state['active_rotations'][rotation_id]['forced_transactions'] = \
                self.state['active_rotations'][rotation_id]['forced_transactions'][-100:]
        
        return self.save_state()
    
    def get_rotation_stats(self, rotation_id):
        """✅ NOUVELLE FONCTION : Obtenir les stats d'une rotation"""
        rotation = self.get_rotation(rotation_id)
        if not rotation:
            return None
        
        return {
            'current_cycle': rotation.get('current_cycle', 1),  # ← AJOUTER
            'cycles_completed': rotation.get('current_cycle', 1) - 1,
            'loop_currency': rotation.get('loop_currency'),
            'forced_transactions_count': len(rotation.get('forced_transactions', [])),
            'created_at': rotation.get('created_at'),
            'loop_currency_set_at': rotation.get('loop_currency_set_at')
        }