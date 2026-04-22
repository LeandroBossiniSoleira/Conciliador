"""
exportador.py
Produz as duas saídas da aba 'Correção de SKUs':

1. Lista de renomeação (auditoria) — DataFrame simples com
   sku_original, sku_sugerido, titulo, status, confianca, problemas.
2. Planilha de importação Tiny (64 colunas) com o SKU já renomeado,
   reaproveitando `gerar_planilha_importacao_produtos_tiny`.
"""

from __future__ import annotations

import pandas as pd

from src.reports.exportador_tiny import gerar_planilha_importacao_produtos_tiny


def gerar_lista_renomeacao(df_analise: pd.DataFrame) -> pd.DataFrame:
    """Extrai as colunas relevantes da análise para auditoria/renomeação."""
    colunas = [
        "sku_original", "sku_sugerido", "titulo",
        "status", "tipo_erro", "confianca", "precisa_acao_manual",
        "problemas_txt",
    ]
    colunas_existentes = [c for c in colunas if c in df_analise.columns]
    out = df_analise[colunas_existentes].copy()
    out = out.rename(columns={
        "sku_original":          "SKU atual",
        "sku_sugerido":          "SKU sugerido",
        "titulo":                "Título",
        "status":                "Status",
        "tipo_erro":             "Tipo de erro",
        "confianca":             "Confiança (%)",
        "precisa_acao_manual":   "Precisa ação manual",
        "problemas_txt":         "Problemas",
    })
    return out


def gerar_planilha_tiny_renomeada(
    df_tiny_norm: pd.DataFrame,
    mapa_renomeacao: dict[str, str],
) -> pd.DataFrame:
    """Gera a planilha Tiny (64 colunas) para os SKUs aprovados, com o novo SKU.

    Parâmetros
    ----------
    df_tiny_norm : DataFrame normalizado do Tiny (session_state['tiny_norm']).
    mapa_renomeacao : dict {sku_atual: sku_novo} — apenas SKUs aprovados pelo usuário.

    Retorna
    -------
    DataFrame no layout Tiny com os SKUs substituídos.
    """
    if not mapa_renomeacao:
        return pd.DataFrame()

    # Filtra só os SKUs a renomear
    df = df_tiny_norm[df_tiny_norm["sku"].astype(str).isin(mapa_renomeacao.keys())].copy()
    if df.empty:
        return pd.DataFrame()

    # Substitui o SKU pelo sugerido
    df["sku"] = df["sku"].astype(str).map(lambda s: mapa_renomeacao.get(s, s))

    return gerar_planilha_importacao_produtos_tiny(df)
