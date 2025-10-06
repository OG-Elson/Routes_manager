"""
Tests unitaires pour route_params_collector
Focus sur mocking inputs utilisateur
"""
import pytest
from unittest.mock import patch, MagicMock
from src.utils.route_params_collector import (
    collect_route_search_parameters,
    collect_simulation_parameters
)


class TestCollectRouteSearchParameters:
    """Tests collecte paramètres recherche routes"""
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_valid_inputs_returns_dict(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Inputs valides retournent dict complet"""
        # Mock sequence: sourcing, exclusion(n), loop(n), conversion(vide=default)
        mock_input.side_effect = ['EUR', '', '']
        mock_confirm.side_effect = [False, False]  # exclusion=n, loop=n
        
        result = collect_route_search_parameters(mock_markets, mock_config_valid)
        
        assert result is not None
        assert result['sourcing_currency'] == 'EUR'
        assert result['soft_excluded'] == []
        assert result['loop_currency'] is None
        assert result['conversion_method'] == 'forex'  # default
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_user_cancel_returns_none(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """User tape 'annuler' retourne None"""
        mock_input.side_effect = ['annuler']
        mock_confirm.return_value = True  # Confirme annulation
        
        result = collect_route_search_parameters(mock_markets, mock_config_valid)
        
        assert result is None
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_invalid_currency_asks_again(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Devise invalide redemande saisie"""
        # Premier input invalide, second valide
        mock_input.side_effect = ['INVALID', 'EUR', '', '']
        mock_confirm.side_effect = [False, False]
        
        result = collect_route_search_parameters(mock_markets, mock_config_valid)
        
        assert result is not None
        assert result['sourcing_currency'] == 'EUR'
        # Vérifie que input a été appelé au moins 2 fois
        assert mock_input.call_count >= 2
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_default_conversion_method(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Entrée vide utilise default_conversion_method"""
        mock_input.side_effect = ['EUR', '', '']  # Conversion = vide
        mock_confirm.side_effect = [False, False]
        
        result = collect_route_search_parameters(mock_markets, mock_config_valid)
        
        assert result['conversion_method'] == 'forex'  # default du config
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_explicit_bank_conversion(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """User choisit explicitement 'bank'"""
        mock_input.side_effect = ['EUR', '', 'bank']
        mock_confirm.side_effect = [False, False]
        
        result = collect_route_search_parameters(mock_markets, mock_config_valid)
        
        assert result['conversion_method'] == 'bank'
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_exclusion_markets(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Exclusion de marchés fonctionne"""
        mock_input.side_effect = ['EUR', 'XAF, XOF', '', '']  # Exclure XAF et XOF
        mock_confirm.side_effect = [True, False]  # exclusion=o, loop=n
        
        result = collect_route_search_parameters(mock_markets, mock_config_valid)
        
        assert 'XAF' in result['soft_excluded']
        assert 'XOF' in result['soft_excluded']
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_loop_currency_with_exclusion(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Loop currency + exclusion ensemble"""
        mock_input.side_effect = ['EUR', 'XAF', 'XAF', '']  # Exclure XAF, loop=XAF
        mock_confirm.side_effect = [True, True]  # exclusion=o, loop=o
        
        result = collect_route_search_parameters(mock_markets, mock_config_valid)
        
        assert 'XAF' in result['soft_excluded']
        assert result['loop_currency'] == 'XAF'  # Priorité loop


class TestCollectSimulationParameters:
    """Tests collecte paramètres simulation"""
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_includes_capital_and_cycles(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Retourne capital + nb_cycles en plus"""
        mock_input.side_effect = [
            'EUR',           # sourcing
            '1000',          # capital
            '3',             # cycles
            '',              # exclusion vide
            '',              # loop vide
            ''               # conversion vide
        ]
        mock_confirm.side_effect = [False, False]  # exclusion=n, loop=n
        
        result = collect_simulation_parameters(mock_markets, mock_config_valid)
        
        assert result is not None
        assert 'initial_capital' in result
        assert 'nb_cycles' in result
        assert result['initial_capital'] == 1000.0
        assert result['nb_cycles'] == 3
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_nan_value_rejected(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Valeur NaN/Infini rejetée"""
        mock_input.side_effect = [
            'EUR',
            'inf',           # Capital invalide (infini)
            '1000',          # Capital valide
            '2',
            '',
            '',
            ''
        ]
        mock_confirm.side_effect = [False, False]
        
        result = collect_simulation_parameters(mock_markets, mock_config_valid)
        
        assert result is not None
        assert result['initial_capital'] == 1000.0
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_negative_capital_rejected(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Capital négatif rejeté"""
        mock_input.side_effect = [
            'EUR',
            '-500',          # Invalide
            '1000',          # Valide
            '2',
            '',
            '',
            ''
        ]
        mock_confirm.side_effect = [False, False]
        
        result = collect_simulation_parameters(mock_markets, mock_config_valid)
        
        assert result['initial_capital'] == 1000.0
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_zero_cycles_rejected(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Nombre de cycles = 0 rejeté"""
        mock_input.side_effect = [
            'EUR',
            '1000',
            '0',             # Invalide
            '3',             # Valide
            '',
            '',
            ''
        ]
        mock_confirm.side_effect = [False, False]
        
        result = collect_simulation_parameters(mock_markets, mock_config_valid)
        
        assert result['nb_cycles'] == 3


class TestInputValidationEdgeCases:
    """Tests validation inputs edge cases"""
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_empty_string_capital_rejected(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """String vide pour capital redemande saisie"""
        mock_input.side_effect = [
            'EUR',
            '',              # Vide
            '1000',          # Valide
            '2',
            '',
            '',
            ''
        ]
        mock_confirm.side_effect = [False, False]
        
        result = collect_simulation_parameters(mock_markets, mock_config_valid)
        
        assert result['initial_capital'] == 1000.0
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_whitespace_only_rejected(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Espaces uniquement rejeté"""
        mock_input.side_effect = [
            'EUR',
            '   ',           # Whitespace
            '1000',
            '2',
            '',
            '',
            ''
        ]
        mock_confirm.side_effect = [False, False]
        
        result = collect_simulation_parameters(mock_markets, mock_config_valid)
        
        assert result['initial_capital'] == 1000.0
    
    @patch('builtins.input')
    @patch('rich.prompt.Confirm.ask')
    def test_comma_decimal_separator(self, mock_confirm, mock_input, mock_markets, mock_config_valid):
        """Virgule comme séparateur décimal acceptée"""
        mock_input.side_effect = [
            'EUR',
            '1000,50',       # Virgule au lieu de point
            '2',
            '',
            '',
            ''
        ]
        mock_confirm.side_effect = [False, False]
        
        result = collect_simulation_parameters(mock_markets, mock_config_valid)
        
        # La fonction devrait convertir virgule en point
        assert abs(result['initial_capital'] - 1000.5) < 0.01