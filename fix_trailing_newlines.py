"""Supprime les newlines multiples en fin de fichier."""
from pathlib import Path

# Fichiers concernés (selon pylint)
files = [
    'src/analysis/kpi_analyzer.py',       # Ligne 510
    'src/cli/daily_briefing.py',          # Ligne 930
    'src/engine/arbitrage_engine.py',     # Ligne 590
    'src/engine/rotation_manager.py',     # Ligne 221
    'src/modules/scenario_generator.py',  # Ligne 381
    'src/modules/simulation_module.py'    # Ligne 595
]

for filepath in files:
    p = Path(filepath)
    if p.exists():
        # Lire le contenu
        content = p.read_text(encoding='utf-8')
        
        # Supprimer tous les espaces/newlines en fin
        content = content.rstrip()
        
        # Ajouter UNE SEULE newline finale
        content += '\n'
        
        # Écrire
        p.write_text(content, encoding='utf-8')
        print(f'✅ {filepath}')
    else:
        print(f'❌ {filepath} (introuvable)')