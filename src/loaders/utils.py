import io
import logging
import warnings

import pandas as pd

logger = logging.getLogger(__name__)

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
