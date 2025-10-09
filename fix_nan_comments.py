"""Ajoute des commentaires pylint pour les vérifications NaN intentionnelles."""
from pathlib import Path
import re

def fix_nan_check_comments(filepath):
    """Ajoute commentaire pylint pour les checks NaN."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    
    for line in lines:
        # Détecter pattern: if variable != variable:
        # avec un commentaire explicatif
        pattern = r'^(\s+)if\s+(\w+)\s*!=\s*\2\s*:\s*$'
        match = re.match(pattern, line)
        
        if match:
            indent = match.group(1)
            var = match.group(2)
            
            # Ajouter commentaire avant la ligne
            comment = f"{indent}# Vérification NaN : NaN != NaN retourne True\n"
            new_lines.append(comment)
            
            # Ajouter directive pylint à la fin de la ligne
            line = line.rstrip() + "  # pylint: disable=comparison-with-itself\n"
            modified = True
        
        new_lines.append(line)
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    
    return False

def main():
    """Ajoute commentaires sur tous les fichiers concernés."""
    print("=" * 70)
    print("🔧 AJOUT COMMENTAIRES POUR VÉRIFICATIONS NaN")
    print("=" * 70)
    print()
    
    files = [
        'src/cli/daily_briefing.py',        # Lignes 82, 99
        'src/modules/simulation_module.py',  # Lignes 68, 91
        'src/engine/arbitrage_engine.py'    # Ligne 165
    ]
    
    fixed = 0
    for filepath in files:
        p = Path(filepath)
        if p.exists():
            if fix_nan_check_comments(p):
                print(f"✅ {filepath} - Commentaires ajoutés")
                fixed += 1
            else:
                print(f"⏭️  {filepath} - Aucun pattern trouvé")
        else:
            print(f"❌ {filepath} - Fichier introuvable")
    
    print()
    print("=" * 70)
    print(f"✅ {fixed} fichiers modifiés")
    print("=" * 70)
    print("\n💡 Les vérifications 'num != num' sont CORRECTES pour détecter NaN")
    print("   Commentaires ajoutés pour clarifier et désactiver le warning Pylint")
    print("\n📋 Prochaines étapes:")
    print("   1. pytest")
    print("   2. git diff          # Vérifier les commentaires ajoutés")
    print("   3. git add . && git commit")

if __name__ == '__main__':
    main()