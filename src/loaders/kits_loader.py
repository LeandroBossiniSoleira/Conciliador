"""
kits_loader.py
Carrega planilhas de Kits do Magis e do Tiny, com suporte a múltiplos arquivos, e mapeia.
"""

import logging

import pandas as pd
import yaml
from pathlib import Path
from src.loaders.utils import ler_arquivo_robusto

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

def _carregar_mapa() -> dict:
    with open(CONFIG_DIR / "mapa_campos.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

def enriquecer_status_kits(df_kits: pd.DataFrame, df_produtos: pd.DataFrame | None) -> pd.DataFrame:
    """
    Enriquece o DataFrame de kits com o status (ATIVO/INATIVO) derivado do
    cadastro de produtos do Magis.

    Regra de negócio:
      - ATIVO  → kit existe nos produtos e está marcado como ATIVO
      - INATIVO → kit não existe nos produtos, está inativo ou excluído
      - DESCONHECIDO → planilha de produtos não foi carregada

    Parâmetros
    ----------
    df_kits : DataFrame com coluna 'sku_kit'
    df_produtos : DataFrame normalizado (colunas 'sku' e 'status').
                  Pode ser None quando a planilha de produtos não foi carregada.
    """
    df = df_kits.copy()

    if df_produtos is None or df_produtos.empty or "status" not in df_produtos.columns:
        df["status_kit"] = "DESCONHECIDO"
        return df

    status_por_sku: dict[str, str] = (
        df_produtos.set_index("sku")["status"].astype(str).str.upper().to_dict()
    )

    def _resolver(sku_kit: str) -> str:
        status = status_por_sku.get(str(sku_kit))
        if status is None:
            return "INATIVO"
        return "ATIVO" if status == "ATIVO" else "INATIVO"

    df["status_kit"] = df["sku_kit"].astype(str).map(_resolver)
    return df


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
        qtd_raw = df["qtd_componente"]
        df["qtd_componente"] = pd.to_numeric(qtd_raw, errors="coerce")
        invalidos = df["qtd_componente"].isna() & qtd_raw.notna() & (qtd_raw.astype(str).str.strip() != "")
        if invalidos.any():
            valores = qtd_raw[invalidos].unique().tolist()
            logger.warning(
                "Kits Magis: %d registro(s) com qtd_componente inválida convertida para 1. Valores: %s",
                invalidos.sum(), valores,
            )
        df["qtd_componente"] = df["qtd_componente"].fillna(1)

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
        qtd_raw = df["qtd_componente"]
        df["qtd_componente"] = pd.to_numeric(qtd_raw, errors="coerce")
        invalidos = df["qtd_componente"].isna() & qtd_raw.notna() & (qtd_raw.astype(str).str.strip() != "")
        if invalidos.any():
            valores = qtd_raw[invalidos].unique().tolist()
            logger.warning(
                "Kits Tiny: %d registro(s) com qtd_componente inválida convertida para 1. Valores: %s",
                invalidos.sum(), valores,
            )
        df["qtd_componente"] = df["qtd_componente"].fillna(1)

    df["sistema_origem"] = "TINY_KITS"
    return df
