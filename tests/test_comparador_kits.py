"""Testes para src/comparators/comparador_kits.py."""

import pandas as pd
import pytest

from src.comparators.comparador_kits import comparar_kits


# ────────────────────────────────────────────
# Fixtures locais
# ────────────────────────────────────────────

@pytest.fixture
def magis_kits_com_status():
    """Kits Magis com coluna status_kit."""
    return pd.DataFrame({
        "sku_kit": ["KIT01", "KIT01", "KIT02", "KIT02", "KIT03", "KIT03"],
        "titulo_kit": ["Kit A"] * 2 + ["Kit B"] * 2 + ["Kit C"] * 2,
        "sku_componente": ["C001", "C002", "C003", "C004", "C005", "C006"],
        "titulo_componente": ["Comp1", "Comp2", "Comp3", "Comp4", "Comp5", "Comp6"],
        "qtd_componente": [1, 2, 1, 3, 1, 1],
        "status_kit": ["ATIVO"] * 2 + ["INATIVO"] * 2 + ["ATIVO"] * 2,
    })


@pytest.fixture
def tiny_kits_basico():
    """Kits Tiny com KIT01 (mesmos componentes) e KIT04 (exclusivo Tiny)."""
    return pd.DataFrame({
        "sku_kit": ["KIT01", "KIT01", "KIT04", "KIT04"],
        "titulo_kit": ["Kit A"] * 2 + ["Kit D"] * 2,
        "sku_componente": ["C001", "C002", "C007", "C008"],
        "titulo_componente": ["Comp1", "Comp2", "Comp7", "Comp8"],
        "qtd_componente": [1, 2, 1, 1],
    })


# ────────────────────────────────────────────
# Retorno e chaves
# ────────────────────────────────────────────

class TestComararKitsRetorno:
    def test_retorna_todas_as_chaves(self, df_magis_kits, df_tiny_kits):
        resultado = comparar_kits(df_magis_kits, df_tiny_kits)
        chaves_esperadas = {
            "somente_magis", "somente_magis_inativos", "somente_magis_desconhecido",
            "somente_tiny", "divergentes", "nos_dois",
        }
        assert set(resultado.keys()) == chaves_esperadas

    def test_todos_valores_sao_dataframes(self, df_magis_kits, df_tiny_kits):
        resultado = comparar_kits(df_magis_kits, df_tiny_kits)
        for chave, valor in resultado.items():
            assert isinstance(valor, pd.DataFrame), f"{chave} não é DataFrame"

    def test_ambos_vazios(self):
        magis = pd.DataFrame()
        tiny = pd.DataFrame()
        resultado = comparar_kits(magis, tiny)
        assert resultado["somente_magis"].empty
        assert resultado["somente_tiny"].empty
        assert resultado["divergentes"].empty


# ────────────────────────────────────────────
# Classificação de kits
# ────────────────────────────────────────────

class TestClassificacaoKits:
    def test_kit_presente_nos_dois_com_mesmos_componentes(self, df_magis_kits, df_tiny_kits):
        """KIT01 está em ambos com mesmos componentes → nos_dois."""
        resultado = comparar_kits(df_magis_kits, df_tiny_kits)
        assert "KIT01" in resultado["nos_dois"]["sku_kit"].values

    def test_kit_exclusivo_magis(self, df_magis_kits, df_tiny_kits):
        """KIT02 está só no Magis; sem status_kit → vai para desconhecido."""
        resultado = comparar_kits(df_magis_kits, df_tiny_kits)
        # fixture df_magis_kits não tem status_kit, então status = DESCONHECIDO
        assert "KIT02" in resultado["somente_magis_desconhecido"]["sku_kit"].values

    def test_kit_exclusivo_tiny(self, magis_kits_com_status, tiny_kits_basico):
        """KIT04 está só no Tiny → somente_tiny."""
        resultado = comparar_kits(magis_kits_com_status, tiny_kits_basico)
        assert "KIT04" in resultado["somente_tiny"]["sku_kit"].values

    def test_kit_inativo_separado(self, magis_kits_com_status, tiny_kits_basico):
        """KIT02 é INATIVO no Magis → somente_magis_inativos."""
        resultado = comparar_kits(magis_kits_com_status, tiny_kits_basico)
        assert "KIT02" in resultado["somente_magis_inativos"]["sku_kit"].values
        # Não deve estar no somente_magis ativo
        if not resultado["somente_magis"].empty:
            assert "KIT02" not in resultado["somente_magis"]["sku_kit"].values


# ────────────────────────────────────────────
# Divergências
# ────────────────────────────────────────────

