# kpi_analyzer.py

import json
import logging
import os
from datetime import datetime

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# --- CONFIGURATION DU LOGGING ---
logging.basicConfig(filename='app.log', level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

console = Console()

def safe_read_csv_kpis(csv_path):
    """Lecture CSV sÃ©curisÃ©e avec fallback d'encodage"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Fichier non trouvÃ©: {csv_path}")

    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        if df.empty:
            raise ValueError("Le fichier CSV est vide")
        return df
    except UnicodeDecodeError:
        try:
            return pd.read_csv(csv_path, sep=';', encoding='utf-8-sig')
        except UnicodeDecodeError:
            return pd.read_csv(csv_path, sep=';', encoding='latin-1')

def clean_and_validate_data(df):
    """Nettoie et valide les donnÃ©es du DataFrame"""
    df = df.fillna('')

    numeric_columns = ['Amount_USDT', 'Price_Local', 'Fee_Pct', 'Amount_Local']

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if col in ['Amount_USDT', 'Amount_Local']:
                df[col] = df[col].apply(lambda x: max(0, x))

    return df

def create_detailed_reports_structure():
    """CrÃ©e la structure de dossiers pour les rapports dÃ©taillÃ©s"""
    now = datetime.now()
    base_dir = "reports_detailed"

    # Structure: reports_detailed/2025/09_September/daily/
    year_dir = os.path.join(base_dir, now.strftime("%Y"))
    month_dir = os.path.join(year_dir, f"{now.strftime('%m')}_{now.strftime('%B')}")
    daily_dir = os.path.join(month_dir, "daily")

    os.makedirs(daily_dir, exist_ok=True)

    return {
        'base_dir': base_dir,
        'year_dir': year_dir,
        'month_dir': month_dir,
        'daily_dir': daily_dir
    }

def save_detailed_transaction_report(df_filtered, rotation_summary, dirs):
    """Sauvegarde le rapport dÃ©taillÃ© en Ã©vitant les doublons"""
    now = datetime.now()

    try:
        # 1. VÃ©rifier les rotations dÃ©jÃ  sauvegardÃ©es aujourd'hui
        today_pattern = now.strftime('%Y%m%d')
        existing_files = [f for f in os.listdir(dirs['daily_dir']) if f.startswith(f'summary_{today_pattern}')]

        existing_rotation_ids = set()
        for file in existing_files:
            try:
                existing_df = pd.read_csv(os.path.join(dirs['daily_dir'], file), sep=';')
                existing_rotation_ids.update(existing_df['Rotation_ID'].tolist())
            except:
                continue

        # 2. Filtrer les nouvelles rotations uniquement
        new_rotations = [r for r in rotation_summary if r['Rotation_ID'] not in existing_rotation_ids]

        if not new_rotations:
            console.print("[yellow]â ï¸ Aucune nouvelle rotation Ã  sauvegarder[/yellow]")
            return {
                'summary_file': None,
                'detail_file': None,
                'metadata_file': None,
                'new_count': 0
            }

        # 3. Filtrer les transactions des nouvelles rotations
        new_rotation_ids = {r['Rotation_ID'] for r in new_rotations}
        df_new_transactions = df_filtered[df_filtered['Rotation_ID'].isin(new_rotation_ids)]

        # 4. Sauvegarder uniquement les nouvelles donnÃ©es
        summary_file = os.path.join(dirs['daily_dir'], f"summary_{now.strftime('%Y%m%d_%H%M')}.csv")
        df_new_summary = pd.DataFrame(new_rotations)
        df_new_summary.to_csv(summary_file, sep=';', index=False, encoding='utf-8')

        detail_file = os.path.join(dirs['daily_dir'], f"transactions_detail_{now.strftime('%Y%m%d_%H%M')}.csv")
        df_new_transactions.to_csv(detail_file, sep=';', index=False, encoding='utf-8')

        # 5. MÃ©tadonnÃ©es
        metadata = {
            'timestamp': now.isoformat(),
            'new_rotations': len(new_rotations),
            'new_transactions': len(df_new_transactions),
            'skipped_existing': len(rotation_summary) - len(new_rotations),
            'files': {
                'summary': summary_file,
                'details': detail_file
            }
        }

        metadata_file = os.path.join(dirs['daily_dir'], f"metadata_{now.strftime('%Y%m%d_%H%M')}.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        console.print(f"[green]â Nouvelles rotations sauvegardÃ©es: {len(new_rotations)}/{len(rotation_summary)}[/green]")
        if len(rotation_summary) - len(new_rotations) > 0:
            console.print(f"[yellow]â­ï¸ Rotations dÃ©jÃ  existantes ignorÃ©es: {len(rotation_summary) - len(new_rotations)}[/yellow]")

        return {
            'summary_file': summary_file,
            'detail_file': detail_file,
            'metadata_file': metadata_file,
            'new_count': len(new_rotations)
        }

    except Exception as e:
        console.print(f"[yellow]â ï¸ Erreur sauvegarde dÃ©taillÃ©e: {e}[/yellow]")
        return None

def update_global_kpis(rotation_summary, dirs):
    """Met Ã  jour les KPIs globaux mensuels et annuels"""
    now = datetime.now()

    try:
        # Fichier KPIs globaux mensuels
        monthly_kpis_file = os.path.join(dirs['month_dir'], "kpis_monthly.json")

        # Charger les KPIs existants ou crÃ©er nouveau
        if os.path.exists(monthly_kpis_file):
            with open(monthly_kpis_file, 'r', encoding='utf-8') as f:
                monthly_data = json.load(f)
        else:
            monthly_data = {
                'month': now.strftime('%Y-%m'),
                'rotations': [],
                'kpis': {
                    'total_invested': 0,
                    'total_final': 0,
                    'total_profit': 0,
                    'roi_global': 0,
                    'avg_margin': 0,
                    'total_rotations': 0
                },
                'last_updated': now.isoformat()
            }

        # Ajouter les nouvelles rotations (Ã©viter les doublons par Rotation_ID)
        existing_rotation_ids = {r['Rotation_ID'] for r in monthly_data['rotations']}
        new_rotations = [r for r in rotation_summary if r['Rotation_ID'] not in existing_rotation_ids]

        if len(new_rotations) != len(rotation_summary):
            skipped = len(rotation_summary) - len(new_rotations)
            console.print(f"[yellow]â­ï¸ KPIs globaux: {skipped} rotation(s) dÃ©jÃ  existante(s) ignorÃ©e(s)[/yellow]")

        monthly_data['rotations'].extend(new_rotations)
        monthly_data['last_updated'] = now.isoformat()

        # Recalculer les KPIs globaux
        all_rotations = monthly_data['rotations']
        if all_rotations:
            total_invested = sum(r['EUR_Invested'] for r in all_rotations)
            total_final = sum(r['EUR_Final'] for r in all_rotations)
            total_profit = sum(r['EUR_Profit'] for r in all_rotations)

            monthly_data['kpis'] = {
                'total_invested': round(total_invested, 2),
                'total_final': round(total_final, 2),
                'total_profit': round(total_profit, 2),
                'roi_global': round((total_profit / total_invested * 100) if total_invested > 0 else 0, 2),
                'avg_margin': round(sum(r['Profit_Pct'] for r in all_rotations) / len(all_rotations), 2),
                'total_rotations': len(all_rotations)
            }

        # Sauvegarder
        with open(monthly_kpis_file, 'w', encoding='utf-8') as f:
            json.dump(monthly_data, f, indent=2, ensure_ascii=False)

        return monthly_kpis_file

    except Exception as e:
        console.print(f"[yellow]â ï¸ Erreur mise Ã  jour KPIs globaux: {e}[/yellow]")
        return None

def display_compact_summary(rotation_summary, show_details_for_rotation=None):
    """Affichage compact avec option de dÃ©tail pour une rotation spÃ©cifique"""

    if not rotation_summary:
        console.print("[bold red]Aucune rotation analysable[/bold red]")
        return

    df_rotations = pd.DataFrame(rotation_summary)

    total_invested = df_rotations['EUR_Invested'].sum()
    total_final = df_rotations['EUR_Final'].sum()
    total_profit_eur = df_rotations['EUR_Profit'].sum()
    avg_margin = df_rotations['Profit_Pct'].mean()
    total_rotations = len(df_rotations)
    roi_global = (total_profit_eur / total_invested * 100) if total_invested > 0 else 0

    # Panel de performance globale
    console.print(Panel(f"Rapport gÃ©nÃ©rÃ© le {datetime.now().strftime('%d/%m/%Y Ã  %H:%M:%S')}",
                       title="[bold]Analyse FinanciÃ¨re P2P[/bold]", border_style="blue"))

    kpi_panel = Panel(
        f"  - [bold]Capital Initial :[/bold] [cyan]{total_invested:,.2f} EUR[/cyan]\n"
        f"  - [bold]Capital Final :[/bold] [blue]{total_final:,.2f} EUR[/blue]\n"
        f"  - [bold]Profit Net Total :[/bold] [bold green]{total_profit_eur:+,.2f} EUR[/bold green]\n"
        f"  - [bold]ROI Global :[/bold] [bold magenta]{roi_global:.2f}%[/bold magenta]\n"
        f"  - [bold]Marge Moyenne :[/bold] [bold blue]{avg_margin:.2f}%[/bold blue]\n"
        f"  - [bold]Rotations ComplÃ¨tes :[/bold] [cyan]{total_rotations}[/cyan]",
        title="[bold]Performance Globale[/bold]", border_style="green"
    )
    console.print(kpi_panel)

    # Tableau rÃ©capitulatif des rotations (toujours affichÃ©)
    table = Table(title="[bold blue]RÃ©capitulatif des Rotations[/bold blue]")
    table.add_column("Rotation", style="cyan")
    table.add_column("Date", style="magenta")
    table.add_column("Capital Initial", style="yellow", justify="right")
    table.add_column("Capital Final", style="green", justify="right")
    table.add_column("Profit EUR", justify="right")
    table.add_column("Marge %", justify="right")
    table.add_column("Nb Trans", justify="center")

    for _, row in df_rotations.iterrows():
        profit_style = "bold green" if row['EUR_Profit'] >= 0 else "bold red"
        margin_style = "bold green" if row['Profit_Pct'] >= 0 else "bold red"

        table.add_row(
            row['Rotation_ID'],
            str(row['Date'])[:10],
            f"{row['EUR_Invested']:,.2f}",
            f"{row['EUR_Final']:,.2f}",
            f"[{profit_style}]{row['EUR_Profit']:+,.2f}[/{profit_style}]",
            f"[{margin_style}]{row['Profit_Pct']:.2f}%[/{margin_style}]",
            str(int(row['Nb_Transactions']))
        )

    console.print(table)

    # Message informatif sur les rapports dÃ©taillÃ©s
    console.print(f"\n[dim]ð¾ Les dÃ©tails complets des transactions sont sauvegardÃ©s dans les rapports dÃ©taillÃ©s.[/dim]")
    console.print(f"[dim]ð Pour voir les dÃ©tails d'une rotation spÃ©cifique, utilisez: --detail ROTATION_ID[/dim]")

def analyze_transactions(csv_path, mode='compact', specific_rotation=None):
    """
    Analyse les transactions avec différents modes d'affichage

    Args:
        csv_path: Chemin vers le fichier CSV
        mode: 'compact' (défaut), 'detail' (pour une rotation spécifique)
        specific_rotation: ID de rotation pour affichage détaillé
    """

    # 1. Lecture et nettoyage
    try:
        df = safe_read_csv_kpis(csv_path)
        console.print(f"[green]✅ Fichier lu avec succès: {len(df)} lignes[/green]")
        df = clean_and_validate_data(df)
    except Exception as e:
        console.print(f"[bold red]ERREUR: {e}[/bold red]")
        return

    # Filtrer les données valides
    df_filtered = df[df['Rotation_ID'] != 'N/A'].copy()
    if df_filtered.empty:
        console.print("[bold yellow]Aucune rotation trouvée[/bold yellow]")
        return

    console.print(f"[blue]📊 Analyse de {len(df_filtered)} transactions sur {df_filtered['Rotation_ID'].nunique()} rotations[/blue]")

    # 2. CALCUL PAR ROTATION
    rotation_summary = []

    for rotation_id, group in df_filtered.groupby('Rotation_ID'):
        try:
            achats = group[group['Type'] == 'ACHAT']
            conversions = group[group['Type'] == 'CONVERSION']

            if achats.empty:
                logging.warning(f"Rotation {rotation_id}: Pas d'achat trouvé")
                continue

            # Capital investi = Somme des ACHATS en EUR
            capital_investi_eur = 0
            usdt_total_investi = 0

            for _, achat in achats.iterrows():
                currency = str(achat['Currency']).strip()

                if currency != 'EUR':
                    console.print(f"[yellow]⚠️ Rotation {rotation_id}: Achat en {currency} ignoré (non EUR)[/yellow]")
                    continue

                montant_eur = float(achat['Amount_Local'])
                usdt_achete = float(achat['Amount_USDT'])

                if montant_eur <= 0 or usdt_achete <= 0:
                    continue

                capital_investi_eur += montant_eur
                usdt_total_investi += usdt_achete

            if capital_investi_eur <= 0:
                logging.warning(f"Rotation {rotation_id}: Capital investi invalide")
                continue

            # CORRECTION : Capital final = Somme des CONVERSIONS vers EUR
            capital_final_eur = 0

            for _, conversion in conversions.iterrows():
                currency = str(conversion['Currency']).strip()

                if currency == 'EUR':
                    montant_eur = float(conversion['Amount_Local'])
                    if montant_eur > 0:
                        capital_final_eur += montant_eur

            # VALIDATION cohérence Amount_USDT des conversions
            for _, conversion in conversions.iterrows():
                usdt_conversion = float(conversion.get('Amount_USDT', 0))
                if usdt_conversion > usdt_total_investi * 1.5:
                    console.print(
                        f"[yellow]⚠️ Rotation {rotation_id}: Amount_USDT suspect dans conversion "
                        f"({usdt_conversion:.2f} vs {usdt_total_investi:.2f} investi)[/yellow]"
                    )
                    logging.warning(
                        f"Rotation {rotation_id}: Incohérence Amount_USDT conversion "
                        f"({usdt_conversion} vs {usdt_total_investi} investi)"
                    )

            if capital_final_eur <= 0:
                console.print(f"[yellow]⚠️ Rotation {rotation_id}: Pas de conversion finale en EUR trouvée[/yellow]")
                continue

            # Calcul du profit
            profit_eur = capital_final_eur - capital_investi_eur
            profit_pct = (profit_eur / capital_investi_eur * 100)

            # Seuils de validation ajustés
            if profit_pct < -95:
                logging.warning(f"Rotation {rotation_id}: Perte anormale {profit_pct:.2f}%")
                console.print(f"[red]⚠️ Rotation {rotation_id}: Perte de {profit_pct:.2f}% détectée[/red]")

            if profit_pct > 500:
                logging.warning(f"Rotation {rotation_id}: Profit aberrant {profit_pct:.2f}%")
                console.print(f"[red]⚠️ Rotation {rotation_id}: Profit suspect de {profit_pct:.2f}%[/red]")
                continue

            rotation_summary.append({
                "Rotation_ID": rotation_id,
                "Date": group['Date'].iloc[0] if not group.empty else 'N/A',
                "USDT_Invested": round(usdt_total_investi, 2),
                "EUR_Invested": round(capital_investi_eur, 2),
                "EUR_Final": round(capital_final_eur, 2),
                "EUR_Profit": round(profit_eur, 2),
                "Profit_Pct": round(profit_pct, 2),
                "Nb_Transactions": len(group)
            })

        except Exception as e:
            console.print(f"[bold red]Erreur rotation {rotation_id}: {e}[/bold red]")
            logging.error(f"Erreur rotation {rotation_id}: {e}", exc_info=True)
            continue

    # 3. GESTION DES RAPPORTS
    dirs = create_detailed_reports_structure()

    saved_files = save_detailed_transaction_report(df_filtered, rotation_summary, dirs)
    global_kpis_file = update_global_kpis(rotation_summary, dirs)

    # 4. AFFICHAGE SELON LE MODE
    if mode == 'compact':
        display_compact_summary(rotation_summary)
    elif mode == 'detail' and specific_rotation:
        display_compact_summary(rotation_summary)
        show_rotation_details(df_filtered, specific_rotation)

    # 5. MESSAGES DE CONFIRMATION
    if saved_files and saved_files.get('new_count', 0) > 0:
        console.print(f"\n[green]✅ Rapports détaillés sauvegardés ({saved_files['new_count']} nouvelles rotations):[/green]")
        console.print(f"  📄 Résumé: {saved_files['summary_file']}")
        console.print(f"  📋 Détails: {saved_files['detail_file']}")
        console.print(f"  📊 Métadonnées: {saved_files['metadata_file']}")
    elif saved_files and saved_files.get('new_count', 0) == 0:
        console.print(f"\n[blue]ℹ️ Toutes les rotations étaient déjà sauvegardées aujourd'hui[/blue]")

    if global_kpis_file:
        console.print(f"  📄 KPIs globaux: {global_kpis_file}")

def show_rotation_details(df_filtered, rotation_id):
    """Affiche les dÃ©tails d'une rotation spÃ©cifique"""
    rotation_data = df_filtered[df_filtered['Rotation_ID'] == rotation_id]

    if rotation_data.empty:
        console.print(f"[bold red]Rotation {rotation_id} non trouvÃ©e[/bold red]")
        return

    console.print(f"\n[bold cyan]ð DÃ©tails de la Rotation {rotation_id}[/bold cyan]")

    trans_table = Table()
    trans_table.add_column("Date", style="magenta")
    trans_table.add_column("Type", style="yellow")
    trans_table.add_column("MarchÃ©", style="cyan")
    trans_table.add_column("USDT", justify="right")
    trans_table.add_column("Local", justify="right")
    trans_table.add_column("Notes", style="dim")

    for _, row in rotation_data.iterrows():
        usdt_str = f"{float(row['Amount_USDT']):.2f}" if row['Amount_USDT'] > 0 else "-"
        local_str = f"{float(row['Amount_Local']):.2f}" if row['Amount_Local'] > 0 else "-"

        trans_table.add_row(
            str(row['Date'])[:10],
            str(row['Type']),
            str(row['Market']),
            usdt_str,
            local_str,
            str(row['Notes'])[:40]
        )

    console.print(trans_table)
def diagnose_rotation_data(csv_path, rotation_id):
    """
    Diagnostic détaillé d'une rotation pour identifier les incohérences
    Usage: diagnose_rotation_data('transactions.csv', 'R20250930-1')
    """
    df = safe_read_csv_kpis(csv_path)
    rotation_data = df[df['Rotation_ID'] == rotation_id]

    if rotation_data.empty:
        console.print(f"[red]Rotation {rotation_id} non trouvée[/red]")
        return

    console.print(f"\n[bold cyan]🔍 DIAGNOSTIC DE LA ROTATION {rotation_id}[/bold cyan]")
    console.print("="*60)

    # Analyse par type de transaction
    for trans_type in ['ACHAT', 'VENTE', 'CONVERSION']:
        trans = rotation_data[rotation_data['Type'] == trans_type]
        if not trans.empty:
            console.print(f"\n[yellow]{trans_type} ({len(trans)} transaction(s)):[/yellow]")
            for _, row in trans.iterrows():
                usdt = float(row.get('Amount_USDT', 0))
                local = float(row.get('Amount_Local', 0))
                currency = row.get('Currency', 'N/A')

                # Vérifications spécifiques aux conversions
                if trans_type == 'CONVERSION':
                    # Vérifier si Amount_USDT semble être en devise locale
                    if usdt > 100000:  # Probablement en XAF
                        console.print(f"  [red]⚠️ Amount_USDT={usdt:.2f} semble être en XAF[/red]")
                    console.print(f"  - {currency}: {usdt:.2f} USDT → {local:.2f} {currency}")
                else:
                    console.print(f"  - {currency}: {usdt:.2f} USDT ↔ {local:.2f} {currency}")

    # Calcul de cohérence
    total_usdt_in = rotation_data[rotation_data['Type'] == 'ACHAT']['Amount_USDT'].sum()
    total_eur_in = rotation_data[
        (rotation_data['Type'] == 'ACHAT') & (rotation_data['Currency'] == 'EUR')
    ]['Amount_Local'].sum()

    total_eur_out = rotation_data[
        (rotation_data['Type'] == 'CONVERSION') & (rotation_data['Currency'] == 'EUR')
    ]['Amount_Local'].sum()

    console.print(f"\n[bold]Résumé:[/bold]")
    console.print(f"  Capital investi: {total_eur_in:.2f} EUR ({total_usdt_in:.2f} USDT)")
    console.print(f"  Capital final: {total_eur_out:.2f} EUR")
    console.print(f"  Profit: {total_eur_out - total_eur_in:+.2f} EUR ({((total_eur_out - total_eur_in) / total_eur_in * 100):.2f}%)")
    console.print("="*60)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Analyse des performances P2P')
    parser.add_argument('--detail', type=str, help='Afficher les dÃ©tails pour une rotation spÃ©cifique')
    parser.add_argument('--file', type=str, default='transactions.csv', help='Fichier CSV Ã  analyser')

    args = parser.parse_args()

    console = Console()
    console.print("[bold blue]ð ANALYSE DES PERFORMANCES P2P[/bold blue]")
    console.print("="*50)

    if args.detail:
        analyze_transactions(args.file, mode='detail', specific_rotation=args.detail)
    else:
        analyze_transactions(args.file, mode='compact')

