"""
comparador_kits.py
Orquestra a comparação de Kits entre Magis 5 e Olist Tiny.
"""

import logging
from pathlib import Path

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _carregar_regras() -> dict:
    with open(CONFIG_DIR / "regras_normalizacao.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


_REGRAS = _carregar_regras()
_STATUSES_INATIVOS = set(_REGRAS.get("statuses_inativos", ["INATIVO", "EXCLUIDO"]))

def comparar_kits(df_magis: pd.DataFrame, df_tiny: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Compara os kits entre Magis e Tiny.
    
    Retorna um dicionário com:
    - somentes_magis: Kits exclusivos do Magis
    - somentes_tiny: Kits exclusivos do Tiny
    - divergentes: Kits presentes em ambos, mas com componentes ou quantidades diferentes
    """
    if df_magis.empty and df_tiny.empty:
        return {
            "somente_magis": pd.DataFrame(),
            "somente_tiny": pd.DataFrame(),
            "divergentes": pd.DataFrame()
        }

    # Prepare magis
    if not df_magis.empty:
        qtd_raw = df_magis['qtd_componente']
        df_magis['qtd_componente'] = pd.to_numeric(qtd_raw, errors='coerce')
        invalidos = df_magis['qtd_componente'].isna() & qtd_raw.notna() & (qtd_raw.astype(str).str.strip() != "")
        if invalidos.any():
            logger.warning("comparar_kits (Magis): %d qtd_componente inválida(s) convertida(s) para 1.", invalidos.sum())
        df_magis['qtd_componente'] = df_magis['qtd_componente'].fillna(1)
        # Sort components to make comparison stable
        df_magis_grouped = df_magis.sort_values(by=['sku_kit', 'sku_componente']).groupby('sku_kit').apply(
            lambda x: pd.Series({
                'componentes': tuple(zip(x['sku_componente'].astype(str), x['qtd_componente'])),
                'titulo_kit': x['titulo_kit'].iloc[0] if 'titulo_kit' in x.columns else '',
                'status_kit': x['status_kit'].iloc[0] if 'status_kit' in x.columns else 'DESCONHECIDO',
            }),
            include_groups=False
        ).reset_index()
    else:
        df_magis_grouped = pd.DataFrame(columns=['sku_kit', 'componentes', 'titulo_kit'])

    # Prepare tiny
    if not df_tiny.empty:
        qtd_raw = df_tiny['qtd_componente']
        df_tiny['qtd_componente'] = pd.to_numeric(qtd_raw, errors='coerce')
        invalidos = df_tiny['qtd_componente'].isna() & qtd_raw.notna() & (qtd_raw.astype(str).str.strip() != "")
        if invalidos.any():
            logger.warning("comparar_kits (Tiny): %d qtd_componente inválida(s) convertida(s) para 1.", invalidos.sum())
        df_tiny['qtd_componente'] = df_tiny['qtd_componente'].fillna(1)
        df_tiny_grouped = df_tiny.sort_values(by=['sku_kit', 'sku_componente']).groupby('sku_kit').apply(
            lambda x: pd.Series({
                'componentes': tuple(zip(x['sku_componente'].astype(str), x['qtd_componente'])),
                'titulo_kit': x['titulo_kit'].iloc[0] if 'titulo_kit' in x.columns else ''
            }),
            include_groups=False
        ).reset_index()
    else:
        df_tiny_grouped = pd.DataFrame(columns=['sku_kit', 'componentes', 'titulo_kit'])

    # Merge on sku_kit
    merged = pd.merge(
        df_magis_grouped, 
        df_tiny_grouped, 
        on='sku_kit', 
        how='outer', 
        suffixes=('_magis', '_tiny'), 
        indicator=True
    )

    somente_magis = merged[merged['_merge'] == 'left_only'].copy()
    somente_tiny  = merged[merged['_merge'] == 'right_only'].copy()

    # Separar kits inativos/excluídos do Magis — não são problemas de migração
    somente_magis_inativos     = pd.DataFrame()
    somente_magis_desconhecido = pd.DataFrame()
    if 'status_kit' in somente_magis.columns:
        status_upper = somente_magis['status_kit'].fillna('').str.upper()
        somente_magis_inativos     = somente_magis[status_upper.isin(_STATUSES_INATIVOS)].copy()
        somente_magis_desconhecido = somente_magis[status_upper == 'DESCONHECIDO'].copy()
        somente_magis              = somente_magis[status_upper == 'ATIVO'].copy()

    nos_dois = merged[merged['_merge'] == 'both'].copy()
    
    # Identify divergent kits
    divergentes = []
    nos_dois_iguais = pd.DataFrame()
    if not nos_dois.empty:
        nos_dois['componentes_iguais'] = nos_dois.apply(
            lambda row: set(row['componentes_magis']) == set(row['componentes_tiny']),
            axis=1
        )
        nos_dois_iguais = nos_dois[nos_dois['componentes_iguais']][['sku_kit', 'titulo_kit_magis']].copy()
        nos_dois_iguais = nos_dois_iguais.rename(columns={'titulo_kit_magis': 'titulo_kit'})
        divergentes_df = nos_dois[~nos_dois['componentes_iguais']].copy()
        
        # Flatten the divergentes to show rows nicely in UI
        for _, row in divergentes_df.iterrows():
            sku_kit = row['sku_kit']
            comp_magis = row['componentes_magis']
            comp_tiny = row['componentes_tiny']
            
            # Format components as strings for display
            comp_magis_str = "\\n".join([f"{sku} ({qtd}x)" for sku, qtd in comp_magis])
            comp_tiny_str = "\\n".join([f"{sku} ({qtd}x)" for sku, qtd in comp_tiny])
            
            divergentes.append({
                'sku_kit': sku_kit,
                'titulo_kit_magis': row['titulo_kit_magis'],
                'titulo_kit_tiny': row['titulo_kit_tiny'],
                'componentes_magis': comp_magis_str,
                'componentes_tiny': comp_tiny_str
            })

    # Prepare final display DataFrames for only Magis / Tiny
    def format_components(comp_tuple):  # noqa: E301
        if not comp_tuple or pd.isna(comp_tuple): return ""
        if isinstance(comp_tuple, str): return comp_tuple
        return "\\n".join([f"{sku} ({qtd}x)" for sku, qtd in comp_tuple])
        
    somente_magis['componentes_formatados'] = somente_magis['componentes_magis'].apply(format_components)
    somente_tiny['componentes_formatados'] = somente_tiny['componentes_tiny'].apply(format_components)
    
    # Select cols
    # 'status_kit' existe apenas no lado Magis, então o merge não aplica sufixo a ele.
    cols_magis = ['sku_kit', 'status_kit', 'titulo_kit_magis', 'componentes_formatados']
    cols_tiny = ['sku_kit', 'titulo_kit_tiny', 'componentes_formatados']

    df_somente_magis = somente_magis[[c for c in cols_magis if c in somente_magis.columns]]
    df_somente_tiny = somente_tiny[[c for c in cols_tiny if c in somente_tiny.columns]]

    df_divergentes = pd.DataFrame(divergentes) if divergentes else pd.DataFrame(columns=[
        'sku_kit', 'titulo_kit_magis', 'titulo_kit_tiny', 'componentes_magis', 'componentes_tiny'
    ])

    # Rename columns for presentation
    df_somente_magis = df_somente_magis.rename(columns={
        'titulo_kit_magis': 'titulo_kit',
        'componentes_formatados': 'componentes (SKU e Qtd)',
    })
    df_somente_tiny = df_somente_tiny.rename(columns={'titulo_kit_tiny': 'titulo_kit', 'componentes_formatados': 'componentes (SKU e Qtd)'})
    
    # Formatar colunas mínimas dos inativos/desconhecidos para display
    def _fmt_subset(df_sub: pd.DataFrame) -> pd.DataFrame:
        if df_sub.empty:
            return pd.DataFrame(columns=['sku_kit', 'status_kit', 'titulo_kit'])
        cols = [c for c in ['sku_kit', 'status_kit', 'titulo_kit_magis'] if c in df_sub.columns]
        out = df_sub[cols].copy()
        if 'titulo_kit_magis' in out.columns:
            out = out.rename(columns={'titulo_kit_magis': 'titulo_kit'})
        return out

    return {
        "somente_magis":             df_somente_magis,
        "somente_magis_inativos":    _fmt_subset(somente_magis_inativos),
        "somente_magis_desconhecido": _fmt_subset(somente_magis_desconhecido),
        "somente_tiny":              df_somente_tiny,
        "divergentes":               df_divergentes,
        "nos_dois":                  nos_dois_iguais,
    }