class TestDivergenciasKits:
    def test_detecta_componentes_diferentes(self):
        """Kit com mesmos SKUs de componentes mas quantidades diferentes."""
        magis = pd.DataFrame({
            "sku_kit": ["KIT01", "KIT01"],
            "titulo_kit": ["Kit A", "Kit A"],
            "sku_componente": ["C001", "C002"],
            "titulo_componente": ["Comp1", "Comp2"],
            "qtd_componente": [1, 2],
            "status_kit": ["ATIVO", "ATIVO"],
        })
        tiny = pd.DataFrame({
            "sku_kit": ["KIT01", "KIT01"],
            "titulo_kit": ["Kit A", "Kit A"],
            "sku_componente": ["C001", "C002"],
            "titulo_componente": ["Comp1", "Comp2"],
            "qtd_componente": [1, 5],  # qtd diferente
        })
        resultado = comparar_kits(magis, tiny)
        assert not resultado["divergentes"].empty
        assert "KIT01" in resultado["divergentes"]["sku_kit"].values

    def test_sem_divergencias_quando_iguais(self):
        magis = pd.DataFrame({
            "sku_kit": ["KIT01", "KIT01"],
            "titulo_kit": ["Kit A", "Kit A"],
            "sku_componente": ["C001", "C002"],
            "titulo_componente": ["Comp1", "Comp2"],
            "qtd_componente": [1, 2],
            "status_kit": ["ATIVO", "ATIVO"],
        })
        tiny = pd.DataFrame({
            "sku_kit": ["KIT01", "KIT01"],
            "titulo_kit": ["Kit A", "Kit A"],
            "sku_componente": ["C001", "C002"],
            "titulo_componente": ["Comp1", "Comp2"],
            "qtd_componente": [1, 2],
        })
        resultado = comparar_kits(magis, tiny)
        assert resultado["divergentes"].empty
        assert "KIT01" in resultado["nos_dois"]["sku_kit"].values

    def test_componente_extra_e_divergencia(self):
        """Kit com componente extra no Tiny."""
        magis = pd.DataFrame({
            "sku_kit": ["KIT01"],
            "titulo_kit": ["Kit A"],
            "sku_componente": ["C001"],
            "titulo_componente": ["Comp1"],
            "qtd_componente": [1],
            "status_kit": ["ATIVO"],
        })
        tiny = pd.DataFrame({
            "sku_kit": ["KIT01", "KIT01"],
            "titulo_kit": ["Kit A", "Kit A"],
            "sku_componente": ["C001", "C002"],
            "titulo_componente": ["Comp1", "Comp2"],
            "qtd_componente": [1, 1],
        })
        resultado = comparar_kits(magis, tiny)
        assert not resultado["divergentes"].empty


# ────────────────────────────────────────────
# Tratamento de qtd_componente inválida
# ────────────────────────────────────────────

class TestQtdComponenteInvalida:
    def test_qtd_nao_numerica_vira_1(self):
        """Qtd inválida é convertida para 1 (fallback)."""
        magis = pd.DataFrame({
            "sku_kit": ["KIT01"],
            "titulo_kit": ["Kit A"],
            "sku_componente": ["C001"],
            "titulo_componente": ["Comp1"],
            "qtd_componente": ["abc"],
            "status_kit": ["ATIVO"],
        })
        tiny = pd.DataFrame({
            "sku_kit": ["KIT01"],
            "titulo_kit": ["Kit A"],
            "sku_componente": ["C001"],
            "titulo_componente": ["Comp1"],
            "qtd_componente": [1],
        })
        resultado = comparar_kits(magis, tiny)
        # Com fallback para 1, devem ser iguais
        assert "KIT01" in resultado["nos_dois"]["sku_kit"].values

    def test_qtd_none_vira_1(self):
        magis = pd.DataFrame({
            "sku_kit": ["KIT01"],
            "titulo_kit": ["Kit A"],
            "sku_componente": ["C001"],
            "titulo_componente": ["Comp1"],
            "qtd_componente": [None],
            "status_kit": ["ATIVO"],
        })
        tiny = pd.DataFrame({
            "sku_kit": ["KIT01"],
            "titulo_kit": ["Kit A"],
            "sku_componente": ["C001"],
            "titulo_componente": ["Comp1"],
            "qtd_componente": [1],
        })
        resultado = comparar_kits(magis, tiny)
        assert "KIT01" in resultado["nos_dois"]["sku_kit"].values


# ────────────────────────────────────────────
# Apenas um lado com dados
# ────────────────────────────────────────────

class TestUmLadoVazio:
    def test_magis_vazio(self, df_tiny_kits):
        magis = pd.DataFrame()
        resultado = comparar_kits(magis, df_tiny_kits)
        assert resultado["somente_magis"].empty
        assert not resultado["somente_tiny"].empty

    def test_tiny_vazio(self, df_magis_kits):
        tiny = pd.DataFrame()
        resultado = comparar_kits(df_magis_kits, tiny)
        # fixture sem status_kit → todos vão para desconhecido, não somente_magis
        assert not resultado["somente_magis_desconhecido"].empty
        assert resultado["somente_tiny"].empty
