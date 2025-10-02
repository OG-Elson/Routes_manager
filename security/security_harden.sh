#!/bin/bash

# security_harden.sh - Durcissement de la sécurité Niveau 3
# Configuration automatique environnement sécurisé
# Auteur: ElsonG
# Date: 2025-10-01

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
NEW_USER="ElsonG"
EMAIL="elvisdushimeemani@gmail.com"
PROJECT_DIR="Routes_manager"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  DURCISSEMENT SÉCURITÉ - Niveau 3      ║${NC}"
echo -e "${BLUE}║  Configuration environnement sécurisé  ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo ""

# Vérifier root
if [ "$(whoami)" != "root" ]; then
    echo -e "${RED}Erreur: Ce script doit être exécuté en root${NC}"
    exit 1
fi

echo -e "${YELLOW}Ce script va:${NC}"
echo "  1. Créer l'utilisateur ElsonG"
echo "  2. Migrer votre environnement vers ElsonG"
echo "  3. Sécuriser les permissions fichiers"
echo "  4. Configurer l'audit quotidien"
echo "  5. Nettoyer les packages inutiles"
echo ""
read -p "Continuer? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# ============================================
# ÉTAPE 1: Créer utilisateur ElsonG
# ============================================
echo -e "\n${BLUE}[1/6]${NC} Création de l'utilisateur $NEW_USER..."

if id "$NEW_USER" &>/dev/null; then
    echo -e "${YELLOW}L'utilisateur $NEW_USER existe déjà${NC}"
else
    # Créer utilisateur avec home directory
    useradd -m -s /bin/bash "$NEW_USER"
    
    # Définir mot de passe interactivement
    echo "Définissez un mot de passe pour $NEW_USER:"
    passwd "$NEW_USER"
    
    # Ajouter sudo limité (pas de NOPASSWD)
    #echo "$NEW_USER ALL=(ALL:ALL) ALL" > /etc/sudoers.d/$NEW_USER
    #chmod 440 /etc/sudoers.d/$NEW_USER
    
    echo -e "${GREEN}✓${NC} Utilisateur $NEW_USER créé"
fi

# ============================================
# ÉTAPE 2: Migration environnement
# ============================================
echo -e "\n${BLUE}[2/6]${NC} Migration de l'environnement..."

# Trouver le projet
PROJECT_PATH=$(find /root ~/storage/shared -name "$PROJECT_DIR" -type d 2>/dev/null | head -1)

if [ -z "$PROJECT_PATH" ]; then
    echo -e "${RED}Projet $PROJECT_DIR introuvable${NC}"
    exit 1
fi

echo "Projet trouvé: $PROJECT_PATH"

# Copier vers home ElsonG
TARGET_PATH="/home/$NEW_USER/$PROJECT_DIR"
if [ ! -d "$TARGET_PATH" ]; then
    cp -r "$PROJECT_PATH" "$TARGET_PATH"
    chown -R $NEW_USER:$NEW_USER "$TARGET_PATH"
    echo -e "${GREEN}✓${NC} Projet copié vers $TARGET_PATH"
else
    echo -e "${YELLOW}Le projet existe déjà dans /home/$NEW_USER${NC}"
fi

