# src/utils/route_params_collector.py

from rich.console import Console
from rich.prompt import Confirm

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


def collect_route_search_parameters(markets_list, config):
    """
    Collecte interactive des paramètres communs pour recherche de routes
    
    Args:
        markets_list: Liste des marchés depuis config
        config: Configuration complète
    
    Returns:
        dict: {
            'sourcing_currency': str,
            'excluded_markets': list,
            'loop_currency': str or None,
            'conversion_method': str ('forex' or 'bank')
        }
        ou None si annulé
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
    
    # 2. Monnaie de bouclage
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
        
        excluded_input = _get_confirmed_input(
            "Marchés à exclure (séparés par virgules) ou vide : ",
            None
        )
        if excluded_input is None:
            return None
        
        if excluded_input.strip():
            excluded_markets = [c.strip().upper() for c in excluded_input.split(',')]
            excluded_markets = [c for c in excluded_markets if c in available_currencies]
            
            if loop_currency and loop_currency in excluded_markets:
                console.print(f"[yellow]⚠️ {loop_currency} est exclu mais forcé comme bouclage → Priorité au bouclage[/yellow]")
    
    # 4. Méthode de conversion
    console.print("\n[yellow]Méthode de conversion fiat[/yellow]")
    default_method = config.get('default_conversion_method', 'forex')
    
    console.print("  [cyan]1.[/cyan] FOREX (marché) - Spreads bid/ask")
    console.print("  [cyan]2.[/cyan] BANQUE - Spread additionnel")
    console.print(f"  [dim]Entrée = Défaut ({default_method.upper()})[/dim]")
    
    method_choice = _get_confirmed_input(
        "Choisissez (1/2 ou Entrée) : ",
        lambda x: x in ['1', '2', ''],
        "Choisissez 1, 2 ou Entrée"
    )
    
    if method_choice is None:
        return None
    
    if method_choice == '':
        conversion_method = default_method
    elif method_choice == '1':
        conversion_method = 'forex'
    else:
        conversion_method = 'bank'
    
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
    Inclut les paramètres de recherche de routes + paramètres spécifiques simulation
    
    Args:
        markets_list: Liste des marchés depuis config
        config: Configuration complète
    
    Returns:
        dict: {
            'sourcing_currency': str,
            'nb_cycles': int,
            'loop_currency': str or None,
            'soft_excluded': list,
            'initial_capital': float,
            'conversion_method': str
        }
        ou None si annulé
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
    
    # ========== FONCTION INTERNE AVEC GESTION D'ERREURS COMPLÈTE ==========
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