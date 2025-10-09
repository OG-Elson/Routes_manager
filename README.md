markdown# Routes Manager - Système d'Arbitrage P2P Crypto

Plateforme intelligente de gestion et d'optimisation de rotations d'arbitrage P2P avec support multi-devises et simulations avancées.
![Langage principal : Python](https://img.shields.io/github/languages/top/OG-Elson/Routes_manager)
![License : MIT](https://img.shields.io/github/license/OG-Elson/Routes_manager)

---

## 🎯 Proposition de Valeur

Ce projet est un moteur d'analyse et de simulation pour détecter les **opportunités d'arbitrage P2P** les plus rentables entre différentes plateformes et devises.

Développé en **Python**, il utilise des algorithmes de recherche de graphe (similaire à l'algorithme de Bellman-Ford ou Dijkstra, adapté au contexte des routes de conversion) pour identifier la séquence d'échanges optimale qui maximise le profit.

### ❓ Problématique Client
L'identification manuelle des opportunités d'arbitrage est chronophage, sujette aux erreurs de calcul (surtout avec la complexité des spreads) et ne permet pas d'optimiser le cycle complet.

### ✅ Solution
Routes Manager automatise la détection de routes, intègre une gestion rigoureuse des taux de change (Forex, Spreads bancaires) et simule des cycles de transactions complets pour fournir une mesure de rentabilité **nette et fiable**.

---

## ✨ Fonctionnalités Clés

La force du projet réside dans sa capacité à modéliser la complexité financière et à fournir une interface utilisateur claire via `rich`.

| Fonctionnalité | Description | Compétence Démontrée |
| :--- | :--- | :--- |
| **Recherche Optimale** | Identification des chemins de transaction les plus courts et les plus rentables pour boucler sur une devise source. |
| **Moteur de Taux Avancé** | Gestion précise des taux de change via **Bid/Ask** pour les taux de marché et intégration des **spreads** pour les conversions bancaires. | **Finance / Traitement de Données Critiques** |
| **Validation des Données** | Validation stricte des configurations (cohérence des spreads, taux négatifs ou nuls) pour garantir la fiabilité du calcul. | **Robustesse / Code Safety** |
| **Interface CLI Rich** | Expérience utilisateur améliorée avec des tableaux formatés et une saisie utilisateur robuste. | **Développement CLI Python Professionnel** |
| **Tests Unitaires** | Couverture complète des cas limites (extrême spread, formats de taux, NaN/Infinity) avec `pytest`. | **Qualité de Code et Maintenabilité** | devise de sourcing, exclusions, bouclage, méthode de conversion | **Filtres avancés** | test de rotations sans risque réel| **Mode simulation**| bouclage automatique sur devise choisie | **Gestion de cycles** | rapports détaillés de performance | **Analyse KPI** | détection d'incohérences dans la configuration | **Validation robuste** | **Interface CLI interactive** | avec Rich


---

## 🛠️ Stack Technique

* **Langage :** Python 3.10+
* **Librairies Principales :**
    * `rich` : Pour l'interface en ligne de commande (CLI) riche et l'affichage des résultats.
    * `pytest` : Pour la suite de tests unitaires et la validation des logiques complexes.
* **Architecture :** Modulaire (Engine, Utils, Modules), permettant une maintenance et une évolution faciles.

---



## 📋 Table des matières

- [Caractéristiques](#caractéristiques)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Fonctionnalités avancées](#fonctionnalités-avancées)
- [Modules](#modules)
- [Tests](#tests)
- [Sécurité](#sécurité)

---

## ✨ Caractéristiques

- **Calcul automatique des routes optimales** avec analyse de profitabilité
- **Support double méthode de conversion** : Forex (bid/ask) ou Banque (spread additionnel)


---

## 🏗️ Architecture
Routes_manager/
├── src/
│   ├── engine/              # Moteur d'arbitrage
│   │   ├── arbitrage_engine.py      # Calcul routes + validation
│   │   └── rotation_manager.py      # Gestion état rotations
│   ├── cli/                 # Interface utilisateur
│   │   └── daily_briefing.py        # Assistant principal
│   ├── modules/             # Modules complémentaires
│   │   ├── simulation_module.py     # Simulateur rotations
│   │   └── scenario_generator.py    # Générateur scénarios test
│   ├── utils/               # Utilitaires
│   │   └── route_params_collector.py # Collecte paramètres centralisée
│   └── analysis/            # Analyse données
│       └── kpi_analyzer.py          # Analyse performances
├── tests/                   # Tests unitaires/intégration
├── data/                    # Fichiers de données
├── security/                # Scripts sécurité
├── config.json              # Configuration principale
└── README.md

---

## 🚀 Installation

### Prérequis
- Python 3.9+
- pip

### Étapes
```bash
# Cloner le dépôt
git clone https://github.com/OG-Elson/Routes_manager.git
cd Routes_manager

# Installer les dépendances
pip install -r requirement.txt

# Configurer
cp config.example.json config.json
# Éditer config.json avec vos paramètres

⚙️ Configuration
Structure config.json
json{
  "markets": [
    {
      "currency": "EUR",
      "buy_price": 0.857,
      "sell_price": 0.851,
      "fee_pct": 0.1,
      "name": "Europe"
    },
    {
      "currency": "XAF",
      "buy_price": 595.86,
      "sell_price": 593.65,
      "fee_pct": 0.0,
      "name": "Afrique Centrale"
    }
  ],
  "forex_rates": {
    "XAF/EUR": {
      "bid": 650.0,
      "ask": 660.0,
      "bank_spread_pct": 1.5
    }
  },
  "default_conversion_method": "forex",
  "SEUIL_RENTABILITE_PCT": 1.5,
  "NB_CYCLES_PAR_ROTATION": 3
}
Format forex_rates
Nouveau format (recommandé) :
json"XAF/EUR": {
  "bid": 650.0,        // Taux si vous VENDEZ XAF contre EUR
  "ask": 660.0,        // Taux si vous ACHETEZ XAF contre EUR
  "bank_spread_pct": 1.5  // Spread bancaire additionnel
}
Ancien format (toujours supporté) :
json"XAF/EUR": 655.957
Méthodes de conversion
FOREX (marché) :

Utilise bid (vente) ou ask (achat) selon la direction
Spreads réels du marché

BANQUE :

Calcule taux mid : (bid + ask) / 2
Applique bank_spread_pct défavorable dans les deux sens
XAF→EUR : mid × (1 - spread%)
EUR→XAF : mid × (1 + spread%)


💻 Utilisation
Mode production (daily_briefing)
bashpython src/cli/daily_briefing.py
Fonctionnalités :

Planification nouvelle rotation (avec collecte paramètres interactive)
Log transactions (achat/vente/conversion/clôture)
Configuration devise de bouclage
Forçage transactions
Génération rapports KPI

Commandes :
bash# Logger une transaction
python src/cli/daily_briefing.py --log-achat
python src/cli/daily_briefing.py --log-vente
python src/cli/daily_briefing.py --log-conversion
python src/cli/daily_briefing.py --log-cloture

# Configurer devise de bouclage
python src/cli/daily_briefing.py --set-loop-currency XAF

# Forcer une transaction
python src/cli/daily_briefing.py --force-transaction VENTE
Mode simulation
bashpython src/cli/daily_briefing.py --simulation
Paramètres collectés interactivement :

Devise de sourcing (EUR, XAF, XOF, RWF, KES)
Capital initial
Nombre de cycles
Devise de bouclage (optionnel)
Marchés exclus (optionnel)
Méthode de conversion (forex / banque)

Résultats générés :

simulations/SIM_YYYYMMDD_HHMMSS/transactions.csv
simulations/SIM_YYYYMMDD_HHMMSS/plan_de_vol.json
simulations/SIM_YYYYMMDD_HHMMSS/simulation_config.json
simulations/SIM_YYYYMMDD_HHMMSS/simulation_report.txt


🎯 Fonctionnalités avancées
Filtres de routes
Le moteur d'arbitrage accepte des filtres pour affiner la recherche :
pythonfrom src.engine.arbitrage_engine import find_routes_with_filters

routes = find_routes_with_filters(
    top_n=5,
    apply_threshold=True,
    sourcing_currency='EUR',           # Forcer devise de départ
    excluded_markets=['RWF', 'KES'],   # Exclure comme marché de vente
    loop_currency='XAF',               # Priorité sur exclusions
    conversion_method='forex'          # 'forex' ou 'bank'
)
Bouclage de cycles
Configuration d'une devise de bouclage pour réinvestir automatiquement :
bashpython src/cli/daily_briefing.py --set-loop-currency XAF
Lorsque vous mettez "Cloture du Cycle N" dans les notes d'une transaction, le système propose de créer un nouveau cycle qui :

Commence par un ACHAT en XAF
Se termine par une CONVERSION vers XAF

Double cycle
Pour certaines devises, le moteur teste automatiquement un "double cycle" :

Vendre USDT en devise locale
Racheter USDT avec le produit de la vente
Continuer la rotation normale

Avantage : Optimise le capital investi en EUR.

📦 Modules
arbitrage_engine.py
Fonctions principales :

find_routes_with_filters() : Recherche routes avec filtres avancés
calculate_profit_route() : Calcul profitabilité d'une route
get_forex_rate() : Conversion avec méthode forex/banque
validate_config_coherence() : Validation configuration

route_params_collector.py
Centralisation collecte paramètres :

collect_route_search_parameters() : Paramètres recherche routes
collect_simulation_parameters() : Paramètres simulation complète

Gestion d'erreurs robuste :

Validation NaN/Infini
Détection valeurs vides
Option 'annuler' à tout moment
Gestion KeyboardInterrupt

rotation_manager.py
Gestion état rotations :

Sauvegarde atomique avec backup
Validation JSON + récupération fichiers corrompus
Historique transactions forcées (limite 100 entrées)
Statistiques rotations

kpi_analyzer.py
Analyse performances :

Calcul ROI, marges, profits
Rapports détaillés par rotation
Sauvegarde historique mensuel
Détection incohérences données


🧪 Tests
bash# Lancer tous les tests
python -m pytest tests/

# Tests spécifiques
python -m pytest tests/test_unit.py
python -m pytest tests/test_integration.py
python -m pytest tests/test_simulation.py
python -m pytest tests/test_advanced.py
Couverture :

Tests unitaires (fonctions isolées)
Tests d'intégration (modules combinés)
Tests simulation (scénarios complets)
Tests avancés (edge cases, erreurs)


🔒 Sécurité
Scripts disponibles
bash# Audit sécurité
bash security/security_audit.sh

# Durcissement système
bash security/security_harden.sh
Bonnes pratiques

Ne JAMAIS commiter config.json avec vraies données
Utiliser config.example.json comme template
Ajouter fichiers sensibles dans .gitignore
Vérifier permissions fichiers (chmod 600 config.json)


📊 Exemple de workflow complet
bash# 1. Configuration initiale
cp config.example.json config.json
vim config.json  # Éditer avec vos marchés/taux

# 2. Simulation test
python src/cli/daily_briefing.py --simulation
# Choisir : EUR, 1000€, 2 cycles, XAF bouclage, forex

# 3. Vérifier résultats
cat simulations/SIM_*/simulation_report.txt

# 4. Planifier rotation réelle
python src/cli/daily_briefing.py
# Choisir route, méthode conversion

# 5. Logger transactions
python src/cli/daily_briefing.py --log-achat
python src/cli/daily_briefing.py --log-vente
python src/cli/daily_briefing.py --log-conversion

# 6. Analyser performances
python src/analysis/kpi_analyzer.py

🤝 Contribution
Les contributions sont les bienvenues. Veuillez :

Fork le projet
Créer une branche feature (git checkout -b feature/AmazingFeature)
Commit vos changements (git commit -m 'Add AmazingFeature')
Push vers la branche (git push origin feature/AmazingFeature)
Ouvrir une Pull Request


📝 License
Ce projet est sous license MIT - voir le fichier LICENSE pour détails.

📞 Support
Pour toute question ou problème :

Ouvrir une issue sur GitHub
Consulter la documentation dans /docs (si disponible)


🗓️ Roadmap

 Interface web (Dashboard)
 Support multi-utilisateurs
 API REST
 Alertes temps réel (Telegram/Email)
 ML pour prédiction marges
 Support plus de 10 devises
 Mode backtest historique
