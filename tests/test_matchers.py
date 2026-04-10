"""Testes para src/matchers/ — sku_matcher, ean_matcher, similaridade_matcher."""

import pandas as pd

from src.matchers.sku_matcher import match_por_sku
from src.matchers.ean_matcher import match_por_ean, match_por_ean_comum
from src.matchers.similaridade_matcher import similaridade, sugerir_matches_por_titulo


class TestMatchPorSku:
    def test_merge_outer_preserva_todos(self, df_magis_basico, df_tiny_basico):
        resultado = match_por_sku(df_magis_basico, df_tiny_basico)
        # SKU001 nos dois, SKU002+SKU003 só Magis, SKU004+SKU005 só Tiny = 5
        assert len(resultado) == 5
        assert "_merge" in resultado.columns

    def test_both_para_sku_comum(self, df_magis_basico, df_tiny_basico):
        resultado = match_por_sku(df_magis_basico, df_tiny_basico)
        both = resultado[resultado["_merge"] == "both"]
        assert len(both) == 1
        assert both.iloc[0]["sku"] == "SKU001"

    def test_left_only_para_exclusivos_magis(self, df_magis_basico, df_tiny_basico):
        resultado = match_por_sku(df_magis_basico, df_tiny_basico)
        left = resultado[resultado["_merge"] == "left_only"]
        assert set(left["sku"]) == {"SKU002", "SKU003"}

    def test_right_only_para_exclusivos_tiny(self, df_magis_basico, df_tiny_basico):
        resultado = match_por_sku(df_magis_basico, df_tiny_basico)
        right = resultado[resultado["_merge"] == "right_only"]
        assert set(right["sku"]) == {"SKU004", "SKU005"}


class TestMatchPorEan:
    def test_match_por_ean_tributavel(self, df_magis_basico, df_tiny_basico):
        resultado = match_por_ean(df_magis_basico, df_tiny_basico)
        # Apenas SKU001 tem EAN tributável em ambos
        assert len(resultado) == 1

    def test_ignora_ean_vazio(self):
        magis = pd.DataFrame({
            "sku": ["A", "B"],
            "ean_tributavel": ["123", ""],
        })
        tiny = pd.DataFrame({
            "sku": ["C", "D"],
            "ean_tributavel": ["123", ""],
        })
        resultado = match_por_ean(magis, tiny)
        assert len(resultado) == 1

    def test_match_por_ean_comum(self):
        magis = pd.DataFrame({"sku": ["A"], "ean": ["999"]})
        tiny = pd.DataFrame({"sku": ["B"], "ean": ["999"]})
        resultado = match_por_ean_comum(magis, tiny)
        assert len(resultado) == 1


class TestSimilaridade:
    def test_titulos_identicos(self):
        assert similaridade("PRODUTO A", "PRODUTO A") == 100.0

    def test_titulos_similares(self):
        score = similaridade("PRODUTO AZUL GRANDE", "PRODUTO AZUL GRANDE 500ML")
        assert score > 70

    def test_titulos_diferentes(self):
        score = similaridade("CAFE TORRADO", "SABONETE LIQUIDO")
        assert score < 50

    def test_titulo_none(self):
        assert similaridade(None, "PRODUTO A") == 0.0

    def test_ambos_none(self):
        assert similaridade(None, None) == 0.0


class TestSugerirMatchesPorTitulo:
    def test_sugere_match_por_titulo(self):
        magis = pd.DataFrame({
            "sku": ["M1"],
            "titulo": ["CAFE TORRADO ESPECIAL 500G"],
        })
        tiny = pd.DataFrame({
            "sku": ["T1", "T2"],
            "titulo": ["CAFE TORRADO ESPECIAL 500G", "SABONETE LIQUIDO"],
        })
        resultado = sugerir_matches_por_titulo(magis, tiny, top_n=1)
        assert len(resultado) >= 1
        assert resultado.iloc[0]["sku_tiny"] == "T1"
        assert resultado.iloc[0]["score"] >= 90

    def test_retorna_vazio_se_sem_titulo(self):
        magis = pd.DataFrame({"sku": ["M1"], "titulo": [None]})
        tiny = pd.DataFrame({"sku": ["T1"], "titulo": ["Produto"]})
        resultado = sugerir_matches_por_titulo(magis, tiny, top_n=1)
        assert resultado.empty

    def test_retorna_vazio_se_tiny_vazio(self):
        magis = pd.DataFrame({"sku": ["M1"], "titulo": ["Produto"]})
        tiny = pd.DataFrame({"sku": pd.Series(dtype=str), "titulo": pd.Series(dtype=str)})
        resultado = sugerir_matches_por_titulo(magis, tiny, top_n=1)
        assert resultado.empty
