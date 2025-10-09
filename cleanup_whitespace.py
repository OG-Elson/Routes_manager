"""Script de nettoyage automatique des espaces pour tout le projet."""
import sys
from pathlib import Path

def get_project_root():
    """Trouve la racine du projet à partir du dossier courant."""
    current = Path.cwd()

    # Vérifier si on est déjà à la racine (présence de src/ ou .git/)
    if (current / 'src').exists() or (current / '.git').exists():
        return current

    # Sinon, remonter les dossiers parents
    while current != current.parent:
        if (current / 'src').exists() or (current / '.git').exists():
            return current
        current = current.parent

    return Path.cwd()

def should_exclude(filepath, project_root):
    """Détermine si un fichier doit être exclu du nettoyage."""
    relative_path = filepath.relative_to(project_root)

    # Dossiers à exclure
    excluded_dirs = {
        '.git',
        '.vscode',
        '__pycache__',
        '.pytest_cache',
        'venv',
        'env',
        '.venv',
        'simulations',
        'htmlcov',
        '.mypy_cache',
        '.tox',
        'build',
        'dist',
        '*.egg-info'
    }

    # Vérifier si le fichier est dans un dossier exclu
    for part in relative_path.parts:
        if part in excluded_dirs or part.startswith('.'):
            return True

    # Fichiers à exclure
    excluded_files = {
        'test_report_*.html',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.DS_Store',
        'Thumbs.db'
    }

    for pattern in excluded_files:
        if filepath.match(pattern):
            return True

    return False

def clean_file(filepath, project_root):
    """Nettoie un fichier Python."""
    try:
        # Lire le fichier
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Si fichier vide, ne rien faire
        if not lines:
            return True

        # Supprimer trailing whitespace sur chaque ligne
        cleaned_lines = [line.rstrip() + '\n' for line in lines]

        # Supprimer les lignes vides multiples en fin de fichier
        while len(cleaned_lines) > 1 and cleaned_lines[-1].strip() == '':
            cleaned_lines.pop()

        # Assurer UNE newline finale
        if cleaned_lines:
            if cleaned_lines[-1].strip():  # Dernière ligne non vide
                cleaned_lines.append('\n')
            elif not cleaned_lines[-1].endswith('\n'):
                cleaned_lines[-1] += '\n'

        # Écrire les modifications
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)

        # Affichage relatif au projet
        relative = filepath.relative_to(project_root)
        print(f"✅ {relative}")
        return True

    except UnicodeDecodeError:
        # Fichier binaire ou encodage non-UTF8
        relative = filepath.relative_to(project_root)
        print(f"⏭️  {relative} (encodage non-UTF8, ignoré)")
        return True

    except Exception as e:
        relative = filepath.relative_to(project_root)
        print(f"❌ {relative}: {e}")
        return False

def main():
    """Nettoie tous les fichiers Python du projet."""
    project_root = get_project_root()

    print("=" * 60)
    print("🧹 NETTOYAGE COMPLET DU PROJET")
    print("=" * 60)
    print(f"📁 Dossier de travail: {Path.cwd()}")
    print(f"📁 Racine du projet: {project_root}")
    print()

    # Collecter tous les fichiers Python
    print("🔍 Recherche de tous les fichiers Python...")
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

    # Organiser par dossier pour affichage
    files_by_dir = {}
    for file in python_files:
        parent = file.parent.relative_to(project_root)
        if parent not in files_by_dir:
            files_by_dir[parent] = []
        files_by_dir[parent].append(file)

    # Nettoyer fichier par fichier
    print("🚀 Nettoyage en cours...\n")

    success = 0
    failed = 0

    for directory in sorted(files_by_dir.keys()):
        print(f"📂 {directory}/")
        for file in sorted(files_by_dir[directory]):
            if clean_file(file, project_root):
                success += 1
            else:
                failed += 1
        print()

    # Résumé
    print("=" * 60)
    print(f"✅ {success} fichiers nettoyés avec succès")
    if failed:
        print(f"❌ {failed} fichiers en erreur")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 Tous les fichiers ont été nettoyés avec succès !")
        print("\n📋 Prochaines étapes:")
        print("   1. git diff          # Vérifier les changements")
        print("   2. pytest            # Tester que rien n'est cassé")
        print("   3. git add .         # Ajouter les changements")
        print("   4. git commit -m '...'  # Commiter")
    else:
        print(f"\n⚠️  {failed} fichiers ont échoué")
        sys.exit(1)

if __name__ == '__main__':
    main()

