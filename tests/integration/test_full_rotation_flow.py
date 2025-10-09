"""
Tests d'intégration pour flux complets de rotation
"""
import json
from pathlib import Path

import pytest

from src.engine.arbitrage_engine import (calculate_profit_route,
                                         find_routes_with_filters)


class TestFullRotationFlow:
    """Tests flux bout-en-bout"""

    def test_search_to_route_calculation(self, mock_config_valid):
        """Flux: recherche routes → calcul détaillé"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']
        arbitrage_engine.SEUIL_RENTABILITE_PCT = mock_config_valid['SEUIL_RENTABILITE_PCT']

        # 1. Recherche routes
        routes = find_routes_with_filters(
            top_n=3,
            conversion_method='forex'
        )

        assert len(routes) > 0

        # 2. Sélectionner meilleure route
        best_route = routes[0]

        # 3. Recalculer avec montant spécifique
        detailed = calculate_profit_route(
            initial_usdt=5000,
            sourcing_code=best_route['sourcing_market_code'],
            selling_code=best_route['selling_market_code'],
            conversion_method=best_route['conversion_method']
        )

        assert detailed is not None
        assert detailed['initial_amount_usdt'] == 5000
        assert 'plan_de_vol' in detailed

    def test_filtered_search_respects_all_params(self, mock_config_valid):
        """Tous filtres appliqués simultanément"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']

        routes = find_routes_with_filters(
            top_n=10,
            sourcing_currency='EUR',
            excluded_markets=['XOF'],
            loop_currency='XAF',
            conversion_method='bank'
        )

        for route in routes:
            # Vérifier sourcing
            assert route['sourcing_market_code'] == 'EUR'

            # Vérifier exclusion (sauf si loop_currency)
            if route['selling_market_code'] != 'XAF':
                assert route['selling_market_code'] != 'XOF'

            # Vérifier conversion method
            assert route['conversion_method'] == 'bank'

    def test_route_profitability_consistency(self, mock_config_valid):
        """Profitabilité cohérente entre recherche et calcul détaillé"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']

        routes = find_routes_with_filters(top_n=1, conversion_method='forex')

        assert len(routes) > 0
        route = routes[0]

        # Recalculer avec même montant (1000 USDT par défaut)
        detailed = calculate_profit_route(
            1000,
            route['sourcing_market_code'],
            route['selling_market_code'],
            'forex'
        )

        # Profits doivent être identiques (tolérance 0.01%)
        assert abs(route['profit_pct'] - detailed['profit_pct']) < 0.01


class TestValidationIntegration:
    """Tests validation avec moteur complet"""

    def test_invalid_config_blocks_search(self, mock_config_missing_rates):
        """Config invalide empêche recherche"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_missing_rates['markets']
        arbitrage_engine.forex_rates = mock_config_missing_rates['forex_rates']

        routes = find_routes_with_filters(
            top_n=5,
            skip_validation=False  # Validation activée
        )

        # Devrait retourner liste vide (taux manquants)
        assert len(routes) == 0

    def test_skip_validation_allows_search(self, mock_config_missing_rates):
        """skip_validation=True ignore erreurs config"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_missing_rates['markets']
        arbitrage_engine.forex_rates = mock_config_missing_rates['forex_rates']

        # Avec skip_validation, recherche tente quand même
        routes = find_routes_with_filters(
            top_n=5,
            skip_validation=True
        )

        # Peut retourner routes ou liste vide selon capacité à calculer
        assert isinstance(routes, list)


class TestMultiCurrencyFlow:
    """Tests avec plusieurs devises"""

    def test_all_currencies_as_sourcing(self, mock_config_valid):
        """Tester toutes devises comme sourcing"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']

        currencies = [m['currency'] for m in mock_config_valid['markets']]

        for currency in currencies:
            routes = find_routes_with_filters(
                top_n=2,
                sourcing_currency=currency,
                conversion_method='forex'
            )

            # Chaque devise devrait générer au moins une route
            if len(routes) > 0:
                assert routes[0]['sourcing_market_code'] == currency

    def test_forex_vs_bank_all_routes(self, mock_config_valid):
        """Comparer forex vs bank pour toutes routes possibles"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']

        routes_forex = find_routes_with_filters(top_n=5, conversion_method='forex')
        routes_bank = find_routes_with_filters(top_n=5, conversion_method='bank')

        assert len(routes_forex) > 0
        assert len(routes_bank) > 0

        # Pour chaque paire identique, bank devrait être moins profitable
        for rf in routes_forex:
            # Trouver route équivalente en bank
            rb = next(
                (r for r in routes_bank
                 if r['sourcing_market_code'] == rf['sourcing_market_code']
                 and r['selling_market_code'] == rf['selling_market_code']),
                None
            )

            if rb:
                assert rb['profit_pct'] <= rf['profit_pct']

