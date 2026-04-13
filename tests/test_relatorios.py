"""Testes para src/reports/gerar_relatorios.py."""

import os
import tempfile

import pandas as pd
import pytest

from src.reports.gerar_relatorios import gerar_excel, gerar_resumo, imprimir_resumo


@pytest.fixture
def resultados_mock():
    """Dicionário simulando saída de executar_comparacao()."""
    return {
        "comparativo_geral": pd.DataFrame({"sku": ["A", "B", "C"]}),
        "somente_magis": pd.DataFrame({"sku": ["B"]}),
        "somente_tiny": pd.DataFrame({"sku": ["C"]}),
        "presente_nos_dois": pd.DataFrame({"sku": ["A"]}),
        "divergencias_fiscais": pd.DataFrame(),
        "duplicidades_sku_magis": pd.DataFrame(),
        "duplicidades_ean_magis": pd.DataFrame(),
        "duplicidades_sku_tiny": pd.DataFrame(),
        "duplicidades_ean_tiny": pd.DataFrame(),
        "sugestao_match_ean": pd.DataFrame(),
        "sugestao_match_titulo": pd.DataFrame(),
        "erros_fiscais_magis": pd.DataFrame(),
        "erros_fiscais_tiny": pd.DataFrame(),
    }


# ────────────────────────────────────────────
# gerar_excel
# ────────────────────────────────────────────

class TestGerarExcel:
    def test_gera_arquivo_xlsx(self, resultados_mock):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            caminho = f.name
        try:
            resultado = gerar_excel(resultados_mock, caminho_saida=caminho)
            assert resultado == caminho
            assert os.path.exists(caminho)
            assert os.path.getsize(caminho) > 0
        finally:
            os.unlink(caminho)

    def test_gera_multiplas_abas(self, resultados_mock):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            caminho = f.name
        try:
            gerar_excel(resultados_mock, caminho_saida=caminho)
            xls = pd.ExcelFile(caminho, engine="openpyxl")
            assert len(xls.sheet_names) > 0
            assert "Comparativo Geral" in xls.sheet_names
            assert "Somente Magis" in xls.sheet_names
        finally:
            os.unlink(caminho)

    def test_abas_vazias_tem_mensagem_informativa(self, resultados_mock):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            caminho = f.name
        try:
            gerar_excel(resultados_mock, caminho_saida=caminho)
            df_vazia = pd.read_excel(caminho, sheet_name="Divergências Fiscais", engine="openpyxl")
            assert "info" in df_vazia.columns
        finally:
            os.unlink(caminho)

    def test_gera_caminho_padrao_se_nao_informado(self, resultados_mock):
        caminho = gerar_excel(resultados_mock)
        try:
            assert os.path.exists(caminho)
            assert "comparativo_" in caminho
            assert caminho.endswith(".xlsx")
        finally:
            os.unlink(caminho)


# ────────────────────────────────────────────
# gerar_resumo
# ────────────────────────────────────────────

class TestGerarResumo:
    def test_retorna_dataframe_com_categorias(self, resultados_mock):
        resumo = gerar_resumo(resultados_mock)
        assert "categoria" in resumo.columns
        assert "quantidade" in resumo.columns
        assert len(resumo) == len(resultados_mock)

    def test_contagens_corretas(self, resultados_mock):
        resumo = gerar_resumo(resultados_mock)
        row_geral = resumo[resumo["categoria"] == "comparativo_geral"]
        assert row_geral["quantidade"].iloc[0] == 3

    def test_categorias_vazias_tem_zero(self, resultados_mock):
        resumo = gerar_resumo(resultados_mock)
        row_div = resumo[resumo["categoria"] == "divergencias_fiscais"]
        assert row_div["quantidade"].iloc[0] == 0

    def test_dict_vazio_retorna_vazio(self):
        resumo = gerar_resumo({})
        assert resumo.empty


# ────────────────────────────────────────────
# imprimir_resumo
# ────────────────────────────────────────────

class TestImprimirResumo:
    def test_imprime_sem_erro(self, resultados_mock, capsys):
        imprimir_resumo(resultados_mock)
        captured = capsys.readouterr()
        assert "RESUMO" in captured.out
        assert "Somente Magis" in captured.out
        assert "Somente Tiny" in captured.out
