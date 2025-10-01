# daily_briefing.py
import csv
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime
import os
import sys
import json
import logging
import shutil
from rotation_manager import RotationManager
# --- CONFIGURATION DU LOGGING ---
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', encoding='utf-8')

# --- CHARGEMENT DE LA CONFIGURATION ---
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    SEUIL_RENTABILITE_PCT = config.get('SEUIL_RENTABILITE_PCT', 1.5)
    NB_CYCLES_PAR_ROTATION = config.get('NB_CYCLES_PAR_ROTATION', 3)
    markets = config.get('markets', [])
except (FileNotFoundError, KeyError) as e:
    logging.error(f"Fichier config.json manquant ou invalide. DÃ©tail: {e}")
    print(f"ERREUR: Fichier config.json manquant ou invalide. Consultez app.log.")
    exit()

# --- IMPORTATION DU MOTEUR ---
try:
    from arbitrage_engine_bis import find_best_routes
except ImportError:
    print("ERREUR: Le fichier 'arbitrage_engine_bis.py' est introuvable dans le mÃªme dossier.")
    exit()

console = Console()
TRANSACTIONS_FILE = 'transactions.csv'
DEBRIEFING_FILE = 'debriefing.csv'
PLAN_FILE_TPL = 'rotation_plan_{}.json'

# --- FONCTIONS DE SAISIE SÃCURISÃE ---
def get_confirmed_input(prompt, validation_func=None, error_msg="Saisie invalide."):
    while True:
        value = console.input(prompt)
        if value.lower() == 'annuler':
            if get_choice_input("Ãtes-vous sÃ»r de vouloir annuler ? (o/n) : ", ['o', 'n']) == 'o':
                logging.info("OpÃ©ration annulÃ©e par l'utilisateur.")
                return None
            else:
                continue
        if validation_func is None or validation_func(value):
            return value
        console.print(f"[bold red]{error_msg}[/bold red]")

def get_choice_input(prompt, choices):
    return get_confirmed_input(prompt, lambda v: v.lower() in choices, f"Choix invalide. Options : {', '.join(choices)}")

def get_numeric_input_safe(prompt, input_type=float, min_val=0):
    """Version ultra-sécurisée pour les inputs numériques critiques"""
    def is_valid_number(v):
        try:
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
        value_str = get_confirmed_input(
            prompt, 
            is_valid_number, 
            f"Nombre invalide (min: {min_val}, max: 1,000,000)"
        )
        if value_str is None:
            return None
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

def get_market_input(prompt, expected_market=None):
    valid_markets = [m['currency'] for m in markets]
    while True:
        value = console.input(prompt).upper()
        if value.lower() == 'annuler': return None
        if value in valid_markets:
            if expected_market and value != expected_market:
                console.print(f"[yellow]AVERTISSEMENT : Le plan prÃ©voit le marchÃ© '{expected_market}', mais vous avez entrÃ© '{value}'.[/yellow]")
                if get_choice_input("Voulez-vous continuer avec votre saisie ? (o/n) : ", ['o', 'n']) != 'o':
                    continue
            return value
        else:
            console.print(f"[bold red]MarchÃ© inconnu. MarchÃ©s valides : {', '.join(valid_markets)}[/bold red]")

