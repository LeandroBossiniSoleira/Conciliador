"""
exportador_tiny.py
Lida com a exportação de rotinas específicas para o Tiny.
"""

import pandas as pd

def gerar_planilha_importacao_tiny(
    df_magis_kits_raw: pd.DataFrame, 
    df_somente_magis: pd.DataFrame, 
    df_tiny_produtos_norm: pd.DataFrame | None = None
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Gera as linhas padronizadas para a planilha de importação de kits Olist/Tiny.
    
    Retorna a planilha gerada (df) e a lista de kits rejeitados com seus motivos.
    """
    rejeitados = []
    importacao_rows = []
    
    if df_magis_kits_raw.empty or df_somente_magis.empty:
        return pd.DataFrame(), rejeitados
        
    skus_somente_magis = set(df_somente_magis['sku_kit'].unique())
    
    # Produtos disponíveis no Tiny
    tiny_skus = set()
    if df_tiny_produtos_norm is not None and not df_tiny_produtos_norm.empty:
        tiny_skus = set(df_tiny_produtos_norm['sku'].astype(str).unique())
    
    # Filtra apenas os kits que foram detectados como exclusivos do magis (ausentes no Tiny)
    df_filtrado = df_magis_kits_raw[df_magis_kits_raw['sku_kit'].isin(skus_somente_magis)]
    
    for sku_kit, gru in df_filtrado.groupby('sku_kit'):
        titulo_kit_raw = gru['titulo_kit'].iloc[0] if 'titulo_kit' in gru.columns else ''
        
        # Validação 1: Quantidade limite de itens
        if len(gru) > 20:
            rejeitados.append({
                'sku_kit': sku_kit,
                'titulo_kit': titulo_kit_raw,
                'motivo': f'Kit excede o limite do Tiny (tem {len(gru)} componentes, máximo 20).'
            })
            continue
            
        # Validação 2: Verificar se SKUs do Kit e Componentes existem no Tiny
        rejeitado_por_ausencia = False
        if df_tiny_produtos_norm is not None and not df_tiny_produtos_norm.empty:
            # 2.a: O SKU do Kit precisa estar cadastrado no Tiny (pode ser cadastro base de produto)
            if str(sku_kit) not in tiny_skus:
                rejeitados.append({
                    'sku_kit': sku_kit,
                    'titulo_kit': titulo_kit_raw,
                    'motivo': f'Produto pai (Kit {sku_kit}) não existe no cadastro de produtos do Olist/Tiny.'
                })
                rejeitado_por_ausencia = True
            
            # 2.b: Todos os SKUs dos componentes precisam estar cadastrados no Tiny
            if not rejeitado_por_ausencia:
                componentes_ausentes = [str(c) for c in gru['sku_componente'].unique() if str(c) not in tiny_skus]
                if componentes_ausentes:
                    lista_ausentes = ", ".join(componentes_ausentes)
                    rejeitados.append({
                        'sku_kit': sku_kit,
                        'titulo_kit': titulo_kit_raw,
                        'motivo': f'Componente(s) ausente(s) no cadastro de produtos do Olist/Tiny: {lista_ausentes}'
                    })
                    rejeitado_por_ausencia = True
                    
        if rejeitado_por_ausencia:
            continue
            
        # Se aprovado, formatar as linhas na estrutura exigida
        for _, componente in gru.iterrows():
            importacao_rows.append({
                'ID kit/fabricado': '',
                'SKU kit/fabricado': sku_kit,
                'Descrição kit/fabricado': titulo_kit_raw,
                'ID componente': '',
                'SKU componente': componente['sku_componente'],
                'Descrição componente': componente['titulo_componente'] if 'titulo_componente' in componente else '',
                'Quantidade componente': componente.get('qtd_componente', 1)
            })

    # Criar o DataFrame com ordem exata de colunas solicitada
    colunas_finais = [
        'ID kit/fabricado', 'SKU kit/fabricado', 'Descrição kit/fabricado',
        'ID componente', 'SKU componente', 'Descrição componente', 'Quantidade componente'
    ]
    
    df_importacao = pd.DataFrame(importacao_rows, columns=colunas_finais)
    
    return df_importacao, rejeitados
