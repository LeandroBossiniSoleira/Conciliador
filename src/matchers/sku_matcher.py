"""
sku_matcher.py
Match entre Magis e Tiny pelo campo SKU (merge outer).
"""

import pandas as pd


def match_por_sku(
    magis: pd.DataFrame,
    tiny: pd.DataFrame,
) -> pd.DataFrame:
    """
    Faz o merge outer entre os dois DataFrames usando o campo 'sku'.

    A coluna '_merge' indicará:
      - 'left_only'  → presente apenas no Magis
      - 'right_only' → presente apenas no Tiny
      - 'both'       → presente nos dois sistemas

    Parameters
    ----------
    magis : pd.DataFrame
        DataFrame normalizado do Magis.
    tiny : pd.DataFrame
        DataFrame normalizado do Tiny.

    Returns
    -------
    pd.DataFrame
    """
    resultado = magis.merge(
        tiny,
        on="sku",
        how="outer",
        suffixes=("_magis", "_tiny"),
        indicator=True,
    )

    return resultado
