"""Testes para src/comparators/comparador_produtos.py."""

import pandas as pd
import pytest

from src.comparators.comparador_produtos import (
    _separar_por_status,
    classificar,
    detectar_divergencias,
    executar_comparacao,
)


# ────────────────────────────────────────────
# _separar_por_status
# ────────────────────────────────────────────

class TestSepararPorStatus:
    def test_separa_ativos_e_inativos(self):
        df = pd.DataFrame({
            "sku": ["A", "B", "C"],
            "status": ["ATIVO", "INATIVO", "EXCLUIDO"],
        })
        ativos, inativos = _separar_por_status(df, "status")
        assert len(ativos) == 1
        assert ativos["sku"].iloc[0] == "A"
        assert len(inativos) == 2

    def test_status_ausente_e_tratado_como_ativo(self):
        df = pd.DataFrame({
            "sku": ["A", "B"],
            "status": [None, "ATIVO"],
        })
        ativos, inativos = _separar_por_status(df, "status")
        assert len(ativos) == 2
        assert inativos.empty

    def test_coluna_inexistente_retorna_todos_como_ativos(self):
        df = pd.DataFrame({"sku": ["A", "B"]})
        ativos, inativos = _separar_por_status(df, "status")
        assert len(ativos) == 2
        assert inativos.empty

    def test_status_case_insensitive(self):
        df = pd.DataFrame({
            "sku": ["A", "B"],
            "status": ["inativo", "excluido"],
        })
        ativos, inativos = _separar_por_status(df, "status")
        assert ativos.empty
        assert len(inativos) == 2

    def test_retorna_copias_independentes(self):
        df = pd.DataFrame({"sku": ["A"], "status": ["ATIVO"]})
        ativos, _ = _separar_por_status(df, "status")
        ativos["sku"] = "MODIFICADO"
        assert df["sku"].iloc[0] == "A"


# ────────────────────────────────────────────
# classificar
# ────────────────────────────────────────────

class TestClassificar:
    def test_left_only(self):
        row = pd.Series({"_merge": "left_only"})
        assert classificar(row) == "SOMENTE_MAGIS"

    def test_right_only(self):
        row = pd.Series({"_merge": "right_only"})
        assert classificar(row) == "SOMENTE_TINY"

    def test_both(self):
        row = pd.Series({"_merge": "both"})
        assert classificar(row) == "PRESENTE_NOS_DOIS"

    def test_valor_desconhecido(self):
        row = pd.Series({"_merge": "outro"})
        assert classificar(row) == "ERRO"

    def test_merge_ausente(self):
        row = pd.Series({"sku": "X"})
        assert classificar(row) == "ERRO"


# ────────────────────────────────────────────
# detectar_divergencias
# ────────────────────────────────────────────

class TestDetectarDivergencias:
    def test_detecta_ncm_divergente(self):
        df = pd.DataFrame({
            "sku": ["SKU001"],
            "ncm_magis": ["12345678"],
            "ncm_tiny": ["99999999"],
        })
        resultado = detectar_divergencias(df)
        assert len(resultado) == 1
        assert resultado["campo_divergente"].iloc[0] == "ncm"
        assert resultado["valor_magis"].iloc[0] == "12345678"
        assert resultado["valor_tiny"].iloc[0] == "99999999"

    def test_sem_divergencias(self):
        df = pd.DataFrame({
            "sku": ["SKU001"],
            "ncm_magis": ["12345678"],
            "ncm_tiny": ["12345678"],
            "origem_magis": ["0"],
            "origem_tiny": ["0"],
        })
        resultado = detectar_divergencias(df)
        assert resultado.empty

    def test_multiplas_divergencias_mesmo_sku(self):
        df = pd.DataFrame({
            "sku": ["SKU001"],
            "ncm_magis": ["111"],
            "ncm_tiny": ["222"],
            "origem_magis": ["0"],
            "origem_tiny": ["1"],
        })
        resultado = detectar_divergencias(df)
        assert len(resultado) == 2
        campos = set(resultado["campo_divergente"])
        assert campos == {"ncm", "origem"}

    def test_none_tratado_como_vazio(self):
        df = pd.DataFrame({
            "sku": ["SKU001"],
            "ncm_magis": [None],
            "ncm_tiny": [None],
        })
        resultado = detectar_divergencias(df)
        assert resultado.empty

    def test_none_vs_valor_e_divergencia(self):
        df = pd.DataFrame({
            "sku": ["SKU001"],
            "ncm_magis": [None],
            "ncm_tiny": ["12345678"],
        })
        resultado = detectar_divergencias(df)
        assert len(resultado) == 1

    def test_colunas_ausentes_ignoradas(self):
        df = pd.DataFrame({"sku": ["SKU001"]})
        resultado = detectar_divergencias(df)
        assert resultado.empty

    def test_retorna_colunas_corretas(self):
        df = pd.DataFrame({
            "sku": ["SKU001"],
            "ncm_magis": ["111"],
            "ncm_tiny": ["222"],
        })
        resultado = detectar_divergencias(df)
        assert list(resultado.columns) == ["sku", "campo_divergente", "valor_magis", "valor_tiny"]