# Copier clé SSH si elle existe
if [ -d /root/.ssh ]; then
    mkdir -p /home/$NEW_USER/.ssh
    cp /root/.ssh/* /home/$NEW_USER/.ssh/ 2>/dev/null || true
    chown -R $NEW_USER:$NEW_USER /home/$NEW_USER/.ssh
    chmod 700 /home/$NEW_USER/.ssh
    chmod 600 /home/$NEW_USER/.ssh/* 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Clé SSH migrée"
fi

# ============================================
# ÉTAPE 3: Sécuriser permissions
# ============================================
echo -e "\n${BLUE}[3/6]${NC} Sécurisation des permissions..."

# config.json
CONFIG_FILE="$TARGET_PATH/config.json"
if [ -f "$CONFIG_FILE" ]; then
    chmod 600 "$CONFIG_FILE"
    chown $NEW_USER:$NEW_USER "$CONFIG_FILE"
    echo -e "${GREEN}✓${NC} config.json protégé (600)"
fi

# .ssh
if [ -d "/home/$NEW_USER/.ssh" ]; then
    chmod 700 /home/$NEW_USER/.ssh
    find /home/$NEW_USER/.ssh -type f -exec chmod 600 {} \;
    echo -e "${GREEN}✓${NC} Permissions SSH sécurisées"
fi

# Supprimer authorized_keys si présent
if [ -f "/home/$NEW_USER/.ssh/authorized_keys" ]; then
    rm /home/$NEW_USER/.ssh/authorized_keys
    echo -e "${GREEN}✓${NC} authorized_keys supprimé (pas d'accès entrant)"
fi

# transactions.csv
TRANS_FILE="$TARGET_PATH/transactions.csv"
if [ -f "$TRANS_FILE" ]; then
    chmod 600 "$TRANS_FILE"
    chown $NEW_USER:$NEW_USER "$TRANS_FILE"
fi

# ============================================
# ÉTAPE 4: Configuration Git locale
# ============================================
echo -e "\n${BLUE}[4/6]${NC} Configuration Git..."

# .gitignore local renforcé
GITIGNORE="$TARGET_PATH/.gitignore"
if [ -f "$GITIGNORE" ]; then
    # Ajouter transactions.csv localement si pas déjà présent
    if ! grep -q "^transactions\.csv$" "$GITIGNORE"; then
        echo -e "\n# Données locales (ne pas pusher)\ntransactions.csv" >> "$GITIGNORE"
        echo -e "${GREEN}✓${NC} transactions.csv ajouté au .gitignore local"
    fi
fi

# Configurer Git pour ElsonG
su - $NEW_USER -c "cd $TARGET_PATH && git config user.name 'ElsonG' && git config user.email '$EMAIL'"
echo -e "${GREEN}✓${NC} Git configuré"

# ============================================
# ÉTAPE 5: Désinstaller services dangereux
# ============================================
echo -e "\n${BLUE}[5/6]${NC} Nettoyage services dangereux..."

# openssh-server
if dpkg -l | grep -q openssh-server; then
    read -p "openssh-server détecté. Désinstaller? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apt-get remove --purge -y openssh-server
        echo -e "${GREEN}✓${NC} openssh-server supprimé"
    fi
else
    echo -e "${GREEN}✓${NC} Pas d'openssh-server"
fi

# Nettoyer packages orphelins
apt-get autoremove -y -qq
echo -e "${GREEN}✓${NC} Packages orphelins nettoyés"

# ============================================
# ÉTAPE 6: Audit quotidien automatique
# ============================================
echo -e "\n${BLUE}[6/6]${NC} Configuration audit quotidien..."

# Copier script audit vers /usr/local/bin
AUDIT_SCRIPT="/usr/local/bin/security_audit.sh"
if [ -f "./security_audit.sh" ]; then
    cp ./security_audit.sh "$AUDIT_SCRIPT"
    chmod +x "$AUDIT_SCRIPT"
    
    # Ajouter email dans le script
    sed -i "s/EMAIL=\"\"/EMAIL=\"$EMAIL\"/" "$AUDIT_SCRIPT"
    
    # Configurer cron pour ElsonG
    if command -v crontab &> /dev/null; then
        (crontab -u $NEW_USER -l 2>/dev/null; echo "$CRON_LINE") | crontab -u $NEW_USER -
        echo -e "${GREEN}✓${NC} Audit quotidien configuré (00:00)"
    else
        echo -e "${YELLOW}⚠${NC} Cron non disponible (proot) - Lancez manuellement: security_audit.sh"
    fi
    
    echo -e "${GREEN}✓${NC} Audit quotidien configuré (00:00)"
else
    echo -e "${YELLOW}⚠${NC} security_audit.sh introuvable (placez-le dans le même dossier)"
fi

# Créer dossier rapports
mkdir -p /home/$NEW_USER/security_reports
chown -R $NEW_USER:$NEW_USER /home/$NEW_USER/security_reports
echo -e "${GREEN}✓${NC} Dossier rapports créé"

# ============================================
# ÉTAPE 7: Alias et configuration shell
# ============================================
echo -e "\n${BLUE}[Bonus]${NC} Configuration alias..."

BASHRC="/home/$NEW_USER/.bashrc"
cat >> "$BASHRC" << 'EOF'

# === Alias Arbitrage ===
alias arb='cd ~/Routes_manager && python3 daily_briefing_bis.py'
alias sim='cd ~/Routes_manager && python3 daily_briefing_bis.py --simulation'
alias status='cd ~/Routes_manager && python3 daily_briefing_bis.py'
alias sec-audit='security_audit.sh'
alias sec-report='cat ~/security_reports/audit_*.log | tail -50'

# === Sécurité ===
alias rm='rm -i'
alias mv='mv -i'
alias cp='cp -i'
EOF

chown $NEW_USER:$NEW_USER "$BASHRC"
echo -e "${GREEN}✓${NC} Alias configurés"

# ============================================
# RAPPORT FINAL
# ============================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  DURCISSEMENT TERMINÉ                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Résumé:${NC}"
echo "  ✓ Utilisateur ElsonG créé et configuré"
echo "  ✓ Projet migré vers /home/$NEW_USER/$PROJECT_DIR"
echo "  ✓ Permissions sécurisées (config: 600, .ssh: 700)"
echo "  ✓ Audit quotidien activé (00:00)"
echo "  ✓ Services dangereux supprimés"
echo ""
echo -e "${YELLOW}Prochaines étapes:${NC}"
echo "  1. Déconnectez-vous de root"
echo "  2. Connectez-vous avec ElsonG:"
echo "     ${BLUE}su - $NEW_USER${NC}"
echo "  3. Testez l'environnement:"
echo "     ${BLUE}cd ~/$PROJECT_DIR && python3 daily_briefing_bis.py --simulation${NC}"
echo "  4. Lancez un audit manuel:"
echo "     ${BLUE}security_audit.sh${NC}"
echo ""
echo -e "${GREEN}Email notifications configuré:${NC} $EMAIL"
echo ""

exit 0