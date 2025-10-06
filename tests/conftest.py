"""
Fixtures centralisées pour tous les tests
"""
import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock


# ==================== FIXTURES CONFIGURATION ====================

@pytest.fixture
def mock_config_valid():
    """Configuration complète valide avec format bid/ask"""
    return {
        "markets": [
            {
                "currency": "EUR",
                "buy_price": 0.857,
                "sell_price": 0.851,
                "fee_pct": 0.1,
                "name": "Europe"
            },
            {
                "currency": "XAF",
                "buy_price": 595.86,
                "sell_price": 593.65,
                "fee_pct": 0.0,
                "name": "Afrique Centrale"
            },
            {
                "currency": "XOF",
                "buy_price": 566.60,
                "sell_price": 569.50,
                "fee_pct": 0.0,
                "name": "Afrique Ouest"
            },
            {
                "currency": "RWF",
                "buy_price": 1470.70,
                "sell_price": 1466.22,
                "fee_pct": 1.0,
                "name": "Rwanda"
            },
            {
                "currency": "KES",
                "buy_price": 128.0,
                "sell_price": 127.61,
                "fee_pct": 1.0,
                "name": "Kenya"
            }
        ],
        "forex_rates": {
            "XAF/EUR": {
                "bid": 650.0,
                "ask": 660.0,
                "bank_spread_pct": 1.5
            },
            "XOF/EUR": {
                "bid": 650.0,
                "ask": 660.0,
                "bank_spread_pct": 1.2
            },
            "RWF/EUR": {
                "bid": 1690.0,
                "ask": 1710.0,
                "bank_spread_pct": 2.0
            },
            "KES/EUR": {
                "bid": 150.5,
                "ask": 153.0,
                "bank_spread_pct": 1.8
            }
        },
        "default_conversion_method": "forex",
        "SEUIL_RENTABILITE_PCT": 1.5,
        "NB_CYCLES_PAR_ROTATION": 3
    }


@pytest.fixture
def mock_config_old_format():
    """Configuration avec ancien format (nombres simples) - rétrocompatibilité"""
    return {
        "markets": [
            {"currency": "EUR", "buy_price": 0.857, "sell_price": 0.851, "fee_pct": 0.1, "name": "Europe"},
            {"currency": "XAF", "buy_price": 595.86, "sell_price": 593.65, "fee_pct": 0.0, "name": "Afrique"}
        ],
        "forex_rates": {
            "XAF/EUR": 655.957  # Ancien format
        },
        "default_conversion_method": "forex",
        "SEUIL_RENTABILITE_PCT": 1.5,
        "NB_CYCLES_PAR_ROTATION": 3
    }


@pytest.fixture
def mock_config_invalid_spread():
    """Configuration avec spread inversé (buy < sell) - erreur"""
    return {
        "markets": [
            {
                "currency": "EUR",
                "buy_price": 0.851,  # INVERSÉ
                "sell_price": 0.857,
                "fee_pct": 0.1,
                "name": "Europe"
            }
        ],
        "forex_rates": {
            "XAF/EUR": {"bid": 650.0, "ask": 660.0, "bank_spread_pct": 1.5}
        },
        "SEUIL_RENTABILITE_PCT": 1.5
    }


@pytest.fixture
def mock_config_missing_rates():
    """Configuration avec taux manquants"""
    return {
        "markets": [
            {"currency": "EUR", "buy_price": 0.857, "sell_price": 0.851, "fee_pct": 0.1, "name": "Europe"},
            {"currency": "XAF", "buy_price": 595.86, "sell_price": 593.65, "fee_pct": 0.0, "name": "Afrique"}
        ],
        "forex_rates": {},  # VIDE
        "SEUIL_RENTABILITE_PCT": 1.5
    }


@pytest.fixture
def mock_config_zero_spread():
    """Configuration avec bank_spread_pct = 0 (edge case)"""
    config = {
        "markets": [
            {"currency": "EUR", "buy_price": 0.857, "sell_price": 0.851, "fee_pct": 0.1, "name": "Europe"},
            {"currency": "XAF", "buy_price": 595.86, "sell_price": 593.65, "fee_pct": 0.0, "name": "Afrique"}
        ],
        "forex_rates": {
            "XAF/EUR": {
                "bid": 650.0,
                "ask": 660.0,
                "bank_spread_pct": 0.0  # Spread = 0
            }
        },
        "default_conversion_method": "forex",
        "SEUIL_RENTABILITE_PCT": 1.5
    }
    return config


# ==================== FIXTURES EXTRAITES ====================

@pytest.fixture
def mock_markets(mock_config_valid):
    """Liste des marchés"""
    return mock_config_valid['markets']


@pytest.fixture
def mock_forex_rates(mock_config_valid):
    """Taux forex"""
    return mock_config_valid['forex_rates']


# ==================== FIXTURES PARAMÉTRÉES ====================

@pytest.fixture(params=['forex', 'bank'])
def conversion_method(request):
    """Paramétrage méthodes conversion"""
    return request.param


