"""
validator.py
Analisa um SKU contra o padrão oficial e gera o contrato de saída definido
pelo usuário:

    {
      "sku_original":        str,
      "status":              "correto" | "erro" | "incompleto",
      "tipo_erro":           "estrutural" | "semantico" | None,
      "problemas":           [str, ...],
      "sku_sugerido":        str | None,
      "confianca":           int,   # 0-100
      "precisa_acao_manual": bool,
      "eh_kit":              bool,
    }
"""

from __future__ import annotations

from typing import TypedDict

import pandas as pd

from src.sku.corretor import TERMOS_KIT, sugerir_sku
from src.sku.dicionario import carregar_dicionario, construir_indice_reverso
from src.sku.parser import parsear_sku


class SKUAnalise(TypedDict):
    sku_original: str
    titulo: str
    status: str
    tipo_erro: str | None
    problemas: list[str]
    sku_sugerido: str | None
    confianca: int
    precisa_acao_manual: bool
    eh_kit: bool


LIMIAR_CONFIANCA_MANUAL = 60


def analisar_sku(sku: str, titulo: str | None = None, dic: dict | None = None, indice: dict | None = None) -> SKUAnalise:
    dic = dic or carregar_dicionario()
    indice = indice or construir_indice_reverso(dic)
    titulo = titulo or ""

    parsed = parsear_sku(sku, dic)
    sug = sugerir_sku(titulo, dic, indice)
    sku_sugerido = sug.montar_sku()
    confianca = sug.confianca()

    problemas: list[str] = []
    problemas.extend(parsed.erros_estruturais)
    problemas.extend(parsed.blocos_invalidos)

    # Detecção de kit: título contém "kit" OU SKU começa com KT
    titulo_up = (titulo or "").upper()
    eh_kit = any(t in titulo_up for t in TERMOS_KIT) or (parsed.pp == "KT")

    # Regra: kit MISTO (produtos diferentes, indicado por "+" no título) deve ter PP=KT.
    # Kits de um único produto usam PP específico + QQQQ=NNNU, então não flagar.
    kit_misto = "+" in titulo_up
    if kit_misto and parsed.pp and parsed.pp != "KT":
        problemas.append(f"Kit misto deveria ter PP=KT (recebeu {parsed.pp})")

    # Determina status + tipo_erro
    if parsed.tem_erro_estrutural:
        status = "erro"
        tipo_erro: str | None = "estrutural"
    elif parsed.tem_erro_semantico or (kit_misto and parsed.pp != "KT"):
        status = "erro"
        tipo_erro = "semantico"
    elif not parsed.pp:
        status = "incompleto"
        tipo_erro = None
    else:
        status = "correto"
        tipo_erro = None

    # Se a sugestão não muda nada, zerar para não poluir a UI
    if status == "correto" and sku_sugerido == (sku or "").strip().upper():
        sku_sugerido = None

    precisa_acao_manual = (
        status != "correto"
        and (sku_sugerido is None or confianca < LIMIAR_CONFIANCA_MANUAL)
    )

    return {
        "sku_original": sku or "",
        "titulo": titulo,
        "status": status,
        "tipo_erro": tipo_erro,
        "problemas": problemas,
        "sku_sugerido": sku_sugerido,
        "confianca": confianca,
        "precisa_acao_manual": precisa_acao_manual,
        "eh_kit": eh_kit,
    }


def analisar_dataframe(df: pd.DataFrame, coluna_sku: str = "sku", coluna_titulo: str = "titulo") -> pd.DataFrame:
    """Aplica a análise a um DataFrame inteiro e retorna um DF com as colunas do contrato.

    O DF resultante preserva o índice original para facilitar join posterior.
    """
    dic = carregar_dicionario()
    indice = construir_indice_reverso(dic)

    if coluna_sku not in df.columns:
        raise KeyError(f"Coluna '{coluna_sku}' não encontrada no DataFrame")

    titulos = df[coluna_titulo] if coluna_titulo in df.columns else pd.Series([""] * len(df), index=df.index)

    registros: list[SKUAnalise] = []
    for sku, titulo in zip(df[coluna_sku].astype(str), titulos.fillna("").astype(str)):
        registros.append(analisar_sku(sku, titulo, dic, indice))

    out = pd.DataFrame(registros, index=df.index)
    # Converte lista de problemas em string separada por "; " para UI/export
    out["problemas_txt"] = out["problemas"].apply(lambda xs: "; ".join(xs) if xs else "")
    return out
