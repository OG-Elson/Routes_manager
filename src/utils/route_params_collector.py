# src/utils/route_params_collector.py

from rich.console import Console
from rich.prompt import Confirm
from typing import List, Optional

console = Console()


def _get_confirmed_input(prompt, validation_func=None, error_msg="Saisie invalide."):
    """Saisie sécurisée avec option annuler"""
    while True:
        try:
            value = console.input(prompt)
            if value.lower() == 'annuler':
                if Confirm.ask("Êtes-vous sûr de vouloir annuler ?"):
                    return None
                else:
                    continue
            if validation_func is None or validation_func(value):
                return value
            console.print(f"[bold red]{error_msg}[/bold red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Opération interrompue[/yellow]")
            return None


# --- NOUVELLE FONCTION D'AIDE pour la validation des marchés exclus ---
def _parse_excluded_markets_input(input_str: str, available_currencies: List[str]) -> Optional[List[str]]:
    """Parse la chaîne d'exclusion et valide chaque code devise."""
    input_str = input_str.strip()
    if not input_str:
        return []

    # Sépare par virgule, filtre les vides et met en majuscules
    codes = [c.strip().upper() for c in input_str.split(',') if c.strip()]
    
    # Vérifie si toutes les devises sont valides
    for code in codes:
        if code not in available_currencies:
            # Retourne None si une devise est invalide
            return None 

    return codes
# ---------------------------------------------------------------------


def collect_route_search_parameters(markets_list, config):
    """
    Collecte interactive des paramètres communs pour recherche de routes
    ...
    """
    
    available_currencies = [m['currency'] for m in markets_list]
    
    # 1. Monnaie de sourcing
    console.print(f"\n[yellow]Monnaies disponibles :[/yellow] {', '.join(available_currencies)}")
    
    sourcing_currency = _get_confirmed_input(
        f"Monnaie de sourcing (options: {'/'.join(available_currencies)}) : ",
        lambda x: x.upper() in available_currencies,
        f"Devise invalide. Choix : {', '.join(available_currencies)}"
    )
    if sourcing_currency is None:
        return None
    sourcing_currency = sourcing_currency.upper()
    
    # 2. Monnaie de bouclage (pas de changement)
    console.print("\n[yellow]Monnaie de bouclage[/yellow]")
    use_loop = _get_confirmed_input(
        "Voulez-vous forcer une monnaie de bouclage ? (o/n) : ",
        lambda x: x.lower() in ['o', 'n'],
        "Répondez 'o' ou 'n'"
    )
    if use_loop is None:
        return None
    
    loop_currency = None
    if use_loop.lower() == 'o':
        loop_currency = _get_confirmed_input(
            f"Monnaie de bouclage (options: {'/'.join(available_currencies)}) : ",
            lambda x: x.upper() in available_currencies,
            f"Devise invalide. Choix : {', '.join(available_currencies)}"
        )
        if loop_currency is None:
            return None
        loop_currency = loop_currency.upper()
    
    # 3. Marchés exclus
    console.print("\n[yellow]Exclusion de marchés[/yellow]")
    use_exclusion = _get_confirmed_input(
        "Voulez-vous exclure certains marchés comme marché de VENTE ? (o/n) : ",
        lambda x: x.lower() in ['o', 'n'],
        "Répondez 'o' ou 'n'"
    )
    if use_exclusion is None:
        return None
    
    excluded_markets = []
    if use_exclusion.lower() == 'o':
        console.print(f"[yellow]Marchés disponibles :[/yellow] {', '.join(available_currencies)}")
        console.print("[dim]Les marchés exclus ne pourront pas être utilisés comme marché de vente[/dim]")
        
        # MODIFICATION CRITIQUE ICI : Utilisation de la validation stricte pour les marchés exclus
        excluded_input = _get_confirmed_input(
            "Marchés à exclure (séparés par virgules) ou vide : ",
            # Le validateur vérifie que l'entrée est bien parsable et que toutes les devises sont connues
            lambda x: _parse_excluded_markets_input(x, available_currencies) is not None,
            "Entrée invalide. Les codes devises doivent être séparés par des virgules et appartenir aux marchés disponibles."
        )
        if excluded_input is None:
            return None
        
        # Le parsing est refait ici après la validation réussie
        parsed_markets = _parse_excluded_markets_input(excluded_input, available_currencies)
        if parsed_markets is not None: 
            excluded_markets = parsed_markets
            
        if loop_currency and loop_currency in excluded_markets:
            console.print(f"[yellow]⚠️ {loop_currency} est exclu mais forcé comme bouclage → Priorité au bouclage[/yellow]")
    
    # 4. Méthode de conversion
    console.print("\n[yellow]Méthode de conversion fiat[/yellow]")
    default_method = config.get('default_conversion_method', 'forex')
    
    console.print("  [cyan]1.[/cyan] FOREX (marché) - Spreads bid/ask")
    console.print("  [cyan]2.[/cyan] BANQUE - Spread additionnel")
    console.print(f"  [dim]Entrée = Défaut ({default_method.upper()})[/dim]")
    
    # MODIFICATION CRITIQUE ICI : Ajout de 'forex' et 'bank' dans la validation
    method_choice = _get_confirmed_input(
        "Choisissez (1/2, 'forex', 'bank', ou Entrée) : ",
        lambda x: x.lower() in ['1', '2', 'forex', 'bank', ''],
        "Choisissez 1, 2, 'forex', 'bank' ou Entrée"
    )
    
    if method_choice is None:
        return None
    
    method_choice_lower = method_choice.lower()
    
    if method_choice_lower == '':
        conversion_method = default_method
    elif method_choice_lower == '1' or method_choice_lower == 'forex':
        conversion_method = 'forex'
    elif method_choice_lower == '2' or method_choice_lower == 'bank':
        conversion_method = 'bank'
    else:
        # Cas impossible avec la validation, mais garde la valeur par défaut si un problème survient
        conversion_method = default_method
    
    console.print(f"[green]✓[/green] Méthode sélectionnée : {conversion_method.upper()}")
    
    return {
        'sourcing_currency': sourcing_currency,
        'excluded_markets': excluded_markets,
        'loop_currency': loop_currency,
        'conversion_method': conversion_method
    }


