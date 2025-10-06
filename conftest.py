"""
Configuration pytest - Racine du projet
Ajoute le répertoire projet au sys.path
"""
import sys
from pathlib import Path

# Ajouter racine projet au path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))