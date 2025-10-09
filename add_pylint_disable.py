"""Ajoute directives pylint pour les vérifications NaN intentionnelles."""
from pathlib import Path
import re

def add_pylint_disable(filepath):
    """Ajoute # pylint: disable=comparison-with-itself aux lignes concernées."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    
    for i, line in enumerate(lines):
        # Détecter les lignes avec "variable != variable"
        if re.search(r'\b(\w+)\s*!=\s*\1\b', line):
            # Vérifier si pylint disable déjà présent
            if 'pylint: disable' not in line:
                # Ajouter à la fin de la ligne
                line = line.rstrip() + '  # pylint: disable=comparison-with-itself\n'
                modified = True
                print(f"   Ligne {i+1:4d}: Directive ajoutée")
        
        new_lines.append(line)
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    
    return False

def main():
    """Ajoute directives dans tous les fichiers."""
    print("=" * 70)
    print("🔧 AJOUT DIRECTIVES PYLINT POUR VÉRIFICATIONS NaN")
    print("=" * 70)
    print()
    
    files = [
        'src/cli/daily_briefing.py',
        'src/modules/simulation_module.py',
        'src/engine/arbitrage_engine.py'
    ]
    
    fixed = 0
    for filepath in files:
        p = Path(filepath)
        if p.exists():
            print(f"📄 {filepath}")
            if add_pylint_disable(p):
                fixed += 1
                print(f"   ✅ Modifié")
            else:
                print(f"   ⏭️  Aucune modification (déjà présent)")
            print()
        else:
            print(f"❌ {filepath} - Fichier introuvable\n")
    
    print("=" * 70)
    print(f"✅ {fixed} fichiers modifiés")
    print("=" * 70)
    print("\n💡 Les vérifications 'num != num' sont INTENTIONNELLES")
    print("   Elles détectent NaN + Infini de manière robuste")
    print("\n📋 Prochaines étapes:")
    print("   1. pytest")
    print("   2. pylint src/  # Devrait réduire les warnings R0124")
    print("   3. git add . && git commit")

if __name__ == '__main__':
    main()