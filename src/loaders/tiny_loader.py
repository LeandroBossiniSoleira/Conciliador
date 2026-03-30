"""
tiny_loader.py
Carrega a planilha exportada do Olist Tiny e mapeia as colunas para o schema padrão.
"""

import pandas as pd
import yaml
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _carregar_mapa() -> dict:
    """Lê o mapeamento de colunas do YAML de configuração."""
    with open(CONFIG_DIR / "mapa_campos.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
    mapa = _carregar_mapa()
    colunas_tiny: dict = mapa.get("tiny", {})

    if not isinstance(caminho_ou_arquivo, list):
        caminho_ou_arquivo = [caminho_ou_arquivo]

    dfs = []
    for f in caminho_ou_arquivo:
        df_temp = pd.read_excel(f, dtype=str)
        dfs.append(df_temp)
        
    if not dfs:
        return pd.DataFrame()
        
    df = pd.concat(dfs, ignore_index=True)

    # Renomeia apenas as colunas que existem no arquivo
    colunas_presentes = {k: v for k, v in colunas_tiny.items() if k in df.columns}
    df = df.rename(columns=colunas_presentes)
    
    if "sku" not in df.columns:
        if "Código" in df.columns:
            df["sku"] = df["Código"]
        elif "Código (SKU)" in df.columns:
            df["sku"] = df["Código (SKU)"]

    # Marca a origem do registro
    df["sistema_origem"] = "TINY"

    return df
