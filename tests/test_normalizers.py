"""Testes para src/normalizers/normalizador.py."""

import pandas as pd

from src.normalizers.normalizador import (
    limpar_texto,
    limpar_codigo,
    extrair_digito_origem,
    normalizar_status,
    normalizar_dataframe,
)


class TestLimparTexto:
    def test_remove_acentos_e_upper(self):
        assert limpar_texto("café com leite") == "CAFE COM LEITE"

    def test_colapsa_espacos(self):
        assert limpar_texto("  muitos   espacos  ") == "MUITOS ESPACOS"

    def test_none_retorna_none(self):
        assert limpar_texto(None) is None

    def test_nan_retorna_none(self):
        assert limpar_texto(float("nan")) is None

    def test_string_vazia_retorna_none(self):
        assert limpar_texto("") is None

    def test_string_espacos_retorna_none(self):
        assert limpar_texto("   ") is None


class TestLimparCodigo:
    def test_remove_nao_digitos(self):
        assert limpar_codigo("123.456-789") == "123456789"

    def test_remove_letras(self):
        assert limpar_codigo("ABC123DEF") == "123"

    def test_none_retorna_none(self):
        assert limpar_codigo(None) is None

    def test_somente_letras_retorna_none(self):
        assert limpar_codigo("ABCDEF") is None


class TestExtrairDigitoOrigem:
    def test_extrai_primeiro_digito(self):
        assert extrair_digito_origem("0 - Nacional") == "0"

    def test_extrai_de_string_mista(self):
        assert extrair_digito_origem("Importação 3") == "3"

    def test_none_retorna_none(self):
        assert extrair_digito_origem(None) is None

    def test_sem_digito_retorna_none(self):
        assert extrair_digito_origem("sem números") is None


class TestNormalizarStatus:
    def test_magis_active(self):
        mapa = {"magis": {"active": "ATIVO"}}
        assert normalizar_status("active", "magis", mapa) == "ATIVO"

    def test_tiny_ativo(self):
        mapa = {"tiny": {"Ativo": "ATIVO"}}
        assert normalizar_status("Ativo", "tiny", mapa) == "ATIVO"

    def test_valor_desconhecido_upper(self):
        mapa = {"magis": {}}
        assert normalizar_status("custom", "magis", mapa) == "CUSTOM"

    def test_none_retorna_none(self):
        assert normalizar_status(None, "magis", {}) is None


class TestNormalizarDataframe:
    def test_normaliza_texto_e_codigo(self):
        df = pd.DataFrame({
            "sku": ["abc-123"],
            "titulo": ["café com açúcar"],
            "ncm": ["1234.56.78"],
            "origem": ["0 - Nacional"],
            "status": ["active"],
        })
        resultado = normalizar_dataframe(df, sistema="magis")
        assert resultado["titulo"].iloc[0] == "CAFE COM ACUCAR"
        assert resultado["ncm"].iloc[0] == "12345678"
        assert resultado["origem"].iloc[0] == "0"
        assert resultado["status"].iloc[0] == "ATIVO"

    def test_preco_custo_converte_virgula(self):
        df = pd.DataFrame({
            "preco_custo": ["10,50", "20,00"],
        })
        resultado = normalizar_dataframe(df)
        assert resultado["preco_custo"].iloc[0] == 10.5
        assert resultado["preco_custo"].iloc[1] == 20.0

    def test_estoque_converte_para_int(self):
        df = pd.DataFrame({
            "estoque": ["100", None, "abc"],
        })
        resultado = normalizar_dataframe(df)
        assert resultado["estoque"].iloc[0] == 100
        assert resultado["estoque"].iloc[1] == 0  # NaN → 0
        assert resultado["estoque"].iloc[2] == 0  # "abc" → 0
