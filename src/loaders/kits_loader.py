"""
kits_loader.py
Carrega planilhas de Kits do Magis e do Tiny, com suporte a múltiplos arquivos, e mapeia.
"""

import pandas as pd
import yaml
from pathlib import Path
from src.loaders.utils import ler_arquivo_robusto

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

def _carregar_mapa() -> dict:
    with open(CONFIG_DIR / "mapa_campos.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

def carregar_kits_magis(arquivos) -> pd.DataFrame:
    mapa = _carregar_mapa()
    colunas = mapa.get("magis_kits", {})
    
    if not isinstance(arquivos, list):
        arquivos = [arquivos]
        
    dfs = []
    for f in arquivos:
        df_temp = ler_arquivo_robusto(f)
        dfs.append(df_temp)
        
    if not dfs:
        return pd.DataFrame()
        
    df = pd.concat(dfs, ignore_index=True)
    
    colunas_presentes = {k: v for k, v in colunas.items() if k in df.columns}
    df = df.rename(columns=colunas_presentes)
    
    # Clean up quantities
    if "qtd_componente" in df.columns:
        df["qtd_componente"] = pd.to_numeric(df["qtd_componente"], errors="coerce").fillna(1)
        
    df["sistema_origem"] = "MAGIS_KITS"
    return df

def carregar_kits_tiny(arquivos) -> pd.DataFrame:
    mapa = _carregar_mapa()
    colunas = mapa.get("tiny_kits", {})
    
    if not isinstance(arquivos, list):
        arquivos = [arquivos]
        
    dfs = []
    for f in arquivos:
        df_temp = ler_arquivo_robusto(f)
        dfs.append(df_temp)
        
    if not dfs:
        return pd.DataFrame()
        
    df = pd.concat(dfs, ignore_index=True)
    
    colunas_presentes = {k: v for k, v in colunas.items() if k in df.columns}
    df = df.rename(columns=colunas_presentes)
    
    # Clean up quantities
    if "qtd_componente" in df.columns:
        df["qtd_componente"] = pd.to_numeric(df["qtd_componente"], errors="coerce").fillna(1)
        
    df["sistema_origem"] = "TINY_KITS"
    return df
