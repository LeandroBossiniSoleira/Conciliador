"""
Fixtures compartilhadas para os testes do comparador de produtos.
"""

import io
import sys
from pathlib import Path

import pandas as pd
import pytest

# Garante que o diretório raiz do projeto está no sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def df_magis_basico():
    """DataFrame normalizado do Magis com dados mínimos."""
    return pd.DataFrame({
        "sku": ["SKU001", "SKU002", "SKU003"],
        "titulo": ["PRODUTO A", "PRODUTO B", "PRODUTO C"],
        "ean": ["7891234560001", "7891234560002", ""],
        "ean_tributavel": ["7891234560001", "7891234560002", ""],
        "ncm": ["12345678", "87654321", None],
        "cest": ["1234567", None, "9999999"],
        "origem": ["0", "0", "1"],
        "preco_custo": [10.50, 20.00, 0.0],
        "estoque": [100, 50, 0],
        "status": ["ATIVO", "ATIVO", "INATIVO"],
        "marca": ["MARCA X", "MARCA Y", "MARCA Z"],
        "sistema_origem": ["MAGIS"] * 3,
    })


@pytest.fixture
def df_tiny_basico():
    """DataFrame normalizado do Tiny com dados mínimos."""
    return pd.DataFrame({
        "sku": ["SKU001", "SKU004", "SKU005"],
        "titulo": ["PRODUTO A TINY", "PRODUTO D", "PRODUTO E"],
        "ean": ["7891234560001", "7891234560004", "7891234560005"],
        "ean_tributavel": ["7891234560001", "7891234560004", "7891234560005"],
        "ncm": ["12345678", "11111111", "22222222"],
        "cest": ["1234567", "2222222", "3333333"],
        "origem": ["0", "0", "2"],
        "preco_custo": [10.50, 30.00, 15.00],
        "estoque": [100, 200, 75],
        "status": ["ATIVO", "ATIVO", "INATIVO"],
        "marca": ["MARCA X", "MARCA D", "MARCA E"],
        "sistema_origem": ["TINY"] * 3,
    })


@pytest.fixture
def df_magis_kits():
    """DataFrame de kits do Magis."""
    return pd.DataFrame({
        "sku_kit": ["KIT01", "KIT01", "KIT02", "KIT02"],
        "titulo_kit": ["Kit Combo A", "Kit Combo A", "Kit Combo B", "Kit Combo B"],
        "sku_componente": ["SKU001", "SKU002", "SKU003", "SKU004"],
        "titulo_componente": ["Prod A", "Prod B", "Prod C", "Prod D"],
        "qtd_componente": [1, 2, 1, 3],
        "sistema_origem": ["MAGIS_KITS"] * 4,
    })


@pytest.fixture
def df_tiny_kits():
    """DataFrame de kits do Tiny."""
    return pd.DataFrame({
        "sku_kit": ["KIT01", "KIT01"],
        "titulo_kit": ["Kit Combo A", "Kit Combo A"],
        "sku_componente": ["SKU001", "SKU002"],
        "titulo_componente": ["Prod A", "Prod B"],
        "qtd_componente": [1, 2],
        "sistema_origem": ["TINY_KITS"] * 2,
    })


@pytest.fixture
def xlsx_simples():
    """Gera um arquivo XLSX em memória para testar loaders."""
    df = pd.DataFrame({
        "SKU": ["SKU001", "SKU002"],
        "Título": ["Produto A", "Produto B"],
        "Ean": ["7891234560001", "7891234560002"],
        "Status": ["active", "inactive"],
    })
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf


@pytest.fixture
def csv_simples():
    """Gera um arquivo CSV em memória para testar fallback do leitor."""
    conteudo = "SKU;Titulo;Status\nSKU001;Produto A;active\nSKU002;Produto B;inactive\n"
    buf = io.BytesIO(conteudo.encode("utf-8"))
    buf.seek(0)
    return buf
