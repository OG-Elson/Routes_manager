"""
Tests unitaires pour route_params_collector
Focus sur mocking inputs utilisateur
"""
from unittest.mock import patch

import pytest

from src.utils.route_params_collector import (collect_route_search_parameters,
                                              collect_simulation_parameters)

# Applique un timeout à tous les tests de ce module pour éviter les boucles infinies
pytestmark = pytest.mark.timeout(5.0)

# Le format des décorateurs est : input, Confirm, print.
# L'ordre des arguments doit être : mock_print, mock_confirm, mock_input.
# On peut aussi changer l'ordre des décorateurs pour correspondre aux arguments usuels, mais ici on s'adapte à l'ordre actuel pour être clair.

class TestCollectRouteSearchParameters:
    """Tests collecte paramètres recherche routes"""

    # NOTE: L'ordre des arguments est (mock_print, mock_confirm, mock_input)
    # pour correspondre à l'ordre inverse des décorateurs (input, Confirm, print)

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_valid_inputs_returns_dict(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Inputs valides retournent dict complet"""

        mock_confirm.return_value = False

        # Séquence d'entrées (4) : [Sourcing, Exclure (n), Bouclage (n), Conversion (défaut)]
        mock_input.side_effect = ['EUR', 'n', 'n', '']

        result = collect_route_search_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 4
        assert result is not None
        assert result['sourcing_currency'] == 'EUR'
        # CORRECTION KEY ERROR: Utiliser 'excluded_markets'
        assert result['excluded_markets'] == []
        assert result['loop_currency'] is None
        assert result['conversion_method'] == 'forex'

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_user_cancel_returns_none(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """User tape 'annuler' retourne None"""

        # Ajouter le mock_print pour la cohérence
        mock_input.side_effect = ['annuler']
        mock_confirm.return_value = True

        result = collect_route_search_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 1
        assert result is None

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_invalid_currency_asks_again(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Devise invalide est rejetée, la saisie est redemandée (5 appels)"""

        mock_confirm.return_value = False

        # Séquence d'entrées (5) : [Sourcing (invalide), Sourcing (valide), Exclure, Bouclage, Conversion]
        mock_input.side_effect = ['INVALID', 'EUR', 'n', 'n', '']

        result = collect_route_search_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 5
        assert result['sourcing_currency'] == 'EUR'

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_default_conversion_method(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Méthode de conversion par défaut si vide est 'forex'"""

        mock_confirm.return_value = False

        # Séquence d'entrées (4)
        mock_input.side_effect = ['EUR', 'n', 'n', '']

        result = collect_route_search_parameters(mock_markets, mock_config_valid)

        assert result['conversion_method'] == 'forex'

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_explicit_bank_conversion(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Méthode de conversion peut être forcée à 'bank' (4 appels)"""

        # Annulation et option de bouclage désactivées par défaut
        mock_confirm.return_value = False

        # Séquence de 4 inputs (minimum requis):
        # [Sourcing(EUR), Exclure(n), Bouclage(n), Conversion(bank)]
        mock_input.side_effect = ['EUR', 'n', 'n', 'bank']

        result = collect_route_search_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 4
        assert result['conversion_method'] == 'bank'

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_loop_currency_forced(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Forcer une devise de bouclage spécifique (XOF) (4 appels)"""

        # Le Confirm.ask() du code est utilisé pour demander si l'on veut forcer une devise de bouclage.
        mock_confirm.return_value = True
        # Séquence correcte (5 inputs) :
        # 1. Sourcing (EUR)
        # 2. Voulez-vous forcer bouclage ? (o)
        # 3. Devise de bouclage (XOF)
        # 4. Voulez-vous exclure ? (n)
        # 5. Conversion ('' = défaut)
        mock_input.side_effect = ['EUR', 'o', 'XOF', 'n', '']

        result = collect_route_search_parameters(mock_markets, mock_config_valid)

        assert result is not None, "La fonction ne doit pas retourner None car l'annulation est bloquée."
        assert mock_input.call_count == 5
        assert result['loop_currency'] == 'XOF'

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_exclusion_markets(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Exclure des marchés spécifiques (XOF, KES) (5 appels)"""

        # Annulation et option de bouclage désactivées par défaut
        mock_confirm.return_value = False

        # Séquence correcte (6 inputs) :
        # 1. Sourcing (EUR)
        # 2. Voulez-vous forcer bouclage ? (n)
        # 3. Voulez-vous exclure ? (o)
        # 4. Liste exclusion (XOF,KES)
        # 5. Conversion (invalide 'n')
        # 6. Conversion (valide '')
        mock_input.side_effect = ['EUR', 'n', 'o', 'XOF,KES', 'n', '']

        result = collect_route_search_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 6
        assert result['excluded_markets'] == ['XOF', 'KES']

# ---
class TestCollectSimulationParameters:
    """Tests collecte paramètres de simulation (inclut les paramètres de route)"""

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_valid_inputs_returns_dict(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Inputs valides retournent dict complet"""

        mock_confirm.return_value = False

        # Séquence d'entrées (6) : [Route x4, Capital (1000), Cycles (2)]
        mock_input.side_effect = ['EUR', 'n', 'n', '', '1000', '2']

        result = collect_simulation_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 6
        assert result['initial_capital'] == 1000.0
        assert result['nb_cycles'] == 2

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_includes_capital_and_cycles(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Vérifie l'inclusion des deux paramètres numériques"""

        mock_confirm.return_value = False

        # Séquence d'entrées (6) : [Route x4, Capital (500.5), Cycles (1)]
        mock_input.side_effect = ['EUR', 'n', 'n', '', '500.5', '1']

        result = collect_simulation_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 6
        assert result['initial_capital'] == 500.5
        assert result['nb_cycles'] == 1

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_invalid_inputs_retries_capital(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Input invalide (non-numérique) pour le capital redemande saisie, puis valide (7 appels)"""

        mock_confirm.return_value = False

        # Séquence d'entrées (7) : [Route x4, Capital (invalide 'abc'), Capital (valide), Cycles]
        mock_input.side_effect = ['EUR', 'n', 'n', '', 'abc', '1000', '2']

        result = collect_simulation_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 7
        assert result['initial_capital'] == 1000.0

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_whitespace_only_rejected(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Espaces uniquement rejeté (7 appels)"""

        mock_confirm.return_value = False

        # Séquence d'entrées (7) : [Route x4, Capital (invalide '   '), Capital (valide), Cycles]
        mock_input.side_effect = ['EUR', 'n', 'n', '', '   ', '1000', '2']

        result = collect_simulation_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 7
        assert result['initial_capital'] == 1000.0

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_empty_string_capital_rejected(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Chaîne vide ('') rejetée pour le capital (7 appels)"""

        mock_confirm.return_value = False

        # Séquence d'entrées (7) : [Route x4, Capital (invalide ''), Capital (valide), Cycles]
        mock_input.side_effect = ['EUR', 'n', 'n', '', '', '1000', '2']

        result = collect_simulation_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 7
        assert result['initial_capital'] == 1000.0

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_negative_capital_rejected(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Capital négatif (-100) rejeté (7 appels)"""

        mock_confirm.return_value = False

        # Séquence d'entrées (7) : [Route x4, Capital (invalide '-100'), Capital (valide), Cycles]
        mock_input.side_effect = ['EUR', 'n', 'n', '', '-100', '1000', '2']

        result = collect_simulation_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 7
        assert result['initial_capital'] == 1000.0

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_zero_cycles_rejected(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Zéro (0) cycles rejeté (7 appels)"""

        mock_confirm.return_value = False

        # Séquence d'entrées (7) : [Route x4, Capital (valide), Cycles (invalide '0'), Cycles (valide)]
        mock_input.side_effect = ['EUR', 'n', 'n', '', '1000', '0', '2']

        result = collect_simulation_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 7
        assert result['nb_cycles'] == 2

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_nan_value_rejected(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Valeur causant NaN (non-numérique) rejetée pour le capital (7 appels)"""

        mock_confirm.return_value = False

        # Séquence d'entrées (7) : [Route x4, Capital (invalide 'NaN'), Capital (valide), Cycles]
        mock_input.side_effect = ['EUR', 'n', 'n', '', 'NaN', '1000', '2']

        result = collect_simulation_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 7
        assert result['initial_capital'] == 1000.0

    @patch('src.utils.route_params_collector.console.input')
    @patch('rich.prompt.Confirm.ask')
    @patch('src.utils.route_params_collector.console.print')
    def test_comma_decimal_separator(self, mock_print, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Virgule comme séparateur décimal acceptée pour le capital (6 appels)"""

        mock_confirm.return_value = False

        # Séquence d'entrées (6) : [Route x4, Capital (1000,50), Cycles (2)]
        mock_input.side_effect = ['EUR', 'n', 'n', '', '1000,50', '2']

        result = collect_simulation_parameters(mock_markets, mock_config_valid)

        assert mock_input.call_count == 6
        assert result['initial_capital'] == 1000.5