def collect_simulation_parameters(markets_list, config):
    """
    Collecte tous les paramètres pour simulation
    ...
    """
    from rich.panel import Panel
    
    console.print(Panel.fit(
        "[bold cyan]MODULE DE SIMULATION[/bold cyan]\n"
        "Configurez votre rotation simulée",
        border_style="cyan"
    ))
    
    # Collecter les paramètres communs de routes
    route_params = collect_route_search_parameters(markets_list, config)
    if route_params is None:
        return None
    
    # ========== FONCTION INTERNE AVEC GESTION D'ERREURS COMPLÈTE (Pas de changement) ==========
    def get_numeric_input_robust(prompt, input_type=float, min_val=0):
        """Saisie numérique ULTRA-sécurisée (copie exacte de votre version)"""
        def is_valid_number(v):
            try:
                # Gestion valeur vide
                if not v or v.strip() == '':
                    return False
                num = input_type(v.replace(',', '.'))
                if input_type == float and (num < min_val or num > 1000000):
                    return False
                # Vérification NaN et infini
                if num != num or num == float('inf') or num == float('-inf'):
                    return False
                return num >= min_val
            except (ValueError, OverflowError):
                return False
        
        while True:
            # Remplacement de l'ancien appel _get_confirmed_input par le nouveau
            value_str = _get_confirmed_input(
                prompt + " (tapez 'annuler' pour quitter) : ",
                is_valid_number,
                f"Nombre invalide (min: {min_val}, max: 1,000,000) ou valeur vide"
            )
            if value_str is None:
                return None
            
            # Vérification valeur vide explicite
            if not value_str or value_str.strip() == '':
                console.print("[bold red]Vous n'avez entré aucune valeur. Veuillez entrer un nombre ou 'annuler'.[/bold red]")
                continue
                
            try:
                result = input_type(value_str.replace(',', '.'))
                # Double vérification post-conversion
                if result != result or result == float('inf') or result == float('-inf'):
                    console.print("[bold red]Valeur invalide (NaN/Infini détecté)[/bold red]")
                    continue
                return result
            except (ValueError, OverflowError):
                console.print("[bold red]Erreur de conversion numérique[/bold red]")
                continue
    
    # Capital initial
    initial_capital = get_numeric_input_robust(
        f"\nCapital initial en {route_params['sourcing_currency']}",
        float, 0
    )
    if initial_capital is None:
        return None
    
    # Nombre de cycles
    nb_cycles = get_numeric_input_robust(
        "Nombre de cycles",
        int, 1
    )
    if nb_cycles is None:
        return None
    
    return {
        'sourcing_currency': route_params['sourcing_currency'],
        'nb_cycles': nb_cycles,
        'loop_currency': route_params['loop_currency'],
        'soft_excluded': route_params['excluded_markets'],
        'initial_capital': initial_capital,
        'conversion_method': route_params['conversion_method']
    }