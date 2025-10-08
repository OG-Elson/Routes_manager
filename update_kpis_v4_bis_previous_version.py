# update_kpis_corrected.py

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
    """Lecture CSV sécurisée avec fallback d'encodage"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Fichier non trouvé: {csv_path}")
    
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
    """Nettoie et valide les données du DataFrame"""
    df = df.fillna('')
    
    numeric_columns = ['Amount_USDT', 'Price_Local', 'Fee_Pct', 'Amount_Local']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if col in ['Amount_USDT', 'Amount_Local']:
                df[col] = df[col].apply(lambda x: max(0, x))
    
    return df

def analyze_transactions(csv_path, show_transaction_details=False):
    """
    LOGIQUE CORRIGÉE :
    - Capital Investi = Somme des ACHATS en EUR
    - Capital Final = Somme des CONVERSIONS vers EUR (dernière étape)
    - Profit = Capital Final - Capital Investi
    
    On ignore les montants intermédiaires en devises locales.
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

    # 2. CALCUL CORRIGÉ PAR ROTATION
    rotation_summary = []
    
    for rotation_id, group in df_filtered.groupby('Rotation_ID'):
        try:
            achats = group[group['Type'] == 'ACHAT']
            conversions = group[group['Type'] == 'CONVERSION']

            if achats.empty:
                logging.warning(f"Rotation {rotation_id}: Pas d'achat trouvé")
                continue
            
            # ============================================
            # CAPITAL INVESTI = Somme des ACHATS en EUR
            # ============================================
            capital_investi_eur = 0
            usdt_total_investi = 0
            
            for _, achat in achats.iterrows():
                currency = str(achat['Currency']).strip()
                
                # Vérifier que c'est bien un achat en EUR
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
            
            # ====================================================
            # CAPITAL FINAL = Somme des CONVERSIONS vers EUR
            # ====================================================
            capital_final_eur = 0
            
            for _, conversion in conversions.iterrows():
                currency = str(conversion['Currency']).strip()
                
                # Ne compter QUE les conversions qui aboutissent en EUR
                if currency == 'EUR':
                    montant_eur = float(conversion['Amount_Local'])
                    if montant_eur > 0:
                        capital_final_eur += montant_eur
            
            # Si pas de conversion trouvée, on ne peut pas calculer le profit
            if capital_final_eur <= 0:
                console.print(f"[yellow]⚠️ Rotation {rotation_id}: Pas de conversion finale en EUR trouvée[/yellow]")
                continue
            
            # ====================================================
            # CALCUL DU PROFIT
            # ====================================================
            profit_eur = capital_final_eur - capital_investi_eur
            profit_pct = (profit_eur / capital_investi_eur * 100)
            
            # Validation des résultats
            if profit_pct < -95 or profit_pct > 500:
                logging.warning(f"Rotation {rotation_id}: Profit aberrant {profit_pct:.2f}%")
                continue
            
            rotation_summary.append({
                "Rotation_ID": rotation_id,
                "Date": group['Date'].iloc[0] if not group.empty else 'N/A',
                "USDT_Invested": round(usdt_total_investi,2),
                "EUR_Invested": round(capital_investi_eur,2),
                "EUR_Final": round(capital_final_eur,2),
                "EUR_Profit": round(profit_eur,2),
                "Profit_Pct": round(profit_pct,2),
                "Nb_Transactions": len(group)
            })
            
        except Exception as e:
            console.print(f"[bold red]Erreur rotation {rotation_id}: {e}[/bold red]")
            logging.error(f"Erreur rotation {rotation_id}: {e}", exc_info=True)
            continue
    
    # 3. AFFICHAGE
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
    
    console.print(Panel(f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}", 
                       title="[bold]Analyse Financière P2P[/bold]", border_style="blue"))
    
    kpi_panel = Panel(
        f"  - [bold]Capital Initial :[/bold] [cyan]{total_invested:,.2f} EUR[/cyan]\n"
        f"  - [bold]Capital Final :[/bold] [blue]{total_final:,.2f} EUR[/blue]\n"
        f"  - [bold]Profit Net Total :[/bold] [bold green]{total_profit_eur:+,.2f} EUR[/bold green]\n"
        f"  - [bold]ROI Global :[/bold] [bold magenta]{roi_global:.2f}%[/bold magenta]\n"
        f"  - [bold]Marge Moyenne :[/bold] [bold blue]{avg_margin:.2f}%[/bold blue]\n"
        f"  - [bold]Rotations Complètes :[/bold] [cyan]{total_rotations}[/cyan]",
        title="[bold]Performance Globale[/bold]", border_style="green"
    )
    console.print(kpi_panel)

    # Table détaillée
    table = Table(title="[bold blue]Détail par Rotation[/bold blue]")
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
    
    # Détails transactions si demandé
    if show_transaction_details:
        console.print("\n" + "="*50)
        console.print("[bold blue]DÉTAIL DES TRANSACTIONS[/bold blue]")
        console.print("="*50)
        
        for rotation_id, group in df_filtered.groupby('Rotation_ID'):
            console.print(f"\n[bold cyan]Rotation {rotation_id}[/bold cyan]")
            
            trans_table = Table()
            trans_table.add_column("Date", style="magenta")
            trans_table.add_column("Type", style="yellow")
            trans_table.add_column("Marché", style="cyan")
            trans_table.add_column("USDT", justify="right")
            trans_table.add_column("Local", justify="right")
            trans_table.add_column("Notes", style="dim")
            
            for _, row in group.iterrows():
                usdt_str = f"{float(row['Amount_USDT']):.2f}" if row['Amount_USDT'] > 0 else "-"
                local_str = f"{float(row['Amount_Local']):.2f}" if row['Amount_Local'] > 0 else "-"
                
                trans_table.add_row(
                    str(row['Date'])[:10],
                    str(row['Type']),
                    str(row['Market']),
                    usdt_str,
                    local_str,
                    str(row['Notes'])[:30]
                )
            
            console.print(trans_table)
    
    # Sauvegarder le rapport
    try:
        now = datetime.now()
        output_dir = os.path.join("reports", now.strftime("%Y"), now.strftime("%B"), f"Semaine_{now.strftime('%W')}")
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, f"rapport_kpis_{now.strftime('%Y%m%d_%H%M')}.csv")
        df_rotations.to_csv(output_file, sep=';', index=False, encoding='utf-8')
        console.print(f"\n[green]✅ Rapport sauvegardé: {output_file}[/green]")
        
    except Exception as e:
        console.print(f"[yellow]⚠️ Impossible de sauvegarder: {e}[/yellow]")

if __name__ == "__main__":
    console = Console()
    console.print("[bold blue]🔍 ANALYSE DES PERFORMANCES P2P[/bold blue]")
    console.print("="*50)
    
    analyze_transactions('transactions.csv', show_transaction_details=True)