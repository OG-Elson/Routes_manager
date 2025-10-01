# Système d'Arbitrage P2P

Système de trading P2P avec simulation de rotations complètes.

## Installation

1. Cloner le dépôt
2. Copier `config.example.json` en `config.json` et remplir vos valeurs
3. Installer les dépendances : `pip install pandas rich`

## Utilisation
```bash
# Mode planification/exécution normale
python daily_briefing_bis.py

# Lancer une simulation
python daily_briefing_bis.py --simulation

# Logger des transactions
python daily_briefing_bis.py --log-achat
python daily_briefing_bis.py --log-vente
python daily_briefing_bis.py --log-conversion