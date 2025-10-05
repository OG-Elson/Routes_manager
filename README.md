# 📊 P2P Arbitrage Analysis System

> Un framework complet de simulation et d'analyse pour l'arbitrage P2P international

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-65%25%20coverage-yellow.svg)](tests/)

## 🎯 Vue d'ensemble

Système d'analyse quantitative pour identifier et simuler des opportunités d'arbitrage dans le trading P2P de cryptomonnaies. Développé pour optimiser les flux de trésorerie et minimiser les risques de change.

### Problème résolu

Le trading P2P international nécessite de jongler entre :
- Multiples devises fiat (EUR, XAF, RWF, KES...)
- Taux de change Forex volatils
- Frais de transaction variables
- Risques de contrepartie

Ce système calcule automatiquement la rentabilité de routes complexes sur plusieurs cycles.

## ✨ Fonctionnalités

- 🔍 **Moteur d'arbitrage** : Calcul de 20+ routes multi-devises en <1s
- 📝 **Suivi de transactions** : Logging structuré avec validation des inputs
- 📊 **KPI Analytics** : Rapports automatiques avec ROI, marges, graphiques
- 🔄 **Simulation** : Tests de scénarios avec 100+ paramètres
- 🧪 **Suite de tests** : 80+ tests unitaires et d'intégration

## 🚀 Quick Start

\`\`\`bash
# Installation
pip install -r requirements.txt

# Configuration
cp config.example.json config.json
# Éditer config.json avec vos marchés

# Lancer l'assistant interactif
python src/daily_briefing.py

# Simuler une rotation
python src/daily_briefing.py --simulation

# Générer les KPIs
python src/kpi_analyzer.py
\`\`\`

## 📐 Architecture

\`\`\`
┌─────────────────┐
│ Daily Briefing  │ ◄── Point d'entrée utilisateur
│  (Interface)    │
└────────┬────────┘
         │
    ┌────▼───────────────────┐
    │  Arbitrage Engine      │ ◄── Calculs financiers
    │  (Logique métier)      │
    └────────┬───────────────┘
             │
    ┌────────▼────────┐
    │  Rotation       │ ◄── État de session
    │  Manager        │
    └─────────────────┘
\`\`\`

### Modules clés

| Module | Responsabilité | LOC |
|--------|---------------|-----|
| `arbitrage_engine.py` | Calcul routes optimales | ~350 |
| `daily_briefing.py` | Interface utilisateur | ~600 |
| `kpi_analyzer.py` | Analyse de performance | ~400 |
| `simulation_module.py` | Tests automatisés | ~500 |

## 💡 Exemples d'utilisation

### Calculer la meilleure route

\`\`\`python
from src.arbitrage_engine import find_best_routes

routes = find_best_routes(top_n=5)
best = routes[0]

print(f"Route: {best['detailed_route']}")
print(f"Marge: {best['profit_pct']:.2f}%")
# Output: Route: EUR → USDT → XAF → EUR → USDT
#         Marge: 5.23%
\`\`\`

### Simuler 1000 scénarios

\`\`\`bash
python tests/test_simulation.py
# Génère 1000 rotations avec capitaux variés
# Temps d'exécution: ~45s
\`\`\`

## 🧪 Tests

\`\`\`bash
# Tests unitaires
python tests/test_unit.py

# Tests avancés
python tests/test_advanced.py

# Tests d'intégration
python tests/test_integration.py

# Tous les tests
pytest tests/ -v
\`\`\`

**Couverture actuelle** : 65% (objectif : 80%)

## 📊 Exemple de résultats

\`\`\`
Capital initial: 1,000 EUR
Route optimale: EUR → USDT → XAF → EUR (3 cycles)

Résultats après 30 jours :
├─ Capital final: 1,157 EUR
├─ Profit net: +157 EUR
├─ ROI: +15.7%
└─ Nb transactions: 27
\`\`\`

## 🛠️ Stack technique

- **Python 3.8+** : Langage principal
- **Pandas** : Manipulation de données
- **Rich** : Interface console
- **Pytest** : Framework de tests

## 📝 TODO / Roadmap

- [ ] Scraping automatique des prix Binance P2P
- [ ] Dashboard web (Flask + Chart.js)
- [ ] Backtesting sur données historiques
- [ ] API REST pour intégration externe

## 🤝 Contribution

Projet personnel à but pédagogique. Feedback bienvenu !

## 📄 License

License - Voir [LICENSE](LICENSE)

---

**Développé par OG_Elson** | [LinkedIn](#) | [Portfolio](#)
\`\`\`

### Ajouts obligatoires

1. **Captures d'écran** : Ajouter dans `docs/screenshots/`
   - Dashboard Rich console
   - Rapport KPI généré
   - Interface simulation

2. **LICENSE** : Ajouter fichier MIT

3. **.gitignore** :
```gitignore
# Configuration sensible
config.json
rotation_state.json

# Données opérationnelles
data/transactions.csv
data/debriefing.csv

# Environnement
venv/
__pycache__/
*.pyc

# Rapports de test
test_reports/