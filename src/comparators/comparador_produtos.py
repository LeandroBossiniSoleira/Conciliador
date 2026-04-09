"""
comparador_produtos.py
Orquestra os matchers e classifica cada registro de acordo
com a presença nos dois sistemas.
"""

import pandas as pd

from src.matchers.sku_matcher import match_por_sku
from src.matchers.ean_matcher import match_por_ean
from src.matchers.similaridade_matcher import sugerir_matches_por_titulo
from src.validators.fiscal_validator import validar_fiscal
from src.validators.duplicidades import relatorio_duplicidades


# ────────────────────────────────────────────
# Status
# ────────────────────────────────────────────

_STATUSES_INATIVOS = {"INATIVO", "EXCLUIDO"}


def _separar_por_status(
    df: pd.DataFrame, col_status: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Divide *df* em (ativos, inativos).

    Registros com status ausente ou não reconhecido são considerados ativos
    para não suprimir dados potencialmente válidos.
    """
    if col_status not in df.columns:
        return df.copy(), pd.DataFrame(columns=df.columns)
    mask_inativo = df[col_status].fillna("").str.upper().isin(_STATUSES_INATIVOS)
    return df[~mask_inativo].copy(), df[mask_inativo].copy()


# ────────────────────────────────────────────
# Classificação
# ────────────────────────────────────────────

def classificar(row: pd.Series) -> str:
    """Classifica o registro de acordo com o resultado do merge."""
    merge = row.get("_merge", "")
    if merge == "left_only":
        return "SOMENTE_MAGIS"
    if merge == "right_only":
        return "SOMENTE_TINY"
    if merge == "both":
        return "PRESENTE_NOS_DOIS"
    return "ERRO"


# ────────────────────────────────────────────
# Detecção de divergências em campos fiscais
# ────────────────────────────────────────────

CAMPOS_COMPARACAO = ["ncm", "cest", "origem", "ean_tributavel"]


def detectar_divergencias(df_both: pd.DataFrame) -> pd.DataFrame:
    """
    Para registros presentes nos dois sistemas, compara os campos
    fiscais e retorna apenas os que possuem ao menos uma divergência.
    """
    divergencias = []

    for campo in CAMPOS_COMPARACAO:
        col_magis = f"{campo}_magis"
        col_tiny = f"{campo}_tiny"

        if col_magis not in df_both.columns or col_tiny not in df_both.columns:
            continue

        mask = (
            df_both[col_magis].fillna("").astype(str)
            != df_both[col_tiny].fillna("").astype(str)
        )
        if mask.any():
            sub = df_both[mask].copy()
            sub["campo_divergente"] = campo
            sub["valor_magis"] = sub[col_magis]
            sub["valor_tiny"] = sub[col_tiny]
            divergencias.append(
                sub[["sku", "campo_divergente", "valor_magis", "valor_tiny"]]
            )

    if divergencias:
        return pd.concat(divergencias, ignore_index=True)
    return pd.DataFrame(columns=["sku", "campo_divergente", "valor_magis", "valor_tiny"])


# ────────────────────────────────────────────
# Pipeline completa
# ────────────────────────────────────────────

def executar_comparacao(
    magis: pd.DataFrame,
    tiny: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """
    Executa a pipeline completa de comparação e retorna um dicionário
    com todos os DataFrames de resultado.

    Returns
    -------
    dict[str, pd.DataFrame]
        Chaves:
        - comparativo_geral
        - somente_magis
        - somente_tiny
        - presente_nos_dois
        - divergencias_fiscais
        - duplicidades_sku_magis
        - duplicidades_ean_magis
        - duplicidades_sku_tiny
        - duplicidades_ean_tiny
        - sugestao_match_ean
        - sugestao_match_titulo
    """
    resultados: dict[str, pd.DataFrame] = {}

    # 1) Match por SKU (merge outer)
    comp = match_por_sku(magis, tiny)
    comp["classificacao"] = comp.apply(classificar, axis=1)
    resultados["comparativo_geral"] = comp

    # 2) Segmentar
    somente_magis_raw = comp[comp["classificacao"] == "SOMENTE_MAGIS"].copy()
    somente_tiny_raw  = comp[comp["classificacao"] == "SOMENTE_TINY"].copy()
    nos_dois = comp[comp["classificacao"] == "PRESENTE_NOS_DOIS"].copy()

    # Remover inativos/excluídos — não exigem ação de migração
    somente_magis, somente_magis_inativos = _separar_por_status(somente_magis_raw, "status_magis")
    somente_tiny,  somente_tiny_inativos  = _separar_por_status(somente_tiny_raw,  "status_tiny")

    resultados["somente_magis"]          = somente_magis
    resultados["somente_magis_inativos"] = somente_magis_inativos
    resultados["somente_tiny"]           = somente_tiny
    resultados["somente_tiny_inativos"]  = somente_tiny_inativos
    resultados["presente_nos_dois"]      = nos_dois

    # 3) Divergências fiscais (registros que estão nos dois)
    resultados["divergencias_fiscais"] = detectar_divergencias(nos_dois)

    # 4) Duplicidades internas (cada sistema separado)
    dups_magis = relatorio_duplicidades(magis, ["sku", "ean", "ean_tributavel"])
    dups_tiny = relatorio_duplicidades(tiny, ["sku", "ean", "ean_tributavel"])

    resultados["duplicidades_sku_magis"] = dups_magis.get("sku", pd.DataFrame())
    resultados["duplicidades_ean_magis"] = dups_magis.get("ean", pd.DataFrame())
    resultados["duplicidades_sku_tiny"] = dups_tiny.get("sku", pd.DataFrame())
    resultados["duplicidades_ean_tiny"] = dups_tiny.get("ean", pd.DataFrame())

    # 5) Sugestão de match por EAN (para os sem match por SKU)
    try:
        resultados["sugestao_match_ean"] = match_por_ean(magis, tiny)
    except Exception:
        resultados["sugestao_match_ean"] = pd.DataFrame()

    # 6) Sugestão de match por título (para os sem match por SKU)
    try:
        resultados["sugestao_match_titulo"] = sugerir_matches_por_titulo(
            somente_magis, somente_tiny, top_n=3
        )
    except Exception:
        resultados["sugestao_match_titulo"] = pd.DataFrame()

    # 7) Validação fiscal em cada sistema original
    magis_fiscal = validar_fiscal(magis.copy())
    tiny_fiscal = validar_fiscal(tiny.copy())
    erros_fiscais_magis = magis_fiscal[magis_fiscal["tem_erro_fiscal"]].copy()
    erros_fiscais_tiny = tiny_fiscal[tiny_fiscal["tem_erro_fiscal"]].copy()
    resultados["erros_fiscais_magis"] = erros_fiscais_magis
    resultados["erros_fiscais_tiny"] = erros_fiscais_tiny

    return resultados
