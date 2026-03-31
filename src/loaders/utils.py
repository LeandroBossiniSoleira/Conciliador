import pandas as pd
import io
import warnings

def ler_arquivo_robusto(f) -> pd.DataFrame:
    """
    Tenta ler o arquivo de várias formas diferentes para suportar XLS corrompidos 
    (HTML masquerading as XLS) ou CSVs.
    """
    f.seek(0)
    content = f.read()
    erro_excel = None

    # 1. Excel (XLSX, XLS real)
    try:
        return pd.read_excel(io.BytesIO(content), dtype=str)
    except Exception as e:
        erro_excel = str(e)

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
            return df
    except Exception:
        pass

    # 3. CSV Tsv/Ssv
    try:
        return pd.read_csv(io.BytesIO(content), sep=None, engine='python', dtype=str, encoding_errors='replace')
    except Exception:
        pass

    raise ValueError(f"Não foi possível ler o arquivo. Erro original do Excel: {erro_excel}")
