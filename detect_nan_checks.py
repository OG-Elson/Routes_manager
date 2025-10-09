"""Détecte les vérifications NaN dans le code."""
from pathlib import Path
import re

def detect_nan_checks(filepath):
    """Détecte les patterns 'variable != variable'."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    found = []
    for i, line in enumerate(lines, 1):
        # Pattern flexible : variable != variable (avec ou sans espaces)
        # Chercher tous les mots répétés avec !=
        matches = re.findall(r'\b(\w+)\s*!=\s*\1\b', line)
        if matches:
            found.append((i, line.rstrip(), matches))
    
    return found

def main():
    """Détecte dans tous les fichiers."""
    print("=" * 70)
    print("🔍 DÉTECTION DES VÉRIFICATIONS NaN")
    print("=" * 70)
    print()
    
    files = [
        'src/cli/daily_briefing.py',
        'src/modules/simulation_module.py',
        'src/engine/arbitrage_engine.py'
    ]
    
    total_found = 0
    
    for filepath in files:
        p = Path(filepath)
        if p.exists():
            results = detect_nan_checks(p)
            if results:
                print(f"📄 {filepath}")
                for line_num, line_content, variables in results:
                    print(f"   Ligne {line_num:4d}: {line_content}")
                    print(f"             Variables: {', '.join(variables)}")
                print()
                total_found += len(results)
            else:
                print(f"⏭️  {filepath} - Aucun pattern trouvé")
        else:
            print(f"❌ {filepath} - Fichier introuvable")
    
    print()
    print("=" * 70)
    print(f"🔍 Total: {total_found} vérifications NaN détectées")
    print("=" * 70)

if __name__ == '__main__':
    main()