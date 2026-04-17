"""
catalogo_tiny.py
Filtros para recortes do catálogo do Tiny ERP (sem depender do Magis).
"""

import pandas as pd


def _normalizar_codigo_pai(serie: pd.Series) -> pd.Series:
    """Converte a coluna para string, remove espaços comuns e no-break space."""
    return (
        serie.astype(str)
        .str.replace("\xa0", "", regex=False)
        .str.strip()
    )


def filtrar_produtos_pai(tiny_norm: pd.DataFrame) -> pd.DataFrame:
    """Retorna apenas SKUs cujo 'codigo_pai' é vazio/nulo (produtos pai).

    Um produto é pai quando a coluna 'codigo_pai' NÃO está preenchida
    (coluna AL no arquivo Tiny = "Código do pai"). Quando preenchida,
    o produto é uma variação (filho) do SKU referenciado.

    Trata NaN, None, string vazia, espaços comuns e no-break space
    (\\xa0, frequente em exportações HTML) como "vazio".
    """
    if tiny_norm is None or tiny_norm.empty:
        return pd.DataFrame()

    if "codigo_pai" not in tiny_norm.columns:
        return tiny_norm.copy()

    col = tiny_norm["codigo_pai"]
    eh_vazio = col.isna() | (_normalizar_codigo_pai(col) == "")
    return tiny_norm.loc[eh_vazio].copy()
