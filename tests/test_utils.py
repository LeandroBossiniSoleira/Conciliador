"""Testes para src/loaders/utils.py — is_empty e ler_arquivo_robusto."""

import io
import numpy as np
import pandas as pd
import pytest

from src.loaders.utils import is_empty, ler_arquivo_robusto


class TestIsEmpty:
    def test_none(self):
        assert is_empty(None) is True

    def test_nan_float(self):
        assert is_empty(float("nan")) is True

    def test_numpy_nan(self):
        assert is_empty(np.nan) is True

    def test_pandas_na(self):
        assert is_empty(pd.NA) is True

    def test_string_vazia(self):
        assert is_empty("") is True

    def test_string_espacos(self):
        assert is_empty("   ") is True

    def test_string_com_valor(self):
        assert is_empty("abc") is False

    def test_numero_zero(self):
        assert is_empty(0) is False

    def test_numero_valido(self):
        assert is_empty(42) is False

    def test_lista_vazia(self):
        # Listas não são "empty" no sentido do utilitário — str([]) != ""
        assert is_empty([]) is False


class TestLerArquivoRobusto:
    def test_ler_xlsx(self, xlsx_simples):
        df = ler_arquivo_robusto(xlsx_simples)
        assert not df.empty
        assert "SKU" in df.columns
        assert len(df) == 2

    def test_ler_csv_fallback(self, csv_simples):
        df = ler_arquivo_robusto(csv_simples)
        assert not df.empty
        assert len(df) == 2

    def test_ler_html_fallback(self):
        html = b"<table><tr><th>SKU</th><th>Nome</th></tr><tr><td>001</td><td>Prod</td></tr></table>"
        buf = io.BytesIO(html)
        df = ler_arquivo_robusto(buf)
        assert not df.empty
        assert len(df) == 1

    def test_arquivo_invalido_levanta_erro(self):
        buf = io.BytesIO(b"conteudo binario invalido \x00\x01\x02")
        with pytest.raises(ValueError, match="Não foi possível ler"):
            ler_arquivo_robusto(buf)
