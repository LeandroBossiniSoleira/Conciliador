"""Testes para src/validators/ — fiscal_validator e duplicidades."""

import pandas as pd

from src.validators.fiscal_validator import validar_registro, validar_fiscal
from src.validators.duplicidades import verificar_duplicidade, relatorio_duplicidades


class TestValidarRegistro:
    def test_sem_erros_quando_campos_preenchidos(self):
        row = pd.Series({"ncm": "12345678", "origem": "0"})
        erros = validar_registro(row, ["ncm", "origem"])
        assert erros == []

    def test_detecta_campo_ausente(self):
        row = pd.Series({"ncm": None, "origem": "0"})
        erros = validar_registro(row, ["ncm", "origem"])
        assert "SEM_NCM" in erros

    def test_detecta_campo_vazio(self):
        row = pd.Series({"ncm": "", "origem": "0"})
        erros = validar_registro(row, ["ncm", "origem"])
        assert "SEM_NCM" in erros

    def test_detecta_campo_espacos(self):
        row = pd.Series({"ncm": "   ", "origem": "0"})
        erros = validar_registro(row, ["ncm", "origem"])
        assert "SEM_NCM" in erros

    def test_detecta_multiplos_erros(self):
        row = pd.Series({"ncm": None, "origem": None})
        erros = validar_registro(row, ["ncm", "origem"])
        assert len(erros) == 2


class TestValidarFiscal:
    def test_adiciona_colunas_de_erro(self, df_magis_basico):
        resultado = validar_fiscal(df_magis_basico.copy())
        assert "erros_fiscais" in resultado.columns
        assert "tem_erro_fiscal" in resultado.columns

    def test_detecta_ncm_ausente(self):
        df = pd.DataFrame({
            "sku": ["SKU001"],
            "ncm": [None],
            "origem": ["0"],
        })
        resultado = validar_fiscal(df)
        assert resultado["tem_erro_fiscal"].iloc[0] == True


class TestVerificarDuplicidade:
    def test_detecta_sku_duplicado(self):
        df = pd.DataFrame({"sku": ["A", "B", "A", "C"]})
        dups = verificar_duplicidade(df, "sku")
        assert len(dups) == 2
        assert set(dups["sku"]) == {"A"}

    def test_sem_duplicidade(self):
        df = pd.DataFrame({"sku": ["A", "B", "C"]})
        dups = verificar_duplicidade(df, "sku")
        assert dups.empty

    def test_ignora_nulos(self):
        df = pd.DataFrame({"sku": ["A", None, None, "B"]})
        dups = verificar_duplicidade(df, "sku")
        assert dups.empty

    def test_ignora_vazios(self):
        df = pd.DataFrame({"sku": ["A", "", "", "B"]})
        dups = verificar_duplicidade(df, "sku")
        assert dups.empty

    def test_coluna_inexistente(self):
        df = pd.DataFrame({"sku": ["A"]})
        dups = verificar_duplicidade(df, "coluna_fake")
        assert dups.empty


class TestRelatorioDuplicidades:
    def test_retorna_dict_com_duplicidades(self):
        df = pd.DataFrame({
            "sku": ["A", "A", "B"],
            "ean": ["111", "222", "111"],
        })
        resultado = relatorio_duplicidades(df, ["sku", "ean"])
        assert "sku" in resultado
        assert "ean" in resultado

    def test_retorna_dict_vazio_sem_duplicidades(self):
        df = pd.DataFrame({
            "sku": ["A", "B", "C"],
            "ean": ["111", "222", "333"],
        })
        resultado = relatorio_duplicidades(df, ["sku", "ean"])
        assert resultado == {}
