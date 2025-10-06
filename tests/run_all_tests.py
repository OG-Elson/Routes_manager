"""
Script principal pour exécuter tous les tests avec rapport détaillé
Génère un rapport HTML et affiche résumé en console
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_tests_with_coverage():
    """Execute tous les tests avec couverture et génération rapports"""
    
    print("=" * 70)
    print("LANCEMENT DE LA SUITE COMPLÈTE DE TESTS")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    

    # Chemins
    project_root = Path(__file__).parent.parent
    reports_dir = project_root / "test_reports"
    
    # Créer dossier rapports s'il n'existe pas
    reports_dir.mkdir(exist_ok=True)
    
    # Timestamp pour nommage unique
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S') 
    # Commande pytest avec tous les plugins
    cmd = [
        "pytest",
        "-v",                                    # Verbose
        "--tb=short",                            # Traceback court
        "--color=yes",                           # Couleurs
        f"--html={reports_dir}/test_report_{timestamp}.html", # Rapport HTML
        "--self-contained-html",                 # HTML autonome
        "--cov=src",                             # Couverture src/
        f"--cov-report=html:{reports_dir}/htmlcov_{timestamp}", # Rapport couverture HTML
        "--cov-report=term-missing",             # Afficher lignes manquantes
        "--durations=10",                        # 10 tests les plus lents
        #"-x",                                    # Arrêter au premier échec (optionnel)
        str(project_root / "tests")              # Dossier tests
    ]
    
    # Retirer -x si vous voulez continuer malgré les échecs
    # cmd.remove("-x")
    
    print("Commande exécutée:")
    print(" ".join(cmd))
    print("\n" + "=" * 70 + "\n")
    
    # Exécuter pytest
    result = subprocess.run(cmd, cwd=project_root)
    
    print("\n" + "=" * 70)
    print("TESTS TERMINÉS")
    print("=" * 70)
    print(f"\nRapport HTML : {reports_dir}/test_report_{timestamp}.html")
    print(f"Couverture   : {reports_dir}/htmlcov_{timestamp}/index.html")
    
    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests_with_coverage()
    sys.exit(exit_code)