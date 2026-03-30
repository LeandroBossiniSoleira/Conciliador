"""
fiscal_validator.py
Valida campos fiscais obrigatórios (NCM, Origem, CEST, ANP).
"""

import pandas as pd
import yaml
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _carregar_regras() -> dict:
    with open(CONFIG_DIR / "regras_normalizacao.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validar_registro(row: pd.Series, campos_obrigatorios: list[str]) -> list[str]:
    """
    Recebe uma linha do DataFrame e retorna uma lista de erros fiscais.

    Ex.: ['SEM_NCM', 'SEM_ORIGEM']
    """
    erros: list[str] = []
    for campo in campos_obrigatorios:
        valor = row.get(campo)
        if pd.isna(valor) or valor is None or str(valor).strip() == "":
            erros.append(f"SEM_{campo.upper()}")
    return erros


def validar_fiscal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona a coluna 'erros_fiscais' ao DataFrame,
    listando os campos obrigatórios ausentes em cada registro.

    Returns
    -------
    pd.DataFrame
        DataFrame original com a coluna extra 'erros_fiscais'.
    """
    regras = _carregar_regras()
    campos = regras.get("validacao_fiscal", {}).get("obrigatorios", ["ncm", "origem"])

    df["erros_fiscais"] = df.apply(
        lambda row: validar_registro(row, campos), axis=1
    )
    df["tem_erro_fiscal"] = df["erros_fiscais"].apply(lambda e: len(e) > 0)

    return df


def filtrar_com_erros(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna apenas os registros que possuem pelo menos um erro fiscal."""
    if "tem_erro_fiscal" not in df.columns:
        df = validar_fiscal(df)
    return df[df["tem_erro_fiscal"]].copy()
