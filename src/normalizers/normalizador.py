"""
normalizador.py
Regras de normalização para unificar os dados do Magis e do Tiny
em um formato padronizado e comparável.
"""

import re
import pandas as pd
import yaml
from pathlib import Path
from unidecode import unidecode
from src.loaders.utils import is_empty


CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _carregar_regras() -> dict:
    """Lê as regras de normalização do YAML."""
    with open(CONFIG_DIR / "regras_normalizacao.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ────────────────────────────────────────────
# Funções auxiliares
# ────────────────────────────────────────────

def limpar_texto(valor) -> str | None:
    """Remove acentos, espaços extras e converte para UPPER."""
    if is_empty(valor):
        return None
    valor = str(valor).strip()
    if valor == "":
        return None
    valor = unidecode(valor)
    valor = valor.upper()
    # Colapsa espaços múltiplos
    valor = re.sub(r"\s+", " ", valor)
    return valor


def limpar_codigo(valor) -> str | None:
    """Remove tudo que não é dígito (pontos, traços, espaços)."""
    if is_empty(valor):
        return None
    valor = re.sub(r"\D", "", str(valor))
    return valor if valor else None


def extrair_digito_origem(valor) -> str | None:
    """
    Extrai o primeiro dígito de um campo de origem.
    Ex.: '0 - Nacional...' → '0'
    """
    if is_empty(valor):
        return None
    match = re.search(r"\d", str(valor))
    return match.group(0) if match else None


def normalizar_status(valor, sistema: str, mapa_status: dict) -> str | None:
    """
    Converte os diferentes valores de status de cada sistema
    para um valor padronizado (ATIVO / INATIVO / EXCLUIDO).
    """
    if is_empty(valor):
        return None
    valor_str = str(valor).strip()
    mapa = mapa_status.get(sistema, {})
    return mapa.get(valor_str, valor_str.upper())


# ────────────────────────────────────────────
# Função principal
# ────────────────────────────────────────────

def normalizar_dataframe(df: pd.DataFrame, sistema: str = "magis") -> pd.DataFrame:
    """
    Aplica todas as regras de normalização ao DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame já carregado por um dos loaders.
    sistema : str
        'magis' ou 'tiny' — usado para saber qual mapa de status usar.

    Returns
    -------
    pd.DataFrame
        DataFrame normalizado.
    """
    regras = _carregar_regras()

    # --- Campos de texto ---
    for campo in regras.get("campos_texto", []):
        if campo in df.columns:
            df[campo] = df[campo].apply(limpar_texto)

    # --- Campos de código ---
    for campo in regras.get("campos_codigo", []):
        if campo in df.columns:
            df[campo] = df[campo].apply(limpar_codigo)

    # --- Origem → primeiro dígito ---
    if "origem" in df.columns:
        df["origem"] = df["origem"].apply(extrair_digito_origem)

    # --- Status normalizado ---
    mapa_status = regras.get("mapa_status", {})
    if "status" in df.columns:
        df["status"] = df["status"].apply(
            lambda v: normalizar_status(v, sistema, mapa_status)
        )

    # --- Preço de custo → float ---
    if "preco_custo" in df.columns:
        df["preco_custo"] = (
            pd.to_numeric(
                df["preco_custo"]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .str.strip(),
                errors="coerce",
            )
            .fillna(0.0)
        )

    # --- Estoque → int ---
    if "estoque" in df.columns:
        df["estoque"] = (
            pd.to_numeric(df["estoque"], errors="coerce").fillna(0).astype(int)
        )

    return df
