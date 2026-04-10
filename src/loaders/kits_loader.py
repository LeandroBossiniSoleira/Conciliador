"""
kits_loader.py
Carrega planilhas de Kits do Magis e do Tiny, com suporte a múltiplos arquivos, e mapeia.
"""

import logging

import pandas as pd
from src.loaders.utils import carregar_generico

logger = logging.getLogger(__name__)


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


def _validar_qtd_componente(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Converte qtd_componente para numérico com logging de valores inválidos."""
    if "qtd_componente" not in df.columns:
        return df

    qtd_raw = df["qtd_componente"]
    df["qtd_componente"] = pd.to_numeric(qtd_raw, errors="coerce")
    invalidos = df["qtd_componente"].isna() & qtd_raw.notna() & (qtd_raw.astype(str).str.strip() != "")
    if invalidos.any():
        valores = qtd_raw[invalidos].unique().tolist()
        logger.warning(
            "Kits %s: %d registro(s) com qtd_componente inválida convertida para 1. Valores: %s",
            label, invalidos.sum(), valores,
        )
    df["qtd_componente"] = df["qtd_componente"].fillna(1)
    return df


def carregar_kits_magis(arquivos) -> pd.DataFrame:
    df = carregar_generico(arquivos, mapa_key="magis_kits", sistema_origem="MAGIS_KITS")
    return _validar_qtd_componente(df, "Magis")


def carregar_kits_tiny(arquivos) -> pd.DataFrame:
    df = carregar_generico(arquivos, mapa_key="tiny_kits", sistema_origem="TINY_KITS")
    return _validar_qtd_componente(df, "Tiny")