# --- FONCTIONS DE GESTION DE FICHIERS CORRIGÃES ---
def robust_csv_append(filename, data_dict, max_retries=3):
    """Version ultra-robuste pour écriture CSV avec nettoyage des lignes vides"""
    # ORDRE FIXE ET CONTRÔLÉ DES COLONNES selon le fichier
    if 'transactions' in filename.lower():
        fieldnames = ['Date', 'Rotation_ID', 'Type', 'Market', 'Currency', 'Amount_USDT', 
                      'Price_Local', 'Amount_Local', 'Fee_Pct', 'Payment_Method', 
                      'Counterparty_ID', 'Notes']
    elif 'debriefing' in filename.lower():
        fieldnames = ['Date', 'Rotation_ID', 'Difficulte_Rencontree', 'Lecon_Apprise']
    else:
        fieldnames = list(data_dict.keys())
    
    backup_file = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    for attempt in range(max_retries):
        try:
            header_needed = not os.path.exists(filename)

            if os.path.exists(filename):
                shutil.copy2(filename, backup_file)
                
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                original_length = len(lines)
                while lines and (not lines[-1].strip() or lines[-1].strip() == '' or set(lines[-1].strip()) <= {';', ' ', '\t'}):
                    lines.pop()
                
                if len(lines) < original_length:
                    console.print(f"[yellow]Nettoyage: {original_length - len(lines)} ligne(s) vide(s) supprimée(s)[/yellow]")
                    logging.info(f"Lignes vides supprimées dans {filename}: {original_length - len(lines)}")
                
                if not lines:
                    header_needed = True
                else:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
            
            with open(filename, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                
                if header_needed:
                    writer.writeheader()
                
                missing_keys = set(fieldnames) - set(data_dict.keys())
                if missing_keys:
                    console.print(f"[yellow]ATTENTION: Clés manquantes dans les données : {missing_keys}[/yellow]")
                    for key in missing_keys:
                        data_dict[key] = "N/A"
                
                writer.writerow(data_dict)

            if os.path.exists(backup_file):
                os.remove(backup_file)
                
            logging.info(f"Ligne ajoutée avec succès au fichier {filename}.")
            return True
            
        except PermissionError:
            console.print(f"\n[bold red]FICHIER VERROUILLÉ[/bold red]")
            console.print(f"Le fichier '{filename}' est ouvert dans Excel ou un autre programme.")
            
            for retry in range(3):
                choice = get_choice_input(
                    f"Tentative {retry + 1}/3 - Fermer le fichier et taper 'o' pour continuer, 'n' pour annuler : ", 
                    ['o', 'n']
                )
                if choice == 'n':
                    if os.path.exists(backup_file):
                        if os.path.exists(filename):
                            os.remove(filename)
                        shutil.move(backup_file, filename)
                    return False
                
                try:
                    with open(filename, 'a', encoding='utf-8') as test_file:
                        break
                except PermissionError:
                    if retry == 2:
                        console.print("[bold red]Échec après 3 tentatives. Annulation.[/bold red]")
                        if os.path.exists(backup_file):
                            if os.path.exists(filename):
                                os.remove(filename)
                            shutil.move(backup_file, filename)
                        return False
                    continue
                
        except Exception as e:
            logging.error(f"Erreur écriture CSV tentative {attempt + 1}: {e}")
            console.print(f"[red]Tentative {attempt + 1} échouée : {e}[/red]")
            if attempt == max_retries - 1:
                if os.path.exists(backup_file):
                    if os.path.exists(filename):
                        os.remove(filename)
                    shutil.move(backup_file, filename)
                console.print(f"[bold red]ÉCHEC CRITIQUE écriture CSV: {e}[/bold red]")
                return False
            
    return False

def safe_read_csv(filename, encoding='utf-8'):
    """Lecture CSV sÃ©curisÃ©e avec fallback d'encodage"""
    try:
        return pd.read_csv(filename, sep=';', dtype=str, encoding=encoding)
    except UnicodeDecodeError:
        try:
            return pd.read_csv(filename, sep=';', dtype=str, encoding='utf-8-sig')
        except UnicodeDecodeError:
            return pd.read_csv(filename, sep=';', dtype=str, encoding='latin-1')
    except pd.errors.EmptyDataError:
        # Retourner un DataFrame vide avec les colonnes essentielles
        return pd.DataFrame(columns=['Date', 'Rotation_ID', 'Type', 'Market', 'Amount_USDT'])
    except FileNotFoundError:
        # Retourner un DataFrame vide si le fichier n'existe pas
        return pd.DataFrame(columns=['Date', 'Rotation_ID', 'Type', 'Market', 'Amount_USDT'])

def get_current_state():
    """Version sÃ©curisÃ©e de get_current_state"""
    try:
        df = safe_read_csv(TRANSACTIONS_FILE)
        
        if df.empty or 'Rotation_ID' not in df.columns:
            return {"rotation_id": None, "is_finished": True}
        
        valid_rotations = df.dropna(subset=['Rotation_ID'])
        if valid_rotations.empty:
            return {"rotation_id": None, "is_finished": True}
            
        last_rotation_id = valid_rotations['Rotation_ID'].iloc[-1]
        
        plan_file = PLAN_FILE_TPL.format(last_rotation_id)
        if not os.path.exists(plan_file):
            return {"rotation_id": None, "is_finished": True}
            
        try:
            with open(plan_file, 'r', encoding='utf-8') as f:
                plan = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as e:
            logging.error(f"Erreur lecture plan de vol {plan_file}: {e}")
            console.print(f"[yellow]ATTENTION: Plan de vol corrompu pour {last_rotation_id}[/yellow]")
            return {"rotation_id": None, "is_finished": True}
            
        rotation_df = df[df['Rotation_ID'] == last_rotation_id]
        completed_phases = len(rotation_df)
        plan_phases = plan.get('plan_de_vol', {}).get('phases', [])
        
        if completed_phases >= len(plan_phases):
            return {"rotation_id": last_rotation_id, "is_finished": True, "plan": plan}

        next_phase_details = plan_phases[completed_phases] if completed_phases < len(plan_phases) else None
        
        return {
            "rotation_id": last_rotation_id,
            "is_finished": False,
            "plan": plan,
            "next_phase_details": next_phase_details,
            "last_transaction": rotation_df.iloc[-1].to_dict() if not rotation_df.empty else None
        }
    except Exception as e:
        logging.error(f"Erreur critique dans get_current_state: {e}")
        console.print(f"[red]Erreur inattendue dans get_current_state: {e}[/red]")
        return {"rotation_id": None, "is_finished": True}
    
def generate_new_rotation_id(last_id):
    today_str = datetime.now().strftime("%Y%m%d")
    if last_id and today_str in last_id:
        parts = last_id.split('-')
        try:
            new_suffix = int(parts[-1]) + 1
        except (ValueError, IndexError):
            new_suffix = 1
        return f"R{today_str}-{new_suffix}"
    return f"R{today_str}-1"

# --- FONCTIONS DE L'ASSISTANT ---
def log_transaction(rotation_id, state):
    # Gestion spéciale pour la clôture de route
    if state.get('forced_closure', False) or (state.get('next_phase_details', {}).get('type') == 'CLOTURE'):
        console.print(f"[bold yellow]CLÔTURE DE LA ROUTE {rotation_id}[/bold yellow]")
        
        if state.get('forced_closure', False):
            closure_note = f"CLOTURE FORCEE - Motif: {state.get('closure_reason', 'Non spécifié')} - Route {rotation_id}"
        else:
            closure_note = f"Cloture normale de la route {rotation_id}"
        
        data = {
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Rotation_ID": rotation_id,
            "Type": "CLOTURE",
            "Market": "N/A",
            "Currency": "N/A",
            "Amount_USDT": "0.0000",
            "Price_Local": "0.0000",
            "Amount_Local": "0.0000",
            "Fee_Pct": "0.0000",
            "Payment_Method": "N/A",
            "Counterparty_ID": "N/A",
            "Notes": closure_note
        }
        
        if robust_csv_append(TRANSACTIONS_FILE, data):
            console.print(f"[green]✅ Clôture de route enregistrée[/green]")
            
            lecon = get_confirmed_input("Quelle leçon retenez-vous de cette rotation ? : ")
            if lecon:
                try:
                    df_debrief = safe_read_csv(DEBRIEFING_FILE)
                    if 'Leçon_Apprise' not in df_debrief.columns:
                        df_debrief['Leçon_Apprise'] = ''
                    
                    prefix = "FORCEE - " if state.get('forced_closure', False) else ""
                    df_debrief.loc[df_debrief['Rotation_ID'] == rotation_id, 'Leçon_Apprise'] = f"{prefix}{lecon.strip()}"
                    df_debrief.to_csv(DEBRIEFING_FILE, sep=';', index=False, encoding='utf-8')
                    console.print("[green]✅ Débriefing enregistré[/green]")
                except Exception as e:
                    logging.error(f"Erreur débriefing: {e}")
            
            console.print("[blue]Génération du rapport KPIs...[/blue]")
            try:
                from update_kpis_v4_bis import analyze_transactions
                analyze_transactions('transactions.csv', mode='compact')
            except Exception as e:
                console.print(f"[yellow]Erreur génération KPIs: {e}[/yellow]")
                logging.error(f"Erreur update_kpis: {e}")
            
            console.print(f"[bold cyan]Route {rotation_id} définitivement fermée[/bold cyan]")
        
        return
    
    phase_details = state.get('next_phase_details')
    if not phase_details:
        console.print("[bold red]Erreur : Impossible de déterminer la prochaine phase. Plan de vol manquant ou corrompu.[/bold red]")
        logging.error(f"Tentative de log pour {rotation_id} mais next_phase_details est manquant dans state.")
        return

    transaction_type = phase_details.get('type', 'INCONNU')
    cycle_num = phase_details.get('cycle', 'N/A')
    phase_num = phase_details.get('phase_in_cycle', 'N/A')

    panel_title = f"Rotation {rotation_id} / Cycle {cycle_num} / Phase {phase_num}"
    panel_content = f"[bold]Plan de Vol :[/bold] {state.get('plan', {}).get('detailed_route', 'N/A')}\n\n"
    
    last_trans = state.get('last_transaction')
    if last_trans:
        panel_content += f"[bold]--- Étape Précédente : {last_trans.get('Type','N/A')} --- [green]✅ TERMINÉ[/green][/bold]\n"
        panel_content += f"    - Montant : {float(last_trans.get('Amount_USDT', 0)):,.2f} USDT sur le marché {last_trans.get('Market', 'N/A')}\n\n"
    
    panel_content += f"[bold]--- Étape Actuelle : {transaction_type} --- [yellow]➡️ EN COURS[/yellow][/bold]\n"
    panel_content += f"    - Action Attendue : {phase_details.get('description', 'N/A')}"
    
    console.print(Panel(panel_content, title=panel_title))
    
    data = {
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"), 
        "Rotation_ID": rotation_id, 
        "Type": transaction_type,
        "Market": "N/A",
        "Currency": "N/A", 
        "Amount_USDT": 0.0,
        "Price_Local": 0.0,
        "Amount_Local": 0.0,
        "Fee_Pct": 0.0,
        "Payment_Method": "N/A",
        "Counterparty_ID": "N/A",
        "Notes": "N/A"
    }

    if transaction_type == "CONVERSION":
        market_from = phase_details.get('market_from', 'INCONNU')
        market_to = phase_details.get('market_to', 'INCONNU')
        
        console.print(f"[bold]Veuillez entrer les détails de la [yellow]CONVERSION[/yellow] (tapez 'annuler' pour quitter) :[/bold]")
        
        amount_sent = get_numeric_input_safe(f"\n> Montant en {market_from} envoyé : ")
        if amount_sent is None: return console.print("[yellow]Opération annulée.[/yellow]")
        
        amount_received = get_numeric_input_safe(f"> Montant en {market_to} reçu : ")
        if amount_received is None: return console.print("[yellow]Opération annulée.[/yellow]")

        rate = amount_sent / amount_received if amount_received > 0 else 0
        console.print(f"→ Le taux de change obtenu est de [bold cyan]{rate:,.4f} {market_from} / {market_to}[/bold cyan].")
        
        payment_method = get_confirmed_input("> Canal de Conversion (ex: Wise, Cash) : ")
        if payment_method is None: return console.print("[yellow]Opération annulée.[/yellow]")
        
        notes = get_confirmed_input("> Notes : ")
        if notes is None: return console.print("[yellow]Opération annulée.[/yellow]")

        # CORRECTION CRITIQUE : Récupérer le montant USDT du cycle
        usdt_in_cycle = 0
        
        if last_trans and last_trans.get('Amount_USDT'):
            usdt_in_cycle = float(last_trans['Amount_USDT'])
        else:
            console.print(f"[yellow]⚠️ Pas de montant USDT trouvé dans la transaction précédente[/yellow]")
            usdt_in_cycle = get_numeric_input_safe(
                f"> Montant USDT équivalent du cycle (pour traçabilité) : "
            )
            if usdt_in_cycle is None:
                usdt_in_cycle = 0

        data.update({
            "Market": f"{market_from}->{market_to}", 
            "Currency": market_to,
            "Amount_USDT": usdt_in_cycle,  # CORRIGÉ : Montant USDT du cycle
            "Price_Local": f"{rate:.3f}", 
            "Amount_Local": amount_received,
            "Fee_Pct": 0.0,
            "Payment_Method": payment_method.strip() if payment_method else "N/A", 
            "Counterparty_ID": "N/A", 
            "Notes": notes.strip() if notes else "N/A"
        })

    else:  # ACHAT, VENTE
        market = phase_details.get('market', 'INCONNU')
        
        console.print(f"[bold]Veuillez entrer les détails de la transaction [yellow]{transaction_type}[/yellow] (tapez 'annuler' pour quitter) :[/bold]")
        
        market_input = get_market_input(f"\n> Marché (prévu: {market}) : ", expected_market=market)
        if market_input is None: return console.print("[yellow]Opération annulée.[/yellow]")
    
        amount_usdt = get_numeric_input_safe(f"> Montant en USDT : ")
        if amount_usdt is None: return console.print("[yellow]Opération annulée.[/yellow]")
    
        amount_local = get_numeric_input_safe(f"> Montant en {market_input} : ")
        if amount_local is None: return console.print("[yellow]Opération annulée.[/yellow]")
    
        if amount_usdt > 0:
            calculated_price = round(amount_local / amount_usdt, 4)
        else:
            calculated_price = 0.0
            console.print("[yellow]ATTENTION: Division par zéro évitée, prix mis à 0[/yellow]")
            
        console.print(f"→ Le prix calculé est de [bold cyan]{calculated_price:,.4f} {market_input} / USDT[/bold cyan].")
    
        fee_pct = get_numeric_input_safe(f"> Frais en % : ")
        if fee_pct is None: return console.print("[yellow]Opération annulée.[/yellow]")
        
        payment_method = get_confirmed_input("> Moyen de Paiement : ")
        if payment_method is None: return console.print("[yellow]Opération annulée.[/yellow]")
    
        counterparty_id = get_confirmed_input("> ID de la Contrepartie : ")
        if counterparty_id is None: return console.print("[yellow]Opération annulée.[/yellow]")
    
        notes = get_confirmed_input("> Notes (ex: 'Cloture du Cycle 1') : ")
        if notes is None: return console.print("[yellow]Opération annulée.[/yellow]")

        data.update({
            "Market": market_input, 
            "Currency": market_input,
            "Amount_USDT": amount_usdt, 
            "Price_Local": f"{calculated_price:.4f}",
            "Amount_Local": amount_local, 
            "Fee_Pct": fee_pct,
            "Payment_Method": payment_method.strip() if payment_method else "N/A",
            "Counterparty_ID": counterparty_id.strip() if counterparty_id else "N/A",
            "Notes": notes.strip() if notes else "N/A"
        })
    
    console.print(f"\n[dim]DEBUG - Données à écrire: {data}[/dim]")
    
    if robust_csv_append(TRANSACTIONS_FILE, data):
        console.print(f"\n[green]✅ Transaction enregistrée avec succès.[/green]")
        
        notes_lower = data.get('Notes', '').lower()
        
        if 'cloture du cycle' in notes_lower or 'clôture du cycle' in notes_lower:
            manager = RotationManager()
            loop_currency = manager.get_loop_currency(rotation_id)
            
            if loop_currency:
                console.print(f"\n[bold yellow]FIN DE CYCLE détectée dans la note[/bold yellow]")
                console.print(f"Note: {data.get('Notes', '')}")
                console.print(f"Devise de bouclage configurée: {loop_currency}")
                
                choice = get_choice_input(
                    f"\nVoulez-vous BOUCLER un nouveau cycle en {loop_currency} ? (o/n) : ",
                    ['o', 'n']
                )
                
                if choice == 'o':
                    selling_currency = state.get('plan', {}).get('selling_market_code', 'XAF')
                    
                    if create_new_cycle_with_currency(rotation_id, loop_currency, selling_currency):
                        manager.increment_cycle(rotation_id)
                        console.print(f"\n[green]✅ Nouveau cycle ajouté ![/green]")
                        console.print(f"[cyan]→ Prochaine étape : ACHAT en {loop_currency}[/cyan]")
                    else:
                        console.print("[red]Échec de l'ajout du cycle[/red]")
                else:
                    console.print("[blue]Le cycle continuera normalement vers la clôture[/blue]")
            else:
                console.print(f"\n[yellow]⚠️ Cloture de cycle détectée mais aucune devise de bouclage n'est configurée[/yellow]")
                console.print("[dim]Utilisez: python daily_briefing.py --set-loop-currency DEVISE[/dim]")
        
        if "cloture" in data.get("Notes", "").lower():
            if "rotation" in data.get("Notes", "").lower(): 
                note = get_confirmed_input("\nRotation terminée. Quelle leçon avez-vous apprise ? : ") 
            else: 
                note = get_confirmed_input("\nCycle terminé. Quelle leçon avez-vous apprise ? : ")
            if note is not None:
                try:
                    df_debrief = safe_read_csv(DEBRIEFING_FILE)
                    if 'Leçon_Apprise' not in df_debrief.columns:
                         df_debrief['Leçon_Apprise'] = ''
                    df_debrief.loc[df_debrief['Rotation_ID'] == rotation_id, 'Leçon_Apprise'] = note.strip()
                    df_debrief.to_csv(DEBRIEFING_FILE, sep=';', index=False, encoding='utf-8')
                    console.print("[green]✅ Débriefing enregistré.[/green]")
                except Exception as e:
                    logging.error(f"Erreur lors de l'enregistrement du débriefing pour {rotation_id}", exc_info=True)
                    console.print(f"[red]Erreur lors de la sauvegarde du débriefing : {e}[/red]")
    else:
        console.print("[bold yellow]L'opération a été annulée. Aucune donnée n'a été sauvegardée.[/bold yellow]")

def plan_new_rotation(last_id):
    """
    Planifie une nouvelle rotation.
    Retourne toujours un tuple (new_rotation_id, plan) ou (None, None) en cas d'Ã©chec.
    """
    console.print("\n[yellow bold]-- ÃTAPE 1 : PLANIFICATION D'UNE NOUVELLE ROTATION --[/yellow bold]")
    console.print("Analyse des opportunitÃ©s de marchÃ© en cours...")
    
    try:
        best_routes = [r for r in find_best_routes() if r.get('profit_pct', 0) >= SEUIL_RENTABILITE_PCT]
    except Exception as e:
        console.print(f"[bold red]Erreur lors de l'analyse des routes: {e}[/bold red]")
        logging.error(f"Erreur find_best_routes: {e}")
        return None, None

    if not best_routes:
        console.print("[bold red]Aucune route dÃ©passant le seuil de rentabilitÃ© n'a Ã©tÃ© trouvÃ©e.[/bold red]")
        return None, None
    
    table = Table(title="[bold blue]Top 5 des Routes Rentables[/bold blue]")
    table.add_column("Choix", justify="center")
    table.add_column("Route", style="cyan")
    table.add_column("Marge (%)", justify="right", style="bold green")
    
    for i, route in enumerate(best_routes):
        table.add_row(f"[{i+1}]", route['detailed_route'], f"+{route['profit_pct']:.2f}%")
    console.print(table)
    
    choice_str = get_choice_input(f"Quelle route souhaitez-vous exÃ©cuter ? (Entrez 1-{len(best_routes)}) : ", [str(i+1) for i in range(len(best_routes))])
    if choice_str is None: return None, None
    choice = int(choice_str)
    chosen_route = best_routes[choice - 1]
    
    console.print("\n[yellow bold]-- CHECKLIST DE PRÃ-VOL --[/yellow bold]")
    if get_choice_input("Les partenaires nÃ©cessaires sont-ils disponibles ? (o/n) : ", ['o','n']) != 'o': return None, None
    if get_choice_input("Les comptes sont-ils au statut 'OK' dans network_health.csv ? (o/n) : ", ['o','n']) != 'o': return None, None
    if get_choice_input("Le 'Canari' de test a-t-il rÃ©ussi ? (o/n) : ", ['o','n']) != 'o': return None, None

    new_rotation_id = generate_new_rotation_id(last_id)
    plan_file = PLAN_FILE_TPL.format(new_rotation_id)
    try:
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(chosen_route, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Impossible de sauvegarder le plan de vol pour {new_rotation_id}: {e}")
        console.print(f"[red]Erreur sauvegarde plan: {e}[/red]")
        return None, None

    debrief_data = {
        "Date": datetime.now().strftime('%Y-%m-%d'), 
        "Rotation_ID": new_rotation_id, 
        "Difficulte_Rencontree": "", 
        "Lecon_Apprise": ""
    }
    if not robust_csv_append(DEBRIEFING_FILE, debrief_data):
        return None, None

    logging.info(f"Nouvelle rotation {new_rotation_id} planifiée avec la route {chosen_route['detailed_route']}.")
    console.print(f"â Rotation [cyan]'{new_rotation_id}'[/cyan] planifiée et prête.")
    
    return new_rotation_id, chosen_route

def handle_log_command(args):
    state = get_current_state()
    rotation_id = state.get('rotation_id')
    is_finished = state.get('is_finished')
    
    if is_finished or not rotation_id:
        console.print("[bold red]Aucune rotation en cours. Lancez d'abord l'assistant sans argument pour planifier.[/bold red]")
        return
        
    command_map = {'--log-achat': 'ACHAT', '--log-vente': 'VENTE', '--log-cloture': 'CLOTURE', '--log-conversion': 'CONVERSION'}
    
    if len(args) < 2 or args[1] not in command_map:
        console.print(f"[bold red]Commande non reconnue. Commandes valides : {', '.join(command_map.keys())}[/bold red]")
        return
        
    command_type = command_map[args[1]]
    expected_type = state.get('next_phase_details', {}).get('type')

    if command_type != expected_type:
        if command_type == 'CLOTURE':
            console.print(Panel(f"[bold yellow]CLÃTURE PRÃMATURÃE DÃTECTÃE[/bold yellow]\n"
                               f"Le plan de vol prÃ©voit un(e) '{expected_type}', mais vous demandez une clÃ´ture.",
                               title="Confirmation ClÃ´ture ForcÃ©e"))
            
            choice = get_choice_input("Tapez 'f' pour FORCER la clÃ´ture dÃ©finitive ou 'n' pour annuler : ", ['f', 'n'])
            if choice == 'n':
                return
            
            # ClÃ´ture forcÃ©e
            motif = get_confirmed_input("Motif de la clÃ´ture prÃ©maturÃ©e : ")
            if motif is None: return
            
            state['forced_closure'] = True
            state['closure_reason'] = motif.strip()
            
        else:
            console.print(Panel(f"[bold red]ERREUR DE SÃQUENCE[/bold red]\n"
                               f"Vous essayez de logger un(e) '{command_type}', mais le plan prÃ©voit un(e) '{expected_type}'.\n"
                               f"Utilisez --log-cloture pour forcer une clÃ´ture prÃ©maturÃ©e.",
                               title="Commande Incorrecte"))
            return
    
    log_transaction(rotation_id, state)





def handle_set_loop_currency_command(args):
    """DÃ©finit la devise sur laquelle boucler les cycles"""
    state = get_current_state()
    rotation_id = state.get('rotation_id')
    
    if state.get('is_finished') or not rotation_id:
        console.print("[bold red]Aucune rotation en cours.[/bold red]")
        return
    
    if len(args) < 3:
        console.print("[bold red]Usage: python daily_briefing.py --set-loop-currency DEVISE[/bold red]")
        console.print("Exemple: python daily_briefing.py --set-loop-currency XAF")
        return
    
    loop_currency = args[2].upper()
    
    # VÃ©rifier que la devise existe
    valid_currencies = [m['currency'] for m in markets]
    if loop_currency not in valid_currencies:
        console.print(f"[bold red]Devise invalide. Devises: {', '.join(valid_currencies)}[/bold red]")
        return
    
    console.print(Panel(
        f"[bold]CONFIGURATION DE LA DEVISE DE BOUCLAGE[/bold]\n\n"
        f"Rotation: [cyan]{rotation_id}[/cyan]\n"
        f"Devise de bouclage: [yellow]{loop_currency}[/yellow]\n\n"
        f"Lorsque vous mettrez 'Cloture du Cycle N' dans les notes,\n"
        f"le systÃ¨me vous proposera de crÃ©er un nouveau cycle qui:\n"
        f"  1. Commence par un ACHAT en {loop_currency}\n"
        f"  2. Se termine par une CONVERSION vers {loop_currency}\n\n"
        f"Vous bouclez ainsi sur la devise de votre choix !",
        title="Devise de Bouclage"
    ))
    
    choice = get_choice_input("Confirmer ? (o/n) : ", ['o', 'n'])
    if choice != 'o':
        console.print("[yellow]OpÃ©ration annulÃ©e[/yellow]")
        return
    
    manager = RotationManager()
    if manager.set_loop_currency(rotation_id, loop_currency):
        console.print(f"[green]â Devise de bouclage dÃ©finie : {loop_currency}[/green]")
        console.print(f"[dim]Lorsque vous mettrez 'Cloture du Cycle N' dans les notes, le bouclage sera proposÃ©[/dim]")
    else:
        console.print("[red]Erreur[/red]")
def handle_force_transaction_command(args):
    """Force une transaction diffÃ©rente de celle prÃ©vue"""
    state = get_current_state()
    rotation_id = state.get('rotation_id')
    
    if state.get('is_finished') or not rotation_id:
        console.print("[bold red]Aucune rotation en cours.[/bold red]")
        return
    
    if len(args) < 3:
        console.print("[bold red]Usage: python daily_briefing.py --force-transaction TYPE[/bold red]")
        console.print("Types: ACHAT, VENTE, CONVERSION")
        return
    
    forced_type = args[2].upper()
    valid_types = ['ACHAT', 'VENTE', 'CONVERSION']
    
    if forced_type not in valid_types:
        console.print(f"[bold red]Type invalide. Types: {', '.join(valid_types)}[/bold red]")
        return
    
    expected_type = state.get('next_phase_details', {}).get('type')
    
    console.print(Panel(
        f"[bold yellow]TRANSACTION FORCÃE[/bold yellow]\n\n"
        f"Type forcÃ©: [red]{forced_type}[/red]\n"
        f"Type attendu: [green]{expected_type}[/green]\n"
        f"Rotation: [cyan]{rotation_id}[/cyan]\n\n"
        f"Cette transaction remplacera l'Ã©tape prÃ©vue.\n"
        f"Le cycle continuera ensuite avec la prochaine phase.",
        title="ForÃ§age"
    ))
    
    choice = get_choice_input("Confirmer ? (o/n) : ", ['o', 'n'])
    if choice != 'o':
        console.print("[yellow]AnnulÃ©[/yellow]")
        return
    
    reason = get_confirmed_input("Raison du forÃ§age : ")
    if not reason:
        console.print("[yellow]AnnulÃ©[/yellow]")
        return
    
    # Enregistrer le forÃ§age
    manager = RotationManager()
    manager.record_forced_transaction(rotation_id, forced_type, reason)
    
    # Modifier l'Ã©tat pour logger
    state['next_phase_details']['type'] = forced_type
    state['next_phase_details']['description'] = f"[FORCÃ] {reason}"
    
    log_transaction(rotation_id, state)
    
    console.print(f"[green]â Transaction {forced_type} forcÃ©e[/green]")
def main():
    """
    Fonction principale pour le mode de planification (lorsque le script est lancÃ© sans argument).
    Elle gÃ¨re le dÃ©marrage, la reprise ou la planification d'une nouvelle rotation.
    """
    logging.info("Lancement de l'assistant en mode planification.")
    console.print("="*60, justify="center")
    console.print(f"ASSISTANT DE TRADING P2P - BRIEFING DU {datetime.now().strftime('%d/%m/%Y')}", justify="center")
    console.print("="*60, justify="center")

    state = get_current_state()
    rotation_id = state.get('rotation_id')
    is_finished = state.get('is_finished')
    
    # ScÃ©nario 1 : Une rotation est en cours
    if not is_finished and rotation_id:
        console.print(f"\nLa rotation [cyan]'{rotation_id}'[/cyan] est toujours en cours.")
        console.print(f"Prochaine Ã©tape attendue : [yellow]{state.get('next_phase_details', {}).get('description', 'N/A')}[/yellow]")
        choice = get_choice_input("Tapez [bold]1[/bold] pour CONTINUER (logger une transaction), ou [bold]2[/bold] pour lancer une NOUVELLE rotation : ", ['1','2'])
        
        if choice is None: # L'utilisateur a annulÃ©
            console.print("[yellow]OpÃ©ration annulÃ©e.[/yellow]")
            return
            
        if choice == '2':
            # L'utilisateur veut abandonner la rotation en cours pour en lancer une nouvelle
            new_id, new_plan = plan_new_rotation(rotation_id)
            if new_id and new_plan:
                console.print("[bold]Pour commencer, loggons la transaction de SOURCING.[/bold]")
                new_state = get_current_state()
                log_transaction(new_id, new_state)
        else: # choice == '1'
            # L'utilisateur veut logger la prochaine transaction de la rotation en cours
            log_transaction(rotation_id, state)
            
    # ScÃ©nario 2 : Aucune rotation en cours, on en planifie une nouvelle
    else:
        new_id, new_plan = plan_new_rotation(rotation_id)
        if new_id and new_plan:
            console.print("[bold]Pour commencer, loggons la transaction de SOURCING.[/bold]")
            # On construit l'objet 'state' manuellement avec le plan qu'on vient de recevoir
            state_for_new_rotation = {
                "rotation_id": new_id,
                "is_finished": False,
                "plan": new_plan,
                "next_phase_details": new_plan.get('plan_de_vol', {}).get('phases', [])[0] if new_plan.get('plan_de_vol', {}).get('phases') else None,
                "last_transaction": None
            }
            if state_for_new_rotation["next_phase_details"]:
                log_transaction(new_id, state_for_new_rotation)
            else:
                console.print("[red]Erreur: Plan de vol invalide, aucune phase dÃ©finie[/red]")

def create_new_cycle_with_currency(rotation_id, loop_currency, selling_currency):
    """CrÃ©e un nouveau cycle qui commence et finit avec loop_currency"""
    plan_file = PLAN_FILE_TPL.format(rotation_id)
    
    if not os.path.exists(plan_file):
        console.print(f"[red]Plan de vol introuvable[/red]")
        return False
    
    try:
        with open(plan_file, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        
        phases = plan.get('plan_de_vol', {}).get('phases', [])
        
        # Retirer la phase CLOTURE si elle existe
        phases = [p for p in phases if p.get('type') != 'CLOTURE']
        
        # Trouver le numÃ©ro du dernier cycle
        last_cycle = max([p.get('cycle', 1) for p in phases]) if phases else 1
        new_cycle_num = last_cycle + 1
        
        # CrÃ©er le nouveau cycle qui COMMENCE et FINIT avec loop_currency
        new_phases = [
            {
                'cycle': new_cycle_num,
                'phase_in_cycle': 1,
                'type': 'ACHAT',
                'market': loop_currency,
                'description': f"Cycle {new_cycle_num} - Achat avec {loop_currency}"
            },
            {
                'cycle': new_cycle_num,
                'phase_in_cycle': 2,
                'type': 'VENTE',
                'market': selling_currency,
                'description': f"Cycle {new_cycle_num} - Vente en {selling_currency}"
            },
            {
                'cycle': new_cycle_num,
                'phase_in_cycle': 3,
                'type': 'CONVERSION',
                'market_from': selling_currency,
                'market_to': loop_currency,
                'description': f"Cycle {new_cycle_num} - Conversion vers {loop_currency}"
            }
        ]
        
        phases.extend(new_phases)
        
        # Ajouter la phase CLOTURE finale
        phases.append({
            'cycle': new_cycle_num,
            'phase_in_cycle': 4,
            'type': 'CLOTURE',
            'market': loop_currency,
            'description': f"ClÃ´ture aprÃ¨s cycle {new_cycle_num}"
        })
        
        plan['plan_de_vol']['phases'] = phases
        
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Nouveau cycle {new_cycle_num} crÃ©Ã© avec devise de bouclage: {loop_currency}")
        return True
        
    except Exception as e:
        logging.error(f"Erreur crÃ©ation cycle: {e}")
        return False
if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command in ['--log-achat', '--log-vente', '--log-cloture', '--log-conversion']:
                logging.info(f"Commande logging: {command}")
                handle_log_command(sys.argv)
            
            elif command == '--set-loop-currency':
                logging.info("Commande configuration devise de bouclage")
                handle_set_loop_currency_command(sys.argv)
            
            elif command == '--force-transaction':
                logging.info("Commande forÃ§age de transaction")
                handle_force_transaction_command(sys.argv)
                
            # ✅ NOUVELLE COMMANDE SIMULATION
            elif command == '--simulation':
                logging.info("Lancement du module de simulation")
                console.print("[cyan]Lancement du module de simulation...[/cyan]\n")
                try:
                    # Import dynamique pour éviter les dépendances circulaires
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(
                        "simulation_module", 
                        "modules/simulation_module.py"
                    )
                    simulation_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(simulation_module)
                    
                    # Lancer la simulation
                    simulation_module.main()
                    
                except FileNotFoundError:
                    console.print("[bold red]❌ Fichier simulation_module.py introuvable dans modules/[/bold red]")
                    console.print("[dim]Assurez-vous que modules/simulation_module.py existe[/dim]")
                except Exception as e:
                    console.print(f"[bold red]❌ Erreur simulation: {e}[/bold red]")
                    logging.error(f"Erreur module simulation: {e}", exc_info=True)
            
            
            else:
                console.print(f"[bold red]Commande inconnue: {command}[/bold red]")
                console.print("\nCommandes disponibles:")
                console.print("  --log-achat, --log-vente, --log-conversion, --log-cloture")
                console.print("  --set-loop-currency DEVISE")
                console.print("  --force-transaction TYPE")
        else:
            main()
            
    except KeyboardInterrupt:
        console.print("\n[yellow]OpÃ©ration interrompue par l'utilisateur[/yellow]")
        logging.info("Script interrompu par l'utilisateur")
    except Exception as e:
        console.print("[bold red]Une erreur critique est survenue.[/bold red]")
        console.print("Consultez [cyan]app.log[/cyan] pour les dÃ©tails.")
        logging.critical(f"Erreur non gÃ©rÃ©e: {e}", exc_info=True)