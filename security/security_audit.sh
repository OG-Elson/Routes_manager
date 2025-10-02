#!/bin/bash

# security_audit.sh - Audit de sécurité pour environnement Termux/Debian
# Niveau 3 - Audit complet non-invasif
# Auteur: ElsonG
# Date: 2025-10-01

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPORT_DIR="$HOME/security_reports"
REPORT_FILE="$REPORT_DIR/audit_$(date +%Y%m%d_%H%M%S).log"
EMAIL="" # Sera demandé ou lu depuis config
ALERT_THRESHOLD=70
SCORE=100

mkdir -p "$REPORT_DIR"

# Fonction de logging
log() {
    echo -e "$1" | tee -a "$REPORT_FILE"
}

alert() {
    log "${RED}[ALERTE]${NC} $1"
    SCORE=$((SCORE - $2))
}

warning() {
    log "${YELLOW}[AVERTISSEMENT]${NC} $1"
    SCORE=$((SCORE - $2))
}

success() {
    log "${GREEN}[OK]${NC} $1"
}

info() {
    log "${BLUE}[INFO]${NC} $1"
}

# Header
clear
log "========================================"
log "  AUDIT DE SÉCURITÉ - Niveau 3"
log "  Date: $(date '+%Y-%m-%d %H:%M:%S')"
log "========================================"
log ""

# Section 1: Informations système
info "Section 1: Informations système"
log "Utilisateur actuel: $(whoami)"
if [ "$(whoami)" = "root" ]; then
    warning "Vous êtes connecté en root - Migration vers ElsonG recommandée" 5
fi
log "Distribution: $(cat /etc/debian_version 2>/dev/null || echo 'Unknown')"
log "Uptime: $(uptime -p 2>/dev/null || echo 'N/A')"
log ""

# Section 2: Réseau
info "Section 2: Vérification réseau"

# Installer net-tools si absent
if ! command -v netstat &> /dev/null; then
    warning "net-tools non installé - Installation..." 0
    apt-get update -qq && apt-get install -y net-tools -qq 2>/dev/null
fi

# Ports ouverts
LISTENING_PORTS=$(netstat -tuln 2>/dev/null | grep LISTEN || echo "")
if [ -z "$LISTENING_PORTS" ]; then
    success "Aucun port en écoute"
else
    alert "Ports en écoute détectés:" 15
    log "$LISTENING_PORTS"
fi

# Connexions établies
ESTABLISHED=$(netstat -tun 2>/dev/null | grep ESTABLISHED | wc -l)
log "Connexions actives: $ESTABLISHED"
if [ $ESTABLISHED -gt 10 ]; then
    warning "Nombre élevé de connexions ($ESTABLISHED)" 5
fi
log ""

# Section 3: Processus suspects
info "Section 3: Analyse des processus"

SUSPICIOUS_PROCS=$(ps aux | grep -E "nc |ncat |socat |ssh.*-R" | grep -v grep || echo "")
if [ -z "$SUSPICIOUS_PROCS" ]; then
    success "Aucun processus suspect détecté"
else
    alert "Processus suspects trouvés:" 20
    log "$SUSPICIOUS_PROCS"
fi

# Processus Python
PYTHON_PROCS=$(ps aux | grep python | grep -v grep | wc -l)
log "Processus Python actifs: $PYTHON_PROCS"
log ""

# Section 4: Packages et dépôts
info "Section 4: Vérification packages"

# Dépôts APT
NON_OFFICIAL=$(grep -v "^#" /etc/apt/sources.list 2>/dev/null | grep -v "deb.debian.org" | grep -v "security.debian.org" || echo "")
if [ -z "$NON_OFFICIAL" ]; then
    success "Tous les dépôts sont officiels"
else
    warning "Dépôts non-officiels détectés:" 10
    log "$NON_OFFICIAL"
fi

# openssh-server
if dpkg -l | grep -q openssh-server; then
    alert "openssh-server installé - RISQUE D'ACCÈS DISTANT" 30
else
    success "openssh-server non installé"
fi

# Packages récents
log "Derniers packages installés:"
log "$(tail -20 /var/log/apt/history.log 2>/dev/null | grep "Install:" || echo 'Historique non disponible')"
log ""

# Section 5: Fichiers sensibles
info "Section 5: Permissions fichiers"

