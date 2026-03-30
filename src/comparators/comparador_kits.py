"""
comparador_kits.py
Orquestra a comparação de Kits entre Magis 5 e Olist Tiny.
"""

import pandas as pd

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
        df_magis['qtd_componente'] = pd.to_numeric(df_magis['qtd_componente'], errors='coerce').fillna(1)
        # Sort components to make comparison stable
        df_magis_grouped = df_magis.sort_values(by=['sku_kit', 'sku_componente']).groupby('sku_kit').apply(
            lambda x: pd.Series({
                'componentes': tuple(zip(x['sku_componente'].astype(str), x['qtd_componente'])),
                'titulo_kit': x['titulo_kit'].iloc[0] if 'titulo_kit' in x.columns else ''
            }),
            include_groups=False
        ).reset_index()
    else:
        df_magis_grouped = pd.DataFrame(columns=['sku_kit', 'componentes', 'titulo_kit'])

    # Prepare tiny
    if not df_tiny.empty:
        df_tiny['qtd_componente'] = pd.to_numeric(df_tiny['qtd_componente'], errors='coerce').fillna(1)
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
    somente_tiny = merged[merged['_merge'] == 'right_only'].copy()
    
    nos_dois = merged[merged['_merge'] == 'both'].copy()
    
    # Identify divergent kits
    divergentes = []
    if not nos_dois.empty:
        nos_dois['componentes_iguais'] = nos_dois.apply(
            lambda row: set(row['componentes_magis']) == set(row['componentes_tiny']),
            axis=1
        )
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
    def format_components(comp_tuple):
        if not comp_tuple or pd.isna(comp_tuple): return ""
        if isinstance(comp_tuple, str): return comp_tuple
        return "\\n".join([f"{sku} ({qtd}x)" for sku, qtd in comp_tuple])
        
    somente_magis['componentes_formatados'] = somente_magis['componentes_magis'].apply(format_components)
    somente_tiny['componentes_formatados'] = somente_tiny['componentes_tiny'].apply(format_components)
    
    # Select cols
    cols_magis = ['sku_kit', 'titulo_kit_magis', 'componentes_formatados']
    cols_tiny = ['sku_kit', 'titulo_kit_tiny', 'componentes_formatados']
    
    df_somente_magis = somente_magis[[c for c in cols_magis if c in somente_magis.columns]]
    df_somente_tiny = somente_tiny[[c for c in cols_tiny if c in somente_tiny.columns]]
    
    df_divergentes = pd.DataFrame(divergentes) if divergentes else pd.DataFrame(columns=[
        'sku_kit', 'titulo_kit_magis', 'titulo_kit_tiny', 'componentes_magis', 'componentes_tiny'
    ])
    
    # Rename columns for presentation
    df_somente_magis = df_somente_magis.rename(columns={'titulo_kit_magis': 'titulo_kit', 'componentes_formatados': 'componentes (SKU e Qtd)'})
    df_somente_tiny = df_somente_tiny.rename(columns={'titulo_kit_tiny': 'titulo_kit', 'componentes_formatados': 'componentes (SKU e Qtd)'})
    
    return {
        "somente_magis": df_somente_magis,
        "somente_tiny": df_somente_tiny,
        "divergentes": df_divergentes
    }
