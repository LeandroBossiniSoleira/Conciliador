"""
tiny_loader.py
Carrega a planilha exportada do Olist Tiny e mapeia as colunas para o schema padrão.
"""

import pandas as pd
from src.loaders.utils import carregar_generico


def carregar_tiny(caminho_ou_arquivo) -> pd.DataFrame:
    """
    Lê o arquivo Excel exportado do Tiny e devolve um DataFrame
    com as colunas renomeadas para o schema padrão.

    Parameters
    ----------
    caminho_ou_arquivo : str, file-like object, ou list
        Arquivo(s) do Tiny.

    Returns
    -------
    pd.DataFrame
    """
    df = carregar_generico(caminho_ou_arquivo, mapa_key="tiny", sistema_origem="TINY")

    # Fallbacks caso a coluna "sku" ainda não exista após o mapeamento
    if "sku" not in df.columns:
        if "Código" in df.columns:
            df["sku"] = df["Código"]
        elif "Código (SKU)" in df.columns:
            df["sku"] = df["Código (SKU)"]

    return df