@pytest.fixture(params=['EUR', 'XAF', 'XOF', 'RWF', 'KES'])
def currency(request):
    """Paramétrage devises"""
    return request.param


# ==================== FIXTURES FICHIERS TEMPORAIRES ====================

@pytest.fixture
def temp_config_file(tmp_path, mock_config_valid):
    """Créer fichier config.json temporaire"""
    config_file = tmp_path / "config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(mock_config_valid, f, indent=2)
    return config_file


@pytest.fixture
def temp_rotation_state_file(tmp_path):
    """Créer fichier rotation_state.json temporaire"""
    state_file = tmp_path / "rotation_state.json"
    initial_state = {"active_rotations": {}}
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(initial_state, f, indent=2)
    return state_file


# ==================== FIXTURES MOCKING ====================

@pytest.fixture
def mock_console_input(monkeypatch):
    """Mock console.input() pour tests interactifs"""
    inputs = []
    
    def mock_input(prompt):
        if not inputs:
            return "EUR"  # Valeur par défaut
        return inputs.pop(0)
    
    monkeypatch.setattr('builtins.input', mock_input)
    
    class InputMocker:
        def set_inputs(self, *values):
            inputs.clear()
            inputs.extend(reversed(values))
    
    return InputMocker()


@pytest.fixture
def mock_confirm_ask(monkeypatch):
    """Mock Confirm.ask() pour questions o/n"""
    answers = []
    
    def mock_ask(prompt):
        if not answers:
            return False
        return answers.pop(0)
    
    # Mock Rich Confirm.ask
    class MockConfirm:
        @staticmethod
        def ask(prompt):
            return mock_ask(prompt)
    
    monkeypatch.setattr('rich.prompt.Confirm', MockConfirm)
    
    class ConfirmMocker:
        def set_answers(self, *values):
            answers.clear()
            answers.extend(reversed(values))
    
    return ConfirmMocker()


# ==================== FIXTURES DONNÉES TEST ====================

@pytest.fixture
def sample_route_result():
    """Résultat type de calculate_profit_route()"""
    return {
        "sourcing_market_code": "EUR",
        "selling_market_code": "XAF",
        "conversion_method": "forex",
        "detailed_route": "EUR → USDT → XAF → EUR → USDT",
        "profit_pct": 2.5,
        "profit_usdt": 25.0,
        "final_amount_usdt": 1025.0,
        "initial_amount_usdt": 1000.0,
        "cost_eur": 857.0,
        "revenue_eur": 878.4,
        "details": {},
        "plan_de_vol": {"phases": []}
    }


# ==================== FIXTURES HELPERS ====================

@pytest.fixture
def approx_equal():
    """Helper pour comparaisons flottants avec tolérance"""
    def _approx_equal(a, b, tolerance=0.0001):
        return abs(a - b) < tolerance
    return _approx_equal

# ==================== CONFIGURATION PYTEST ====================

def pytest_configure(config):
    """Configuration pytest personnalisée"""
    config.addinivalue_line(
        "markers", "unit: Tests unitaires"
    )
    config.addinivalue_line(
        "markers", "integration: Tests d'intégration"
    )
    config.addinivalue_line(
        "markers", "advanced: Tests edge cases"
    )


def pytest_collection_modifyitems(config, items):
    """Ajouter markers automatiquement selon fichier"""
    for item in items:
        # Ajouter marker selon chemin fichier
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "advanced" in str(item.fspath):
            item.add_marker(pytest.mark.advanced)


# Hook pour afficher résumé personnalisé
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Afficher résumé personnalisé en fin de tests"""
    print("\n" + "=" * 70)
    print("RÉSUMÉ DES TESTS")
    print("=" * 70)
    
    stats = terminalreporter.stats
    
    passed = len(stats.get('passed', []))
    failed = len(stats.get('failed', []))
    skipped = len(stats.get('skipped', []))
    errors = len(stats.get('error', []))
    
    total = passed + failed + skipped + errors
    
    if total > 0:
        success_rate = (passed / total) * 100
    else:
        success_rate = 0
    
    print(f"\n✓ Réussis:  {passed}")
    print(f"✗ Échoués:  {failed}")
    print(f"⊘ Ignorés:  {skipped}")
    print(f"⚠ Erreurs:  {errors}")
    print(f"━━━━━━━━━━━━━━━━━━━━")
    print(f"  TOTAL:    {total}")
    print(f"\n📊 Taux de réussite: {success_rate:.1f}%")
    
    if success_rate == 100 and total > 0:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
    elif success_rate >= 80:
        print(f"\n✓ Bon taux de réussite ({success_rate:.1f}%)")
    elif success_rate >= 50:
        print(f"\n⚠ Taux moyen ({success_rate:.1f}%) - À améliorer")
    else:
        print(f"\n✗ Taux faible ({success_rate:.1f}%) - Action requise")
    
    print("=" * 70)