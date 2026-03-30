"""
duplicidades.py
Detecta registros duplicados dentro de um mesmo sistema.
"""

import pandas as pd


def verificar_duplicidade(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """
    Retorna todos os registros com valores duplicados na coluna informada.

    Parameters
    ----------
    df : pd.DataFrame
    coluna : str
        Nome da coluna a verificar (ex.: 'sku', 'ean', 'ean_tributavel').

    Returns
    -------
    pd.DataFrame
        Subconjunto contendo apenas as linhas duplicadas, ordenado pela coluna.
    """
    if coluna not in df.columns:
        return pd.DataFrame()

    # Ignora nulos antes de checar duplicidade
    mask_nao_nulo = df[coluna].notna() & (df[coluna] != "")
    sub = df[mask_nao_nulo]

    duplicados = sub[sub.duplicated(coluna, keep=False)].sort_values(coluna)
    return duplicados


def relatorio_duplicidades(
    df: pd.DataFrame,
    colunas: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Gera um dicionário { coluna: DataFrame_de_duplicados }
    para cada coluna solicitada.

    Parameters
    ----------
    df : pd.DataFrame
    colunas : list[str], optional
        Colunas a verificar. Padrão: ['sku', 'ean', 'ean_tributavel'].

    Returns
    -------
    dict[str, pd.DataFrame]
    """
    if colunas is None:
        colunas = ["sku", "ean", "ean_tributavel"]

    resultado: dict[str, pd.DataFrame] = {}
    for col in colunas:
        dups = verificar_duplicidade(df, col)
        if not dups.empty:
            resultado[col] = dups

    return resultado
