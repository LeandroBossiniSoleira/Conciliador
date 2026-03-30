"""
ean_matcher.py
Match entre Magis e Tiny pelo campo EAN tributável.
Usado para sugerir correspondência quando o SKU difere.
"""

import pandas as pd


def match_por_ean(
    magis: pd.DataFrame,
    tiny: pd.DataFrame,
) -> pd.DataFrame:
    """
    Faz inner join entre os DataFrames usando 'ean_tributavel'.
    Retorna apenas os registros que batem.

    Parameters
    ----------
    magis : pd.DataFrame
    tiny : pd.DataFrame

    Returns
    -------
    pd.DataFrame
    """
    # Remove linhas sem EAN tributável
    m = magis[magis["ean_tributavel"].notna() & (magis["ean_tributavel"] != "")].copy()
    t = tiny[tiny["ean_tributavel"].notna() & (tiny["ean_tributavel"] != "")].copy()

    resultado = m.merge(
        t,
        on="ean_tributavel",
        how="inner",
        suffixes=("_magis", "_tiny"),
    )

    return resultado


def match_por_ean_comum(
    magis: pd.DataFrame,
    tiny: pd.DataFrame,
) -> pd.DataFrame:
    """
    Faz inner join usando o campo 'ean' (EAN normal, não tributável).

    Parameters
    ----------
    magis : pd.DataFrame
    tiny : pd.DataFrame

    Returns
    -------
    pd.DataFrame
    """
    m = magis[magis["ean"].notna() & (magis["ean"] != "")].copy()
    t = tiny[tiny["ean"].notna() & (tiny["ean"] != "")].copy()

    resultado = m.merge(
        t,
        on="ean",
        how="inner",
        suffixes=("_magis", "_tiny"),
    )

    return resultado
