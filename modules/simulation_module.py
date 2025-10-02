# modules/simulation_module.py

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Configuration chemin
current_file = os.path.abspath(__file__)
modules_dir = os.path.dirname(current_file)
project_root = os.path.dirname(modules_dir)
os.chdir(project_root)
sys.path.insert(0, project_root)

from arbitrage_engine_bis import calculate_profit_route, markets, forex_rates
from daily_briefing_bis import robust_csv_append, generate_new_rotation_id
from rotation_manager import RotationManager
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.table import Table

console = Console()


class SimulationEngine:
    """Moteur de simulation de rotations complètes"""
    
    def __init__(self):
        self.simulation_id = None
        self.simulation_dir = None
        self.config = self._load_config()
        self.manager = RotationManager()

    def _get_confirmed_input(self, prompt, validation_func=None, error_msg="Saisie invalide."):
        """Saisie sécurisée avec option annuler"""
        while True:
            try:
                value = console.input(prompt)
                if value.lower() == 'annuler':
                    if Confirm.ask("Êtes-vous sûr de vouloir annuler la simulation ?"):
                        return None
                    else:
                        continue
                if validation_func is None or validation_func(value):
                    return value
                console.print(f"[bold red]{error_msg}[/bold red]")
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️  Simulation interrompue[/yellow]")
                return None
            
    def _get_numeric_input(self, prompt, input_type=float, min_val=0):
        """Saisie numérique ultra-sécurisée (copie de daily_briefing_bis)"""
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
            value_str = self._get_confirmed_input(
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

    def _load_config(self):
        """Charge la configuration"""
        with open('config.json', 'r') as f:
            return json.load(f)
    @staticmethod
    def _round_amounts(data):
        """Arrondit les montants pour l'écriture CSV"""
        data['Amount_USDT'] = round(float(data['Amount_USDT']), 2)  # 6 décimales pour USDT
        data['Price_Local'] = round(float(data['Price_Local']), 2)  # 4 décimales pour prix
        data['Amount_Local'] = round(float(data['Amount_Local']), 2)  # 2 décimales pour FIAT
        data['Fee_Pct'] = round(float(data['Fee_Pct']), 2)  # 2 décimales pour %
        return data
    
    def _create_simulation_dirs(self):
        """Crée la structure de dossiers pour la simulation"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.simulation_id = f"SIM_{timestamp}"
        self.simulation_dir = Path('simulations') / self.simulation_id
        self.simulation_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(f"\n[green]✓[/green] Dossier de simulation créé : {self.simulation_dir}")
        return self.simulation_dir
    
    def _get_user_inputs(self):
        """Collecte les paramètres de simulation via interface interactive"""
        console.print(Panel.fit(
            "[bold cyan]MODULE DE SIMULATION[/bold cyan]\n"
            "Configurez votre rotation simulée",
            border_style="cyan"
        ))
        
        # 1. Monnaie de sourcing
        available_currencies = [m['currency'] for m in self.config['markets']]
        console.print(f"\n[yellow]Monnaies disponibles :[/yellow] {', '.join(available_currencies)}")
        
        sourcing_currency = self._get_confirmed_input(
            f"Monnaie de sourcing (options: {'/'.join(available_currencies)}) : ",
            lambda x: x.upper() in available_currencies,
            f"Devise invalide. Choix : {', '.join(available_currencies)}"
        )
        if sourcing_currency is None:
            return None
        sourcing_currency = sourcing_currency.upper()
        
        # 2. Capital initial
        initial_capital = self._get_numeric_input(
            f"Capital initial en {sourcing_currency}",
            float, 0
        )
        if initial_capital is None:
            return None
        
        # 3. Nombre de cycles
        nb_cycles = self._get_numeric_input(
            "Nombre de cycles",
            int, 1
        )
        if nb_cycles is None:
            return None
        
        # 4. Monnaie de bouclage
        console.print("\n[yellow]Monnaie de bouclage[/yellow]")
        use_loop = self._get_confirmed_input(
            "Voulez-vous forcer une monnaie de bouclage ? (o/n) : ",
            lambda x: x.lower() in ['o', 'n'],
            "Répondez 'o' ou 'n'"
        )
        if use_loop is None:
            return None
        
        loop_currency = None
        if use_loop.lower() == 'o':
            loop_currency = self._get_confirmed_input(
                f"Monnaie de bouclage (options: {'/'.join(available_currencies)}) : ",
                lambda x: x.upper() in available_currencies,
                f"Devise invalide. Choix : {', '.join(available_currencies)}"
            )
            if loop_currency is None:
                return None
            loop_currency = loop_currency.upper()
        
        # 5. Marchés exclus
        console.print("\n[yellow]Exclusion de marchés[/yellow]")
        use_exclusion = self._get_confirmed_input(
            "Voulez-vous exclure certains marchés comme marché de VENTE ? (o/n) : ",
            lambda x: x.lower() in ['o', 'n'],
            "Répondez 'o' ou 'n'"
        )
        if use_exclusion is None:
            return None
        
        soft_excluded = []
        if use_exclusion.lower() == 'o':
            console.print(f"[yellow]Marchés disponibles :[/yellow] {', '.join(available_currencies)}")
            console.print("[dim]Les marchés exclus ne pourront pas être utilisés comme marché de vente[/dim]")
            
            excluded_input = self._get_confirmed_input(
                "Marchés à exclure (séparés par virgules) ou vide : ",
                None  # Pas de validation, peut être vide
            )
            if excluded_input is None:
                return None
            
            if excluded_input.strip():
                soft_excluded = [c.strip().upper() for c in excluded_input.split(',')]
                soft_excluded = [c for c in soft_excluded if c in available_currencies]
                
                if loop_currency and loop_currency in soft_excluded:
                    console.print(f"[yellow]⚠️  {loop_currency} est exclu mais forcé comme bouclage → Priorité au bouclage[/yellow]")
        
        return {
            'sourcing_currency': sourcing_currency,
            'nb_cycles': nb_cycles,
            'loop_currency': loop_currency,
            'soft_excluded': soft_excluded,
            'initial_capital': initial_capital
        }
    
    def _convert_to_usdt(self, amount, currency):
        """Convertit un montant en USDT selon les prix du marché"""
        for market in self.config['markets']:
            if market['currency'] == currency:
                # Coût pour acheter 1 USDT dans cette monnaie (avec frais)
                cost_per_usdt = market['buy_price'] * (1 + market['fee_pct'] / 100.0)
                usdt_amount = amount / cost_per_usdt
                return usdt_amount
        return amount  # Fallback si monnaie non trouvée
    
    def _get_market_price(self, currency, price_type):
        """Récupère le prix d'un marché"""
        for market in self.config['markets']:
            if market['currency'] == currency:
                if price_type == 'buy':
                    return market['buy_price']
                elif price_type == 'sell':
                    return market['sell_price']
        return 0

    def _get_market_fee(self, currency):
        """Récupère les frais d'un marché"""
        for market in self.config['markets']:
            if market['currency'] == currency:
                return market['fee_pct']
        return 0
    
    def _find_optimal_route(self, sourcing_currency, soft_excluded, loop_currency):
        """Trouve la meilleure route en tenant compte des exclusions"""
        console.print("\n[yellow]🔍 Recherche de la route optimale...[/yellow]")
        
        all_routes = []
        
        for market in self.config['markets']:
            selling_currency = market['currency']
            
            # Skip si même monnaie
            if selling_currency == sourcing_currency:
                continue
            
            # RÈGLE CRITIQUE: Skip si marché de VENTE est exclu
            # EXCEPTION: Sauf si c'est le bouclage forcé
            if selling_currency in soft_excluded:
                if loop_currency and selling_currency == loop_currency:
                    console.print(f"[dim]  {selling_currency} exclu mais accepté car bouclage forcé[/dim]")
                else:
                    console.print(f"[dim]  {selling_currency} exclu comme marché de vente → Skip[/dim]")
                    continue
            
            # Tester sans et avec double cycle
            for use_dc in [False, True]:
                route = calculate_profit_route(
                    1000,  # Capital test standardisé
                    sourcing_currency,
                    selling_currency,
                    use_dc
                )
                
                if route:
                    all_routes.append(route)
    
        if not all_routes:
            console.print("[red]❌ Aucune route valide trouvée avec ces contraintes[/red]")
            return None

        # Trier par profitabilité
        sorted_routes = sorted(all_routes, key=lambda x: x['profit_pct'], reverse=True)

        # Afficher top 5 (ou moins si pas assez de routes)
        nb_routes_to_show = min(5, len(sorted_routes))
        table = Table(title="Routes Optimales Disponibles", show_header=True)
        table.add_column("Choix", justify="center", style="cyan")
        table.add_column("Route", style="white")
        table.add_column("Marge %", justify="right")

        for i, route in enumerate(sorted_routes[:nb_routes_to_show], 1):
            style = "bold green" if i == 1 else ""
            margin_style = "bold green" if route['profit_pct'] > 0 else "bold red"
            table.add_row(
                str(i),
                f"[{style}]{route['detailed_route']}[/]" if style else route['detailed_route'],
                f"[{margin_style}]{route['profit_pct']:.2f}%[/{margin_style}]"
            )

        console.print(table)

        # Demander à l'utilisateur de choisir
        try:
            choice_str = self._get_confirmed_input(
                f"Quelle route souhaitez-vous simuler ? (1-{nb_routes_to_show}) : ",
                lambda x: x.isdigit() and 1 <= int(x) <= nb_routes_to_show,
                f"Entrez un nombre entre 1 et {nb_routes_to_show}"
            )
            if choice_str is None:
                return None
            
            choice = int(choice_str)
            best_route = sorted_routes[choice - 1]
            
            console.print(f"\n[green]✓[/green] Route sélectionnée : {best_route['detailed_route']}")
            return best_route
            
        except (ValueError, IndexError):
            console.print("[red]Choix invalide[/red]")
            return None
    
    def _generate_simulated_transactions(self, params, best_route):
        """Génère les transactions simulées pour tous les cycles"""
        transactions = []
        rotation_id = generate_new_rotation_id(None)
        
        # Convertir capital initial en USDT
        current_usdt = self._convert_to_usdt(params['initial_capital'], params['sourcing_currency'])
        
        console.print(f"\n[cyan]Capital initial:[/cyan] {params['initial_capital']:.2f} {params['sourcing_currency']} = {current_usdt:.6f} USDT")
        
        # Initialiser la rotation dans le manager
        self.manager.init_rotation(rotation_id)
        if params['loop_currency']:
            self.manager.set_loop_currency(rotation_id, params['loop_currency'])
        
        console.print(f"\n[yellow]📝 Génération des transactions pour {params['nb_cycles']} cycles...[/yellow]\n")
        
        for cycle in range(1, params['nb_cycles'] + 1):
            # Cycle 1: utilise le sourcing choisi
            # Cycles 2+: sourcing = monnaie de bouclage (réinvestissement)
            if cycle == 1:
                sourcing = best_route['sourcing_market_code']
                use_dc = best_route['use_double_cycle']
            else:
                sourcing = params['loop_currency'] or 'EUR'
                use_dc = False
            
            selling = best_route['selling_market_code']
            
            # Recalculer avec le capital actuel
            route = calculate_profit_route(current_usdt, sourcing, selling, use_dc)
            
            if not route:
                console.print(f"[red]⚠️  Impossible de calculer le cycle {cycle}[/red]")
                break
            
            console.print(f"[cyan]Cycle {cycle}:[/cyan] {route['detailed_route']} → Marge: {route['profit_pct']:.2f}%")
            
            # Transaction 1: ACHAT
            sourcing_market = next((m for m in self.config['markets'] if m['currency'] == sourcing), None)
            achat_data ={
                'Date': datetime.now().strftime('%Y-%m-%d'),
                'Rotation_ID': rotation_id,
                'Type': 'ACHAT',
                'Market': sourcing,
                'Currency': sourcing,
                'Amount_USDT': current_usdt,
                'Price_Local': sourcing_market['buy_price'],
                'Amount_Local': current_usdt * sourcing_market['buy_price'],
                'Fee_Pct': sourcing_market['fee_pct'],
                'Payment_Method': 'Simulation',
                'Counterparty_ID': f'SIM_BUYER_{cycle}',
                'Notes': f'Cycle {cycle} - Achat USDT simulé'
            }
            transactions.append(self._round_amounts(achat_data))
            
            # Transaction 2: VENTE
            selling_market = next((m for m in self.config['markets'] if m['currency'] == selling), None)
            vente_data ={
                'Date': datetime.now().strftime('%Y-%m-%d'),
                'Rotation_ID': rotation_id,
                'Type': 'VENTE',
                'Market': selling,
                'Currency': selling,
                'Amount_USDT': current_usdt,
                'Price_Local': selling_market['sell_price'],
                'Amount_Local': current_usdt * selling_market['sell_price'],
                'Fee_Pct': selling_market['fee_pct'],
                'Payment_Method': 'Simulation',
                'Counterparty_ID': f'SIM_SELLER_{cycle}',
                'Notes': f'Cycle {cycle} - Vente USDT simulée'
            }
            
            transactions.append(self._round_amounts(vente_data))
            
            # Transaction 3: CONVERSION (toujours vers monnaie de bouclage)
            loop_curr = params['loop_currency'] or 'EUR'
            conversion_data = {
                'Date': datetime.now().strftime('%Y-%m-%d'),
                'Rotation_ID': rotation_id,
                'Type': 'CONVERSION',
                'Market': f"{selling}->{loop_curr}",
                'Currency': loop_curr,
                'Amount_USDT': route['final_amount_usdt'],
                'Price_Local': 1.0,
                'Amount_Local': route['revenue_eur'],
                'Fee_Pct': 0.0,
                'Payment_Method': 'Forex',
                'Counterparty_ID': 'FOREX_SIM',
                'Notes': f'Cycle {cycle} - Conversion {selling}→{loop_curr} simulée'
            }

            transactions.append(self._round_amounts(conversion_data))
            
            # Mettre à jour le capital pour le prochain cycle
            current_usdt = route['final_amount_usdt']
            self.manager.increment_cycle(rotation_id)
        
        return transactions, rotation_id, current_usdt
    
    def _save_simulation_data(self, transactions, params, best_route, final_usdt):
        """Sauvegarde tous les fichiers de simulation"""
        
        # 1. Transactions CSV
        csv_file = self.simulation_dir / 'transactions.csv'
        for trans in transactions:
            robust_csv_append(str(csv_file), trans)
        
        console.print(f"\n[green]✓[/green] Transactions: {csv_file}")
        
        # 2. Plan de vol JSON
        plan_file = self.simulation_dir / 'plan_de_vol.json'
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(best_route['plan_de_vol'], f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]✓[/green] Plan de vol: {plan_file}")
        
        # 3. Configuration simulation JSON
        initial_usdt = self._convert_to_usdt(params['initial_capital'], params['sourcing_currency'])
        
        config_file = self.simulation_dir / 'simulation_config.json'
        config_data = {
            'simulation_id': self.simulation_id,
            'timestamp': datetime.now().isoformat(),
            'parameters': {
                'sourcing_currency': params['sourcing_currency'],
                'nb_cycles': params['nb_cycles'],
                'loop_currency': params['loop_currency'],
                'soft_excluded': params['soft_excluded'],
                'initial_capital': params['initial_capital'],
                'initial_capital_usdt': initial_usdt
            },
            'best_route': {
                'route': best_route['detailed_route'],
                'margin_pct': best_route['profit_pct'],
                'sourcing': best_route['sourcing_market_code'],
                'selling': best_route['selling_market_code'],
                'use_double_cycle': best_route['use_double_cycle']
            },
            'results': {
                'initial_usdt': initial_usdt,
                'final_usdt': final_usdt,
                'profit_usdt': final_usdt - initial_usdt,
                'roi_pct': ((final_usdt - initial_usdt) / initial_usdt * 100) if initial_usdt > 0 else 0,
                'nb_transactions': len(transactions)
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]✓[/green] Configuration: {config_file}")
        
        # 4. Rapport texte
        self._generate_text_report(transactions, params, best_route, initial_usdt, final_usdt)
    
    def _generate_text_report(self, transactions, params, best_route, initial_usdt, final_usdt):
        """Génère un rapport texte lisible"""
        report_file = self.simulation_dir / 'simulation_report.txt'
        
        profit_usdt = final_usdt - initial_usdt
        roi_pct = (profit_usdt / initial_usdt * 100) if initial_usdt > 0 else 0
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("RAPPORT DE SIMULATION DE ROTATION\n")
            f.write(f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
            f.write(f"ID Simulation: {self.simulation_id}\n")
            f.write("="*70 + "\n\n")
            
            f.write("PARAMÈTRES DE SIMULATION:\n")
            f.write("-"*70 + "\n")
            f.write(f"  Monnaie de sourcing:        {params['sourcing_currency']}\n")
            f.write(f"  Capital initial:            {params['initial_capital']:.2f} {params['sourcing_currency']}\n")
            f.write(f"                              = {initial_usdt:.6f} USDT\n")
            f.write(f"  Nombre de cycles:           {params['nb_cycles']}\n")
            f.write(f"  Monnaie de bouclage:        {params['loop_currency'] or 'Auto (EUR par défaut)'}\n")
            f.write(f"  Marchés exclus (vente):     {', '.join(params['soft_excluded']) or 'Aucun'}\n\n")
            
            f.write("ROUTE OPTIMALE SÉLECTIONNÉE:\n")
            f.write("-"*70 + "\n")
            f.write(f"  Chemin:                     {best_route['detailed_route']}\n")
            f.write(f"  Marge théorique:            {best_route['profit_pct']:.2f}%\n")
            f.write(f"  Double cycle:               {'Oui' if best_route['use_double_cycle'] else 'Non'}\n")
            f.write(f"  Marché de sourcing:         {best_route['sourcing_market_code']}\n")
            f.write(f"  Marché de vente:            {best_route['selling_market_code']}\n\n")
            
            f.write("DÉTAIL DES TRANSACTIONS SIMULÉES:\n")
            f.write("-"*70 + "\n")
            
            for i, trans in enumerate(transactions, 1):
                f.write(f"\n  Transaction {i} ({trans['Type']}):\n")
                f.write(f"    Marché:           {trans['Market']}\n")
                f.write(f"    Montant USDT:     {trans['Amount_USDT']:.6f}\n")
                f.write(f"    Prix local:       {trans['Price_Local']:.6f}\n")
                f.write(f"    Montant local:    {trans['Amount_Local']:.2f} {trans['Currency']}\n")
                f.write(f"    Frais:            {trans['Fee_Pct']}%\n")
                f.write(f"    Contrepartie:     {trans['Counterparty_ID']}\n")
            
            f.write("\n" + "="*70 + "\n")
            f.write("RÉSULTAT FINAL:\n")
            f.write("="*70 + "\n")
            f.write(f"  Capital initial (USDT):     {initial_usdt:.6f}\n")
            f.write(f"  Capital final (USDT):       {final_usdt:.6f}\n")
            f.write(f"  Profit (USDT):              {profit_usdt:.6f}\n")
            f.write(f"  ROI:                        {roi_pct:.2f}%\n")
            f.write(f"  Nombre de transactions:     {len(transactions)}\n")
            f.write("="*70 + "\n")
        
        console.print(f"[green]✓[/green] Rapport: {report_file}")
    
    def run_simulation(self):
        """Lance la simulation complète"""
        try:
            # 1. Créer dossiers
            self._create_simulation_dirs()
            
            # 2. Collecter paramètres
            params = self._get_user_inputs()

            if params is None:
                console.print("[yellow]⚠️  Simulation annulée par l'utilisateur[/yellow]")
                return False            
            # 3. Trouver route optimale
            best_route = self._find_optimal_route(
                params['sourcing_currency'],
                params['soft_excluded'],
                params['loop_currency']
            )
            
            if not best_route:
                console.print("[red]❌ Impossible de trouver une route valide[/red]")
                return False
            
            # 4. Générer transactions
            transactions, rotation_id, final_usdt = self._generate_simulated_transactions(params, best_route)
            
            # 5. Sauvegarder tout
            self._save_simulation_data(transactions, params, best_route, final_usdt)
            
            # 6. Résumé final
            initial_usdt = self._convert_to_usdt(params['initial_capital'], params['sourcing_currency'])
            profit_usdt = final_usdt - initial_usdt
            roi_pct = (profit_usdt / initial_usdt * 100) if initial_usdt > 0 else 0
            
            profit_style = "green" if profit_usdt > 0 else "red"
            
            console.print(Panel.fit(
                f"[bold green]✓ SIMULATION TERMINÉE[/bold green]\n\n"
                f"[cyan]ID:[/cyan] {self.simulation_id}\n"
                f"[cyan]Rotation ID:[/cyan] {rotation_id}\n"
                f"[cyan]Dossier:[/cyan] {self.simulation_dir}\n\n"
                f"[yellow]Capital initial:[/yellow] {initial_usdt:.6f} USDT\n"
                f"[yellow]Capital final:[/yellow] {final_usdt:.6f} USDT\n"
                f"[{profit_style}]Profit:[/{profit_style}] [{profit_style}]{profit_usdt:.6f} USDT[/{profit_style}]\n"
                f"[{profit_style}]ROI:[/{profit_style}] [{profit_style}]{roi_pct:.2f}%[/{profit_style}]\n\n"
                f"[dim]Fichiers générés: 4[/dim]",
                border_style="green"
            ))
            
            return True
            
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  Simulation interrompue par l'utilisateur[/yellow]")
            return False
        except Exception as e:
            console.print(f"[bold red]❌ Erreur: {e}[/bold red]")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Point d'entrée du module"""
    engine = SimulationEngine()
    success = engine.run_simulation()
    
    if success:
        console.print("\n[green]Simulation réussie ! Les fichiers sont dans le dossier simulations/[/green]")
    else:
        console.print("\n[red]Simulation échouée[/red]")
    
    return success


if __name__ == "__main__":
    main()