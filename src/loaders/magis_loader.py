"""
magis_loader.py
Carrega a planilha exportada do Magis 5 e mapeia as colunas para o schema padrão.
"""

import pandas as pd
from src.loaders.utils import carregar_generico


def carregar_magis(caminho_ou_arquivo) -> pd.DataFrame:
    """
    Lê o arquivo Excel exportado do Magis e devolve um DataFrame
    com as colunas renomeadas para o schema padrão.

    Parameters
    ----------
    caminho_ou_arquivo : str, file-like object, ou list
        Arquivo(s) do Magis.

    Returns
    -------
    pd.DataFrame
    """
    df = carregar_generico(caminho_ou_arquivo, mapa_key="magis", sistema_origem="MAGIS")

    # Fallbacks caso a coluna "sku" ainda não exista após o mapeamento
    if "sku" not in df.columns:
        if "Id" in df.columns and "SKU" in df.columns:
            df["sku"] = df["SKU"]
        elif "SKU (N)" in df.columns:
            df["sku"] = df["SKU (N)"]

    return df
