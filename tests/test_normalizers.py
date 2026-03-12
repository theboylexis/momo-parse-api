"""Unit tests for parser/normalizers.py"""
import pytest
from parser.normalizers import normalize_amount, normalize_phone, normalize_name


class TestNormalizeAmount:
    def test_plain_float(self):
        assert normalize_amount("150.00") == 150.00

    def test_comma_thousands(self):
        assert normalize_amount("1,037.64") == 1037.64

    def test_integer_string(self):
        assert normalize_amount("200") == 200.0

    def test_zero(self):
        assert normalize_amount("0.00") == 0.0

    def test_strips_whitespace(self):
        assert normalize_amount("  50.00 ") == 50.0

    def test_none_input(self):
        assert normalize_amount(None) is None

    def test_invalid_returns_none(self):
        assert normalize_amount("GHS") is None

    def test_trailing_period(self):
        # "0." from fee capture — should parse as 0.0
        assert normalize_amount("0.") == 0.0


class TestNormalizePhone:
    def test_local_format_to_e164(self):
        assert normalize_phone("0241880380") == "+233241880380"

    def test_233_prefix_to_e164(self):
        assert normalize_phone("233241880380") == "+233241880380"

    def test_already_e164(self):
        assert normalize_phone("+233241880380") == "+233241880380"

    def test_agent_code_passthrough(self):
        # Agent codes like A25736 are returned as-is
        assert normalize_phone("A25736") == "A25736"

    def test_none_input(self):
        assert normalize_phone(None) is None

    def test_short_code_passthrough(self):
        assert normalize_phone("750000") == "750000"

    def test_telecel_number(self):
        assert normalize_phone("0594372553") == "+233594372553"


class TestNormalizeName:
    def test_strips_leading_trailing_whitespace(self):
        assert normalize_name("  KWAME ASANTE  ") == "KWAME ASANTE"

    def test_preserves_internal_spaces(self):
        assert normalize_name("SAMUEL NANA AGYEI ASANTE") == "SAMUEL NANA AGYEI ASANTE"

    def test_none_input(self):
        assert normalize_name(None) is None

    def test_already_clean(self):
        assert normalize_name("KOFI MENSAH") == "KOFI MENSAH"
