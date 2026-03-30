"""
similaridade_matcher.py
Usa rapidfuzz para sugerir correspondência entre títulos de produtos
que não bateram por SKU nem EAN.
"""

import pandas as pd
import yaml
from pathlib import Path
from rapidfuzz import fuzz


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

    resultados = []

    titulos_tiny = somente_tiny[["sku", "titulo"]].dropna(subset=["titulo"])

    for _, row_m in somente_magis.iterrows():
        titulo_m = row_m.get("titulo")
        sku_m = row_m.get("sku")

        if not titulo_m:
            continue

        scores = []
        for _, row_t in titulos_tiny.iterrows():
            score = similaridade(titulo_m, row_t["titulo"])
            if score >= limiar_revisar:
                scores.append(
                    {
                        "sku_magis": sku_m,
                        "titulo_magis": titulo_m,
                        "sku_tiny": row_t["sku"],
                        "titulo_tiny": row_t["titulo"],
                        "score": round(score, 2),
                    }
                )

        # Ordena e pega os top_n
        scores.sort(key=lambda x: x["score"], reverse=True)
        resultados.extend(scores[:top_n])

    df = pd.DataFrame(resultados)

    if not df.empty:
        df["classificacao"] = df["score"].apply(
            lambda s: (
                "MATCH_PROVAVEL" if s >= limiar_match
                else "REVISAR"
            )
        )

    return df
