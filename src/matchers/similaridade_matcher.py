"""
similaridade_matcher.py
Usa rapidfuzz para sugerir correspondência entre títulos de produtos
que não bateram por SKU nem EAN.
"""

import logging

import pandas as pd
import yaml
from pathlib import Path
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _carregar_limiares() -> dict:
    with open(CONFIG_DIR / "regras_normalizacao.yaml", encoding="utf-8") as f:
        regras = yaml.safe_load(f)
    return regras.get("similaridade", {})


def similaridade(titulo1: str | None, titulo2: str | None) -> float:
    """
    Calcula a similaridade entre dois títulos usando token_sort_ratio.

    Retorna um float de 0 a 100.
    """
    if not titulo1 or not titulo2:
        return 0.0
    return fuzz.token_sort_ratio(titulo1, titulo2)


def sugerir_matches_por_titulo(
    somente_magis: pd.DataFrame,
    somente_tiny: pd.DataFrame,
    top_n: int = 3,
) -> pd.DataFrame:
    """
    Para cada produto que está SOMENTE no Magis, busca os títulos
    mais similares dentre os que estão SOMENTE no Tiny.

    Parameters
    ----------
    somente_magis : pd.DataFrame
        Registros presentes apenas no Magis (sem match por SKU/EAN).
    somente_tiny : pd.DataFrame
        Registros presentes apenas no Tiny.
    top_n : int
        Quantidade de sugestões por produto Magis.

    Returns
    -------
    pd.DataFrame
        Colunas: sku_magis, titulo_magis, sku_tiny, titulo_tiny,
                 score, classificacao
    """
    limiares = _carregar_limiares()
    limiar_match = limiares.get("match_provavel", 90)
    limiar_revisar = limiares.get("revisar", 80)

    # Preparar dados do Tiny (choices para o rapidfuzz)
    titulos_tiny = somente_tiny[["sku", "titulo"]].dropna(subset=["titulo"])
    if titulos_tiny.empty:
        return pd.DataFrame()

    tiny_titulos_list = titulos_tiny["titulo"].tolist()
    tiny_skus_list = titulos_tiny["sku"].tolist()

    # Preparar dados do Magis (queries)
    magis_com_titulo = somente_magis[["sku", "titulo"]].dropna(subset=["titulo"])
    if magis_com_titulo.empty:
        return pd.DataFrame()

    logger.info(
        "Matching por similaridade: %d produtos Magis × %d produtos Tiny",
        len(magis_com_titulo), len(titulos_tiny),
    )

    resultados = []

    for _, row_m in magis_com_titulo.iterrows():
        titulo_m = row_m["titulo"]
        sku_m = row_m["sku"]

        # process.extract retorna lista de (match, score, index) — vetorizado em C++
        matches = process.extract(
            titulo_m,
            tiny_titulos_list,
            scorer=fuzz.token_sort_ratio,
            limit=top_n,
            score_cutoff=limiar_revisar,
        )

        for titulo_tiny, score, idx in matches:
            resultados.append({
                "sku_magis": sku_m,
                "titulo_magis": titulo_m,
                "sku_tiny": tiny_skus_list[idx],
                "titulo_tiny": titulo_tiny,
                "score": round(score, 2),
            })

    df = pd.DataFrame(resultados)

    if not df.empty:
        df["classificacao"] = df["score"].apply(
            lambda s: "MATCH_PROVAVEL" if s >= limiar_match else "REVISAR"
        )

    return df
