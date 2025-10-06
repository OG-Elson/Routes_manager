"""
Tests unitaires pour le moteur d'arbitrage
Focus sur calculate_profit_route() et find_routes_with_filters()
"""
import pytest
from src.engine.arbitrage_engine import (
    calculate_profit_route,
    find_routes_with_filters,
    validate_config_coherence,
    get_market_data,
    safe_divide
)


class TestCalculateProfitRoute:
    """Tests calcul profitabilité routes"""
    
    def test_simple_route_eur_to_xaf(self, mock_markets, mock_forex_rates):
        """Route EUR→XAF→EUR avec conversion forex"""
        result = calculate_profit_route(
            initial_usdt=1000,
            sourcing_code="EUR",
            selling_code="XAF",
            conversion_method="forex"
        )
        
        assert result is not None
        assert result['sourcing_market_code'] == "EUR"
        assert result['selling_market_code'] == "XAF"
        assert result['conversion_method'] == "forex"
        assert 'profit_pct' in result
        assert 'profit_usdt' in result
        assert result['initial_amount_usdt'] == 1000
    
    def test_forex_vs_bank_different_profits(self, mock_markets, mock_forex_rates):
        """Forex vs Bank donnent profits différents"""
        result_forex = calculate_profit_route(1000, "EUR", "XAF", "forex")
        result_bank = calculate_profit_route(1000, "EUR", "XAF", "bank")
        
        assert result_forex is not None
        assert result_bank is not None
        
        # Les profits doivent être différents
        assert result_forex['profit_pct'] != result_bank['profit_pct']
        
        # Bank devrait être moins profitable (spreads défavorables)
        assert result_bank['profit_pct'] < result_forex['profit_pct']
    
    def test_invalid_usdt_amount_returns_none(self, mock_markets, mock_forex_rates):
        """Montant USDT ≤ 0 retourne None"""
        result = calculate_profit_route(0, "EUR", "XAF", "forex")
        assert result is None
        
        result = calculate_profit_route(-100, "EUR", "XAF", "forex")
        assert result is None
    
    def test_circular_conversion_returns_none(self, mock_markets, mock_forex_rates):
        """EUR→EUR retourne None"""
        result = calculate_profit_route(1000, "EUR", "EUR", "forex")
        assert result is None
    
    def test_missing_market_returns_none(self, mock_markets, mock_forex_rates):
        """Devise inexistante retourne None"""
        result = calculate_profit_route(1000, "INVALID", "XAF", "forex")
        assert result is None
    
    def test_profit_calculation_consistency(self, mock_markets, mock_forex_rates):
        """Vérifier cohérence profit_eur et profit_pct"""
        result = calculate_profit_route(1000, "EUR", "XAF", "forex")
        
        assert result is not None
        
        # profit_pct = (profit_eur / cost_eur) * 100
        expected_pct = (result['profit_eur'] / result['cost_eur']) * 100 if result['cost_eur'] > 0 else 0
        assert abs(result['profit_pct'] - expected_pct) < 0.01
    
    def test_plan_de_vol_structure(self, mock_markets, mock_forex_rates):
        """Plan de vol contient structure attendue"""
        result = calculate_profit_route(1000, "EUR", "XAF", "forex")
        
        assert 'plan_de_vol' in result
        assert 'phases' in result['plan_de_vol']
        
        phases = result['plan_de_vol']['phases']
        assert len(phases) > 0
        
        # Vérifier structure première phase
        first_phase = phases[0]
        assert 'cycle' in first_phase
        assert 'type' in first_phase
        assert 'description' in first_phase


