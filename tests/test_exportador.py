"""Testes para src/reports/exportador_tiny.py — geração de planilhas de importação."""

import pandas as pd
import pytest

from src.reports.exportador_tiny import (
    LAYOUT_IMPORTACAO_TINY,
    gerar_planilha_importacao_produtos_tiny,
    gerar_planilha_importacao_tiny,
    verificar_tipos_produto,
    _buscar_produto_tiny,
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


# ────────────────────────────────────────────
# _buscar_produto_tiny
# ────────────────────────────────────────────

class TestBuscarProdutoTiny:
    def test_encontra_sku_existente(self):
        df = pd.DataFrame({"sku": ["SKU001", "SKU002"], "titulo": ["A", "B"]})
        resultado = _buscar_produto_tiny("SKU001", df)
        assert resultado is not None
        assert resultado["titulo"] == "A"

    def test_retorna_none_para_sku_inexistente(self):
        df = pd.DataFrame({"sku": ["SKU001"], "titulo": ["A"]})
        assert _buscar_produto_tiny("SKU999", df) is None

    def test_compara_como_string(self):
        df = pd.DataFrame({"sku": [123], "titulo": ["Num"]})
        resultado = _buscar_produto_tiny("123", df)
        assert resultado is not None


# ────────────────────────────────────────────
# verificar_tipos_produto
# ────────────────────────────────────────────

class TestVerificarTiposProduto:
    def test_detecta_tipo_incorreto(self):
        df_tiny = pd.DataFrame({
            "sku": ["KIT01"],
            "titulo": ["Kit A"],
            "tipo_produto": ["P"],
            "status": ["ATIVO"],
        })
        alertas, correcoes = verificar_tipos_produto({"KIT01"}, df_tiny, tipo_esperado="K")
        assert len(alertas) == 1
        assert alertas[0]["tipo_atual"] == "P"
        assert alertas[0]["tipo_esperado"] == "K"
        assert len(correcoes) == 1

    def test_sem_alerta_quando_tipo_correto(self):
        df_tiny = pd.DataFrame({
            "sku": ["KIT01"],
            "titulo": ["Kit A"],
            "tipo_produto": ["K"],
            "status": ["ATIVO"],
        })
        alertas, correcoes = verificar_tipos_produto({"KIT01"}, df_tiny, tipo_esperado="K")
        assert alertas == []
        assert correcoes == []

    def test_ignora_sku_nao_encontrado(self):
        df_tiny = pd.DataFrame({"sku": ["SKU001"], "titulo": ["A"], "tipo_produto": ["P"]})
        alertas, correcoes = verificar_tipos_produto({"SKU999"}, df_tiny)
        assert alertas == []

    def test_tiny_none_retorna_vazio(self):
        alertas, correcoes = verificar_tipos_produto({"KIT01"}, None)
        assert alertas == []
        assert correcoes == []

    def test_tiny_vazio_retorna_vazio(self):
        alertas, correcoes = verificar_tipos_produto({"KIT01"}, pd.DataFrame())
        assert alertas == []


# ────────────────────────────────────────────
# gerar_planilha_importacao_tiny (kits)
# ────────────────────────────────────────────

class TestGerarPlanilhaImportacaoKits:
    @pytest.fixture
    def magis_kits_raw(self):
        return pd.DataFrame({
            "sku_kit": ["KIT01", "KIT01"],
            "titulo_kit": ["Kit Combo", "Kit Combo"],
            "sku_componente": ["C001", "C002"],
            "titulo_componente": ["Comp A", "Comp B"],
            "qtd_componente": [1, 2],
            "status_kit": ["ATIVO", "ATIVO"],
        })

    @pytest.fixture
    def somente_magis_kits(self):
        return pd.DataFrame({"sku_kit": ["KIT01"]})

    @pytest.fixture
    def tiny_produtos(self):
        return pd.DataFrame({
            "sku": ["KIT01", "C001", "C002"],
            "titulo": ["Kit Combo", "Comp A", "Comp B"],
            "tipo_produto": ["K", "P", "P"],
            "status": ["ATIVO", "ATIVO", "ATIVO"],
        })

    def test_gera_linhas_de_importacao(self, magis_kits_raw, somente_magis_kits, tiny_produtos):
        df_imp, rejeitados, _, _ = gerar_planilha_importacao_tiny(
            magis_kits_raw, somente_magis_kits, tiny_produtos
        )
        assert len(df_imp) == 2
        assert "SKU kit/fabricado" in df_imp.columns
        assert "SKU componente" in df_imp.columns
        assert rejeitados == []

    def test_7_colunas_no_layout_kits(self, magis_kits_raw, somente_magis_kits, tiny_produtos):
        df_imp, _, _, _ = gerar_planilha_importacao_tiny(
            magis_kits_raw, somente_magis_kits, tiny_produtos
        )
        assert len(df_imp.columns) == 7

    def test_rejeita_kit_com_componente_ausente(self, magis_kits_raw, somente_magis_kits):
        tiny_sem_componente = pd.DataFrame({
            "sku": ["KIT01"],  # C001 e C002 ausentes
            "titulo": ["Kit Combo"],
            "tipo_produto": ["K"],
            "status": ["ATIVO"],
        })
        df_imp, rejeitados, _, _ = gerar_planilha_importacao_tiny(
            magis_kits_raw, somente_magis_kits, tiny_sem_componente
        )
        assert df_imp.empty
        assert len(rejeitados) == 1
        assert "ausente" in rejeitados[0]["motivo"].lower()

    def test_rejeita_kit_pai_ausente_no_tiny(self, magis_kits_raw, somente_magis_kits):
        tiny_sem_pai = pd.DataFrame({
            "sku": ["C001", "C002"],  # KIT01 ausente
            "titulo": ["Comp A", "Comp B"],
            "tipo_produto": ["P", "P"],
            "status": ["ATIVO", "ATIVO"],
        })
        df_imp, rejeitados, _, _ = gerar_planilha_importacao_tiny(
            magis_kits_raw, somente_magis_kits, tiny_sem_pai
        )
        assert df_imp.empty
        assert len(rejeitados) == 1

    def test_rejeita_kit_inativo_no_magis(self, somente_magis_kits, tiny_produtos):
        magis_inativo = pd.DataFrame({
            "sku_kit": ["KIT01", "KIT01"],
            "titulo_kit": ["Kit Combo", "Kit Combo"],
            "sku_componente": ["C001", "C002"],
            "titulo_componente": ["Comp A", "Comp B"],
            "qtd_componente": [1, 2],
            "status_kit": ["INATIVO", "INATIVO"],
        })
        df_imp, rejeitados, _, _ = gerar_planilha_importacao_tiny(
            magis_inativo, somente_magis_kits, tiny_produtos
        )
        assert df_imp.empty
        assert len(rejeitados) == 1
        assert "inativo" in rejeitados[0]["motivo"].lower()

    def test_ambos_vazios_retorna_vazio(self):
        df_imp, rejeitados, df_corr, alertas = gerar_planilha_importacao_tiny(
            pd.DataFrame(), pd.DataFrame()
        )
        assert df_imp.empty
        assert rejeitados == []
        assert df_corr.empty
        assert alertas == []

    def test_gera_correcao_tipo_quando_necessario(self, somente_magis_kits):
        magis = pd.DataFrame({
            "sku_kit": ["KIT01", "KIT01"],
            "titulo_kit": ["Kit Combo", "Kit Combo"],
            "sku_componente": ["C001", "C002"],
            "titulo_componente": ["Comp A", "Comp B"],
            "qtd_componente": [1, 2],
            "status_kit": ["ATIVO", "ATIVO"],
        })
        tiny = pd.DataFrame({
            "sku": ["KIT01", "C001", "C002"],
            "titulo": ["Kit Combo", "Comp A", "Comp B"],
            "tipo_produto": ["P", "P", "P"],  # KIT01 deveria ser K
            "status": ["ATIVO", "ATIVO", "ATIVO"],
        })
        _, rejeitados, df_corr, alertas = gerar_planilha_importacao_tiny(
            magis, somente_magis_kits, tiny
        )
        assert len(alertas) >= 1
        assert not df_corr.empty