# ────────────────────────────────────────────
# executar_comparacao (integração)
# ────────────────────────────────────────────

class TestExecutarComparacao:
    def test_retorna_todas_as_chaves(self, df_magis_basico, df_tiny_basico):
        resultado = executar_comparacao(df_magis_basico, df_tiny_basico)
        chaves_esperadas = {
            "comparativo_geral",
            "somente_magis", "somente_magis_inativos",
            "somente_tiny", "somente_tiny_inativos",
            "presente_nos_dois",
            "divergencias_fiscais",
            "duplicidades_sku_magis", "duplicidades_ean_magis",
            "duplicidades_sku_tiny", "duplicidades_ean_tiny",
            "sugestao_match_ean", "sugestao_match_titulo",
            "erros_fiscais_magis", "erros_fiscais_tiny",
        }
        assert set(resultado.keys()) == chaves_esperadas

    def test_todos_os_valores_sao_dataframes(self, df_magis_basico, df_tiny_basico):
        resultado = executar_comparacao(df_magis_basico, df_tiny_basico)
        for chave, valor in resultado.items():
            assert isinstance(valor, pd.DataFrame), f"{chave} não é DataFrame"

    def test_classificacao_correta(self, df_magis_basico, df_tiny_basico):
        resultado = executar_comparacao(df_magis_basico, df_tiny_basico)
        comp = resultado["comparativo_geral"]
        assert "classificacao" in comp.columns
        # SKU001 está em ambos
        row_sku001 = comp[comp["sku"] == "SKU001"]
        assert row_sku001["classificacao"].iloc[0] == "PRESENTE_NOS_DOIS"

    def test_somente_magis_exclui_inativos(self, df_magis_basico, df_tiny_basico):
        resultado = executar_comparacao(df_magis_basico, df_tiny_basico)
        # SKU003 está no Magis com status INATIVO → deve ir para inativos, não para somente_magis
        somente_magis = resultado["somente_magis"]
        inativos = resultado["somente_magis_inativos"]
        assert "SKU003" not in somente_magis["sku"].values
        assert "SKU003" in inativos["sku"].values

    def test_sku_exclusivo_tiny_classificado(self, df_magis_basico, df_tiny_basico):
        resultado = executar_comparacao(df_magis_basico, df_tiny_basico)
        somente_tiny = resultado["somente_tiny"]
        # SKU004 e SKU005 são exclusivos Tiny; SKU005 é INATIVO
        assert "SKU004" in somente_tiny["sku"].values

    def test_erros_fiscais_detectados(self, df_tiny_basico):
        # Produto ATIVO sem NCM deve ser reportado como erro fiscal.
        magis = pd.DataFrame({
            "sku": ["SKU999"],
            "titulo": ["PRODUTO ATIVO SEM NCM"],
            "ean": ["7891234569999"],
            "ean_tributavel": ["7891234569999"],
            "ncm": [None],
            "cest": [None],
            "origem": ["0"],
            "preco_custo": [10.0],
            "estoque": [1],
            "status": ["ATIVO"],
            "marca": ["X"],
            "sistema_origem": ["MAGIS"],
        })
        resultado = executar_comparacao(magis, df_tiny_basico)
        erros_magis = resultado["erros_fiscais_magis"]
        assert "SKU999" in erros_magis["sku"].values

    def test_erros_fiscais_excluem_inativos(self, df_magis_basico, df_tiny_basico):
        # SKU003 está INATIVO no Magis e tem NCM ausente — não pode aparecer
        # como erro fiscal (produto inativo não será migrado).
        resultado = executar_comparacao(df_magis_basico, df_tiny_basico)
        erros_magis = resultado["erros_fiscais_magis"]
        assert "SKU003" not in erros_magis["sku"].values
        # SKU005 está INATIVO no Tiny — idem.
        erros_tiny = resultado["erros_fiscais_tiny"]
        assert "SKU005" not in erros_tiny["sku"].values

    def test_dataframes_vazios(self):
        magis = pd.DataFrame(columns=["sku", "titulo", "ean", "ean_tributavel",
                                       "ncm", "cest", "origem", "status"])
        tiny = magis.copy()
        resultado = executar_comparacao(magis, tiny)
        assert resultado["comparativo_geral"].empty
        assert resultado["somente_magis"].empty
        assert resultado["somente_tiny"].empty