class TestFindRoutesWithFilters:
    """Tests recherche routes avec filtres"""
    
    def test_sourcing_currency_filter(self, mock_config_valid):
        """sourcing_currency='EUR' filtre correctement"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']
        
        routes = find_routes_with_filters(
            top_n=10,
            sourcing_currency='EUR',
            conversion_method='forex'
        )
        
        # Toutes routes doivent commencer par EUR
        for route in routes:
            assert route['sourcing_market_code'] == 'EUR'
    
    def test_excluded_markets_filter(self, mock_config_valid):
        """excluded_markets=['XAF'] exclut XAF"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']
        
        routes = find_routes_with_filters(
            top_n=10,
            excluded_markets=['XAF'],
            conversion_method='forex'
        )
        
        # Aucune route ne doit vendre en XAF
        for route in routes:
            assert route['selling_market_code'] != 'XAF'
    
    def test_loop_currency_overrides_exclusion(self, mock_config_valid):
        """loop_currency prioritaire sur exclusions"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']
        
        routes = find_routes_with_filters(
            top_n=10,
            excluded_markets=['XAF'],
            loop_currency='XAF',  # XAF exclu mais forcé
            conversion_method='forex'
        )
        
        # XAF doit apparaître malgré exclusion
        xaf_routes = [r for r in routes if r['selling_market_code'] == 'XAF']
        assert len(xaf_routes) > 0
    
    def test_apply_threshold_filters_low_profit(self, mock_config_valid):
        """apply_threshold=True filtre routes < seuil"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']
        arbitrage_engine.SEUIL_RENTABILITE_PCT = mock_config_valid['SEUIL_RENTABILITE_PCT']
        
        routes = find_routes_with_filters(
            top_n=10,
            apply_threshold=True,
            conversion_method='forex'
        )
        
        # Toutes routes > seuil
        for route in routes:
            assert route['profit_pct'] >= arbitrage_engine.SEUIL_RENTABILITE_PCT
    
    def test_conversion_method_propagated(self, mock_config_valid):
        """conversion_method est propagé aux routes"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']
        
        routes = find_routes_with_filters(
            top_n=5,
            conversion_method='bank'
        )
        
        for route in routes:
            assert route['conversion_method'] == 'bank'
    
    def test_empty_results_when_all_excluded(self, mock_config_valid):
        """Tous marchés exclus → liste vide"""
        from src.engine import arbitrage_engine
        arbitrage_engine.markets = mock_config_valid['markets']
        arbitrage_engine.forex_rates = mock_config_valid['forex_rates']
        
        all_currencies = [m['currency'] for m in mock_config_valid['markets'] if m['currency'] != 'EUR']
        
        routes = find_routes_with_filters(
            sourcing_currency='EUR',
            excluded_markets=all_currencies
        )
        
        assert len(routes) == 0


class TestValidateConfigCoherence:
    """Tests validation configuration"""
    
    def test_valid_config_no_errors(self, mock_markets, mock_forex_rates):
        """Config valide → aucune erreur critique"""
        alerts = validate_config_coherence(mock_markets, mock_forex_rates)
        
        critical_errors = [a for a in alerts if a['severity'] == 'ERROR']
        assert len(critical_errors) == 0
    
    def test_missing_rates_raises_error(self, mock_config_missing_rates):
        """Taux manquants → erreur critique"""
        markets = mock_config_missing_rates['markets']
        forex_rates = mock_config_missing_rates['forex_rates']
        
        alerts = validate_config_coherence(markets, forex_rates)
        
        critical_errors = [a for a in alerts if a['severity'] == 'ERROR']
        assert len(critical_errors) > 0
    
    def test_invalid_spread_detected(self, mock_config_invalid_spread):
        """Spread inversé (buy < sell) détecté"""
        markets = mock_config_invalid_spread['markets']
        forex_rates = mock_config_invalid_spread['forex_rates']
        
        alerts = validate_config_coherence(markets, forex_rates)
        
        spread_errors = [a for a in alerts if a['type'] == 'SPREAD_INVERSE']
        assert len(spread_errors) > 0


class TestUtilityFunctions:
    """Tests fonctions utilitaires"""
    
    def test_get_market_data_valid(self, mock_markets):
        """get_market_data retourne market correct"""
        market = get_market_data("EUR", mock_markets)
        
        assert market['currency'] == "EUR"
        assert 'buy_price' in market
        assert 'sell_price' in market
    
    def test_get_market_data_invalid_raises(self, mock_markets):
        """get_market_data avec devise invalide lève ValueError"""
        with pytest.raises(ValueError, match="Aucun marché trouvé"):
            get_market_data("INVALID", mock_markets)
    
    def test_safe_divide_normal(self):
        """safe_divide avec valeurs normales"""
        result = safe_divide(10, 2)
        assert result == 5.0
    
    def test_safe_divide_by_zero(self):
        """safe_divide par zéro retourne default"""
        result = safe_divide(10, 0, default=0)
        assert result == 0
    
    def test_safe_divide_nan_handled(self):
        """safe_divide gère NaN"""
        result = safe_divide(float('nan'), 2, default=0)
        assert result == 0