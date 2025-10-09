"""Script de correction automatique des indentations."""
import sys
from pathlib import Path

def fix_indentation(filepath, project_root, tab_size=4):
    """
    Corrige l'indentation d'un fichier Python.
    Convertit tous les tabs en espaces et normalise l'indentation.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            return True

        fixed_lines = []
        for line in lines:
            # Remplacer tabs par espaces
            # 1 tab = tab_size espaces
            fixed_line = line.expandtabs(tab_size)
            fixed_lines.append(fixed_line)

        # Écrire les modifications
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)

        relative = filepath.relative_to(project_root)
        print(f"✅ {relative}")
        return True

    except UnicodeDecodeError:
        relative = filepath.relative_to(project_root)
        print(f"⏭️  {relative} (encodage non-UTF8, ignoré)")
        return True

    except Exception as e:
        relative = filepath.relative_to(project_root)
        print(f"❌ {relative}: {e}")
        return False

def should_exclude(filepath, project_root):
    """Détermine si un fichier doit être exclu."""
    relative_path = filepath.relative_to(project_root)

    # Dossiers à exclure
    excluded_dirs = {
        '.git', '.vscode', '__pycache__', '.pytest_cache',
        'venv', 'env', '.venv', 'simulations', 'htmlcov',
        '.mypy_cache', '.tox', 'build', 'dist'
    }

    for part in relative_path.parts:
        if part in excluded_dirs or part.startswith('.'):
            return True

    return False

def main():
    """Corrige l'indentation de tous les fichiers Python."""
    project_root = Path.cwd()

    print("=" * 60)
    print("🔧 CORRECTION DES INDENTATIONS")
    print("=" * 60)
    print(f"📁 Racine du projet: {project_root}")
    print(f"🔹 Taille tab: 4 espaces")
    print()

    # Collecter tous les fichiers Python
    print("🔍 Recherche des fichiers Python...")
    all_python_files = list(project_root.rglob('*.py'))

    # Filtrer les fichiers exclus
    python_files = [
        f for f in all_python_files
        if not should_exclude(f, project_root)
    ]

    excluded_count = len(all_python_files) - len(python_files)

    print(f"📊 Statistiques:")
    print(f"   • Total trouvés: {len(all_python_files)} fichiers")
    print(f"   • Exclus: {excluded_count} fichiers")
    print(f"   • À traiter: {len(python_files)} fichiers")
    print()

    if not python_files:
        print("⚠️  Aucun fichier Python à traiter")
        sys.exit(0)

    # Organiser par dossier
    files_by_dir = {}
    for file in python_files:
        parent = file.parent.relative_to(project_root)
        if parent not in files_by_dir:
            files_by_dir[parent] = []
        files_by_dir[parent].append(file)

    # Corriger fichier par fichier
    print("🚀 Correction en cours...\n")

    success = 0
    failed = 0

    for directory in sorted(files_by_dir.keys()):
        print(f"📂 {directory}/")
        for file in sorted(files_by_dir[directory]):
            if fix_indentation(file, project_root):
                success += 1
            else:
                failed += 1
        print()

    # Résumé
    print("=" * 60)
    print(f"✅ {success} fichiers corrigés")
    if failed:
        print(f"❌ {failed} fichiers en erreur")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 Toutes les indentations ont été corrigées !")
        print("\n📋 Prochaines étapes:")
        print("   1. pytest            # Tester que rien n'est cassé")
        print("   2. git diff          # Vérifier les changements")
        print("   3. git add .         # Ajouter les changements")
        print("   4. git commit -m 'fix: correction indentations'")
    else:
        print(f"\n⚠️  {failed} fichiers ont échoué")
        sys.exit(1)

if __name__ == '__main__':
    main()

