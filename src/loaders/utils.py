import io
import logging
import warnings

import pandas as pd
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def is_empty(valor) -> bool:
    """Verifica se um valor é considerado vazio (None, NaN, ou string em branco)."""
    if valor is None:
        return True
    if isinstance(valor, float) and pd.isna(valor):
        return True
    try:
        if pd.isna(valor):
            return True
    except (TypeError, ValueError):
        pass
    return str(valor).strip() == ""


def _carregar_mapa() -> dict:
    """Lê o mapeamento de colunas do YAML de configuração."""
    with open(CONFIG_DIR / "mapa_campos.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def carregar_generico(arquivos, mapa_key: str, sistema_origem: str) -> pd.DataFrame:
    """
    Lê um ou mais arquivos, concatena, renomeia colunas conforme o mapa YAML
    e marca a origem do registro.

    Parameters
    ----------
    arquivos : str, file-like object, ou list
        Arquivo(s) a carregar.
    mapa_key : str
        Chave no mapa_campos.yaml (ex: 'magis', 'tiny', 'magis_kits', 'tiny_kits').
    sistema_origem : str
        Valor para a coluna 'sistema_origem' (ex: 'MAGIS', 'TINY').

    Returns
    -------
    pd.DataFrame com colunas renomeadas e coluna 'sistema_origem'.
    """
    mapa = _carregar_mapa()
    colunas = mapa.get(mapa_key, {})

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

    df["sistema_origem"] = sistema_origem
    return df

def ler_arquivo_robusto(f) -> pd.DataFrame:
    """
    Tenta ler o arquivo de várias formas diferentes para suportar XLS corrompidos 
    (HTML masquerading as XLS) ou CSVs.
    """
    f.seek(0)
    content = f.read()
    erro_excel = None

    # 1. Excel (XLSX, XLS real)
    # Tenta usar o calamine primeiro (muito mais robusto para arquivos XLS malformados)
    try:
        return pd.read_excel(io.BytesIO(content), dtype=str, engine='calamine')
    except Exception as e:
        erro_excel = f"Calamine: {str(e)}"
        
        # Fallback para o default se calamine não suportar
        try:
            return pd.read_excel(io.BytesIO(content), dtype=str)
        except Exception as e2:
            erro_excel += f" | Nativo: {str(e2)}"

    # 2. HTML (Muitos sistemas exportam HTML puro com extensão .xls)
    try:
        try:
            html_str = content.decode('utf-8')
        except UnicodeDecodeError:
            html_str = content.decode('latin1', errors='replace')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            dfs = pd.read_html(io.StringIO(html_str), decimal=',', thousands='.')

        if dfs:
            df = dfs[0]
            for col in df.columns:
                df[col] = df[col].astype(str)
            logger.info("Arquivo lido como HTML (fallback). Erro original do Excel: %s", erro_excel)
            return df
    except Exception as e_html:
        logger.debug("Falha ao ler como HTML: %s", e_html)

    # 3. CSV Tsv/Ssv
    try:
        df = pd.read_csv(io.BytesIO(content), sep=None, engine='python', dtype=str, encoding_errors='replace')
        logger.info("Arquivo lido como CSV (fallback). Erro original do Excel: %s", erro_excel)
        return df
    except Exception as e_csv:
        logger.debug("Falha ao ler como CSV: %s", e_csv)

    raise ValueError(f"Não foi possível ler o arquivo. Erro original do Excel: {erro_excel}")
