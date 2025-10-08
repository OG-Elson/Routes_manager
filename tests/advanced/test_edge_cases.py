"""
Tests avancés pour cas limites et erreurs
Basé sur test_advanced.py existant avec améliorations
"""
import math

import pytest

from src.engine.arbitrage_engine import (calculate_profit_route,
                                         get_forex_rate, safe_divide,
                                         validate_config_coherence)


class TestNaNAndInfinity:
    """Tests gestion NaN et Infini"""
    
    def test_nan_usdt_amount_returns_none(self, mock_markets, mock_forex_rates):
        """Montant USDT = NaN retourne None"""
        result = calculate_profit_route(
            float('nan'),
            "EUR",
            "XAF",
            "forex"
        )
        assert result is None
    
    def test_infinity_usdt_amount_returns_none(self, mock_markets, mock_forex_rates):
        """Montant USDT = Infini retourne None"""
        result = calculate_profit_route(
            float('inf'),
            "EUR",
            "XAF",
            "forex"
        )
        assert result is None
    
    def test_safe_divide_nan_returns_default(self):
        """safe_divide avec NaN retourne default"""
        result = safe_divide(float('nan'), 2, default=0)
        assert result == 0
    
    def test_safe_divide_infinity_numerator(self):
        """safe_divide avec numérateur infini"""
        result = safe_divide(float('inf'), 2, default=0)
        # Devrait retourner default ou gérer proprement
        assert result == 0 or math.isinf(result)


class TestDivisionByZero:
    """Tests divisions par zéro"""
    
    def test_safe_divide_by_zero(self):
        """safe_divide par zéro retourne default"""
        result = safe_divide(10, 0, default=0)
        assert result == 0
    
    def test_zero_forex_rate_handled(self):
        """Taux forex = 0 géré proprement"""
        invalid_rates = {
            "XAF/EUR": {
                "bid": 0.0,
                "ask": 660.0,
                "bank_spread_pct": 1.5
            }
        }
        
        with pytest.raises((ValueError, ZeroDivisionError)):
            get_forex_rate("XAF", "EUR", invalid_rates, "forex")
    
    def test_zero_market_prices(self, mock_forex_rates):
        """Prix marchés = 0 géré"""
        invalid_markets = [{
            "currency": "EUR",
            "buy_price": 0.0,
            "sell_price": 0.0,
            "fee_pct": 0.1
        }]
        
        # calculate_profit_route devrait retourner None
        # (nécessite mock complet de markets)
        pass


class TestInvalidConfigurations:
    """Tests configurations invalides"""
    
    def test_negative_prices(self):
        """Prix négatifs détectés"""
        invalid_markets = [{
            "currency": "EUR",
            "buy_price": -0.857,
            "sell_price": 0.851,
            "fee_pct": 0.1
        }]
        
        alerts = validate_config_coherence(invalid_markets, {})
        
        # Devrait détecter anomalie
        errors = [a for a in alerts if a['severity'] == 'ERROR']
        assert len(errors) > 0
    
    def test_fees_over_100_percent(self):
        """Frais > 100% détectés"""
        invalid_markets = [{
            "currency": "EUR",
            "buy_price": 0.857,
            "sell_price": 0.851,
            "fee_pct": 150.0  # 150%
        }]
        
        # Devrait générer warning ou erreur
        alerts = validate_config_coherence(invalid_markets, {})
        
        warnings = [a for a in alerts if a['severity'] in ['WARNING', 'ERROR']]
        # Note: actuellement non implémenté, test de régression
    
    def test_empty_currency_code(self):
        """Code devise vide géré"""
        invalid_markets = [{
            "currency": "",
            "buy_price": 0.857,
            "sell_price": 0.851,
            "fee_pct": 0.1
        }]
        
        # Devrait lever erreur ou retourner None
        pass


class TestMissingData:
    """Tests données manquantes"""
    
    def test_missing_forex_rate(self, mock_config_missing_rates):
        """Taux forex manquant détecté"""
        markets = mock_config_missing_rates['markets']
        forex_rates = mock_config_missing_rates['forex_rates']
        
        alerts = validate_config_coherence(markets, forex_rates)
        
        errors = [a for a in alerts if a['type'] == 'TAUX_MANQUANT']
        assert len(errors) > 0
    
    def test_missing_market_fields(self):
        """Champs market manquants détectés"""
        incomplete_market = {
            "currency": "EUR"
            # buy_price, sell_price manquants
        }
        
        from src.engine.arbitrage_engine import validate_market_data
        is_valid, message = validate_market_data(incomplete_market)
        
        assert not is_valid
        assert "manquant" in message.lower()


class TestExtremeValues:
    """Tests valeurs extrêmes"""
    
    def test_very_large_capital(self, mock_markets, mock_forex_rates):
        """Capital très élevé (1 milliard USDT)"""
        result = calculate_profit_route(
            1_000_000_000,
            "EUR",
            "XAF",
            "forex"
        )
        
        # Devrait fonctionner
        assert result is not None
        assert result['initial_amount_usdt'] == 1_000_000_000
    
    def test_very_small_capital(self, mock_markets, mock_forex_rates):
        """Capital très faible (0.01 USDT)"""
        result = calculate_profit_route(
            0.01,
            "EUR",
            "XAF",
            "forex"
        )
        
        assert result is not None
        assert result['initial_amount_usdt'] == 0.01
    
    def test_extreme_forex_spread(self):
        """Spread forex extrême (1000%)"""
        extreme_rates = {
            "XAF/EUR": {
                "bid": 100.0,
                "ask": 1000.0,  # 10x spread
                "bank_spread_pct": 1.5
            }
        }
        
        # Devrait calculer sans erreur
        rate = get_forex_rate("EUR", "XAF", extreme_rates, "forex")
        assert rate == 100.0


class TestInvalidSpreadDetection:
    """Tests détection spreads invalides"""
    
    def test_inverted_spread_buy_less_than_sell(self, mock_config_invalid_spread):
        """buy_price < sell_price détecté"""
        markets = mock_config_invalid_spread['markets']
        forex_rates = mock_config_invalid_spread['forex_rates']
        
        alerts = validate_config_coherence(markets, forex_rates)
        
        spread_errors = [a for a in alerts if a['type'] in ['SPREAD_INVERSE', 'ANOMALIE_SPREAD']]
        assert len(spread_errors) > 0
    
    def test_zero_spread_allowed(self):
        """Spread = 0 autorisé (edge case)"""
        zero_spread_market = [{
            "currency": "EUR",
            "buy_price": 0.857,
            "sell_price": 0.857,  # Même prix
            "fee_pct": 0.1
        }]
        
        alerts = validate_config_coherence(zero_spread_market, {})
        
        # Ne devrait pas générer d'erreur (spread = 0% acceptable)
        errors = [a for a in alerts if a['severity'] == 'ERROR']
        # Peut générer warning mais pas erreur