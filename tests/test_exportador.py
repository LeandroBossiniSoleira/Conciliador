"""Testes para src/reports/exportador_tiny.py — geração de planilhas de importação."""

import pandas as pd

from src.reports.exportador_tiny import (
    LAYOUT_IMPORTACAO_TINY,
    gerar_planilha_importacao_produtos_tiny,
    _tipo_correto,
)


class TestLayoutImportacao:
    def test_layout_tem_64_colunas(self):
        assert len(LAYOUT_IMPORTACAO_TINY) == 64

    def test_colunas_essenciais_presentes(self):
        essenciais = [
            "Código (SKU)", "Descrição", "Situação", "GTIN/EAN",
            "Classificação fiscal", "Origem", "Tipo do produto",
            "Peso líquido (Kg)", "Peso bruto (Kg)",
        ]
        for col in essenciais:
            assert col in LAYOUT_IMPORTACAO_TINY, f"Coluna '{col}' ausente no layout"


class TestGerarPlanilhaImportacao:
    def test_gera_dataframe_com_64_colunas(self, df_magis_basico):
        resultado = gerar_planilha_importacao_produtos_tiny(df_magis_basico)
        assert len(resultado.columns) == 64
        assert list(resultado.columns) == LAYOUT_IMPORTACAO_TINY

    def test_preenche_sku(self, df_magis_basico):
        resultado = gerar_planilha_importacao_produtos_tiny(df_magis_basico)
        assert resultado["Código (SKU)"].iloc[0] == "SKU001"

    def test_preenche_descricao(self, df_magis_basico):
        resultado = gerar_planilha_importacao_produtos_tiny(df_magis_basico)
        assert resultado["Descrição"].iloc[0] == "PRODUTO A"

    def test_status_ativo_mapeia_para_ativo(self, df_magis_basico):
        resultado = gerar_planilha_importacao_produtos_tiny(df_magis_basico)
        assert resultado["Situação"].iloc[0] == "Ativo"

    def test_status_inativo_mapeia_para_inativo(self, df_magis_basico):
        resultado = gerar_planilha_importacao_produtos_tiny(df_magis_basico)
        assert resultado["Situação"].iloc[2] == "Inativo"

    def test_numero_de_linhas_igual_ao_input(self, df_magis_basico):
        resultado = gerar_planilha_importacao_produtos_tiny(df_magis_basico)
        assert len(resultado) == len(df_magis_basico)

    def test_dataframe_vazio_retorna_vazio(self):
        df = pd.DataFrame()
        resultado = gerar_planilha_importacao_produtos_tiny(df)
        assert resultado.empty

    def test_peso_liquido_e_bruto_separados(self):
        df = pd.DataFrame({
            "sku": ["SKU001"],
            "titulo": ["Produto"],
            "status": ["ATIVO"],
            "peso_liquido": ["1.5"],
            "peso_bruto": ["2.0"],
        })
        resultado = gerar_planilha_importacao_produtos_tiny(df)
        assert resultado["Peso líquido (Kg)"].iloc[0] == "1.5"
        assert resultado["Peso bruto (Kg)"].iloc[0] == "2.0"

    def test_peso_fallback_para_peso_kg(self):
        df = pd.DataFrame({
            "sku": ["SKU001"],
            "titulo": ["Produto"],
            "status": ["ATIVO"],
            "peso_kg": ["3.0"],
        })
        resultado = gerar_planilha_importacao_produtos_tiny(df)
        assert resultado["Peso líquido (Kg)"].iloc[0] == "3.0"
        assert resultado["Peso bruto (Kg)"].iloc[0] == "3.0"


class TestTipoCorreto:
    def test_sem_codigo_pai_retorna_v(self):
        row = pd.Series({"codigo_pai": None})
        assert _tipo_correto(row) == "V"

    def test_codigo_pai_vazio_retorna_v(self):
        row = pd.Series({"codigo_pai": ""})
        assert _tipo_correto(row) == "V"

    def test_com_codigo_pai_retorna_k(self):
        row = pd.Series({"codigo_pai": "PAI001"})
        assert _tipo_correto(row) == "K"