# Clé SSH
if [ -d "$HOME/.ssh" ]; then
    SSH_PERMS=$(stat -c %a "$HOME/.ssh" 2>/dev/null || echo "000")
    if [ "$SSH_PERMS" = "700" ]; then
        success "Permissions .ssh correctes (700)"
    else
        warning ".ssh permissions incorrectes: $SSH_PERMS (devrait être 700)" 5
    fi
    
    # Clé privée
    if [ -f "$HOME/.ssh/id_ed25519" ]; then
        KEY_PERMS=$(stat -c %a "$HOME/.ssh/id_ed25519")
        if [ "$KEY_PERMS" = "600" ]; then
            success "Clé SSH privée protégée (600)"
        else
            alert "Clé SSH privée exposée: $KEY_PERMS (devrait être 600)" 15
        fi
    fi
    
    # authorized_keys (ne devrait PAS exister)
    if [ -f "$HOME/.ssh/authorized_keys" ]; then
        alert "authorized_keys détecté - ACCÈS DISTANT POSSIBLE" 25
    else
        success "Pas d'authorized_keys (pas d'accès SSH entrant)"
    fi
else
    warning "Dossier .ssh absent" 0
fi

# config.json
if [ -f "$HOME/Routes_manager/config.json" ] || [ -f "$HOME/storage/shared/Routes_manager/config.json" ]; then
    CONFIG_PATH=$(find $HOME -name "config.json" 2>/dev/null | grep Routes_manager | head -1)
    CONFIG_PERMS=$(stat -c %a "$CONFIG_PATH" 2>/dev/null || echo "000")
    if [ "$CONFIG_PERMS" = "600" ]; then
        success "config.json protégé (600)"
    else
        warning "config.json permissions faibles: $CONFIG_PERMS (recommandé: 600)" 10
    fi
fi
log ""

# Section 6: .bashrc backdoors
info "Section 6: Analyse .bashrc"
BASHRC_SUSPICIOUS=$(grep -E "curl.*\|.*sh|wget.*\|.*bash|eval.*base64|nc -e" "$HOME/.bashrc" 2>/dev/null || echo "")
if [ -z "$BASHRC_SUSPICIOUS" ]; then
    success "Aucune commande suspecte dans .bashrc"
else
    alert "Commandes suspectes dans .bashrc:" 20
    log "$BASHRC_SUSPICIOUS"
fi
log ""

# Section 7: Crontab
info "Section 7: Tâches planifiées"
CRON_JOBS=$(crontab -l 2>/dev/null || echo "Aucune tâche cron")
log "Crontab actuel:"
log "$CRON_JOBS"
if echo "$CRON_JOBS" | grep -qE "curl|wget|nc|ncat"; then
    warning "Commandes réseau dans cron détectées" 10
fi
log ""

# Section 8: GitHub
info "Section 8: Configuration GitHub"
if [ -f "$HOME/.ssh/id_ed25519.pub" ]; then
    success "Clé SSH GitHub présente (push autorisé)"
    log "Empreinte: $(ssh-keygen -lf $HOME/.ssh/id_ed25519.pub 2>/dev/null || echo 'N/A')"
fi
log "RAPPEL: Vérifiez que votre dépôt est PRIVÉ sur github.com/OG-Elson/Routes_manager/settings"
log ""

# Rapport final
log "========================================"
log "  RAPPORT FINAL"
log "========================================"
log "Score de sécurité: ${SCORE}/100"

if [ $SCORE -ge 90 ]; then
    log "${GREEN}Excellent${NC} - Environnement très sécurisé"
elif [ $SCORE -ge 70 ]; then
    log "${YELLOW}Bon${NC} - Quelques améliorations possibles"
elif [ $SCORE -ge 50 ]; then
    log "${YELLOW}Moyen${NC} - Corrections recommandées"
else
    log "${RED}Critique${NC} - Action immédiate requise"
fi

log ""
log "Rapport sauvegardé: $REPORT_FILE"

# Envoyer alerte email si score < seuil
if [ $SCORE -lt $ALERT_THRESHOLD ] && [ -n "$EMAIL" ]; then
    log "Envoi notification email à $EMAIL..."
    # Note: Nécessite mailutils ou sendmail configuré
fi

exit 0