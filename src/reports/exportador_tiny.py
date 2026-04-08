"""
exportador_tiny.py
Lida com a exportação de rotinas específicas para o Tiny.
"""

import pandas as pd


# ────────────────────────────────────────────
# Layout exato de 64 colunas da exportação/importação de produtos do Tiny.
# Extraído diretamente da planilha exportada pelo Tiny ERP (PlanilhaExemplo.xls).
# ────────────────────────────────────────────

LAYOUT_IMPORTACAO_TINY = [
    "ID", "Código (SKU)", "Descrição", "Unidade", "Classificação fiscal",
    "Origem", "Preço", "Valor IPI fixo", "Observações", "Situação",
    "Estoque", "Preço de custo", "Cód do Fornecedor", "Fornecedor",
    "Localização", "Estoque máximo", "Estoque mínimo", "Peso líquido (Kg)",
    "Peso bruto (Kg)", "GTIN/EAN", "GTIN/EAN tributável",
    "Descrição complementar", "CEST", "Código de Enquadramento IPI",
    "Formato embalagem", "Largura embalagem", "Altura embalagem",
    "Comprimento embalagem", "Diâmetro embalagem", "Tipo do produto",
    "URL imagem 1", "URL imagem 2", "URL imagem 3", "URL imagem 4",
    "URL imagem 5", "URL imagem 6", "Categoria", "Código do pai",
    "Variações", "Marca", "Garantia", "Sob encomenda", "Preço promocional",
    "URL imagem externa 1", "URL imagem externa 2", "URL imagem externa 3",
    "URL imagem externa 4", "URL imagem externa 5", "URL imagem externa 6",
    "Link do vídeo", "Título SEO", "Descrição SEO", "Palavras chave SEO",
    "Slug", "Dias para preparação", "Controlar lotes", "Unidade por caixa",
    "URL imagem externa 7", "URL imagem externa 8", "URL imagem externa 9",
    "URL imagem externa 10", "Markup", "Permitir inclusão nas vendas",
    "EX TIPI"
]


def _buscar_produto_tiny(sku: str, df_tiny: pd.DataFrame) -> pd.Series | None:
    """Localiza um produto no DataFrame normalizado do Tiny pelo SKU."""
    match = df_tiny[df_tiny['sku'].astype(str) == str(sku)]
    if match.empty:
        return None
    return match.iloc[0]


def _tipo_correto(produto_tiny: pd.Series) -> str:
    """
    Determina o tipo correto de um produto:
      - Se 'codigo_pai' está vazio → é o PAI agrupador → tipo 'V'
      - Se 'codigo_pai' está preenchido → é filho → tipo 'K'
    """
    codigo_pai = produto_tiny.get('codigo_pai', None)
    if pd.isna(codigo_pai) or str(codigo_pai).strip() == '':
        return 'V'
    return 'K'


def _montar_linha_correcao(produto_tiny: pd.Series, tipo_esperado: str) -> dict:
    """Monta uma linha para a planilha de correção mantendo estritamente 
    o layout de 64 colunas da importação de produtos do Tiny, populando 
    apenas as informações essenciais para a correção."""
    
    # Inicializa a linha com todas as 64 colunas vazias
    linha_dict = {col: '' for col in LAYOUT_IMPORTACAO_TINY}
    
    # Normaliza o status para o formato aceito pelo Tiny
    status_raw = produto_tiny.get('status', '')
    status_map = {'ATIVO': 'Ativo', 'INATIVO': 'Inativo'}
    situacao = status_map.get(str(status_raw).strip().upper(), str(status_raw) if pd.notna(status_raw) else 'Ativo')

    # Limpa o codigo_pai
    codigo_pai = produto_tiny.get('codigo_pai', '')
    if pd.isna(codigo_pai):
        codigo_pai = ''
        
    # Preenche apenas campos necessários (nomes conforme layout real do Tiny)
    id_produto = produto_tiny.get('id', '')
    if pd.isna(id_produto):
        id_produto = ''
        
    linha_dict['ID'] = id_produto
    linha_dict['Código (SKU)'] = produto_tiny.get('sku', '')
    linha_dict['Descrição'] = produto_tiny.get('titulo', '')
    linha_dict['Situação'] = situacao
    linha_dict['Preço'] = produto_tiny.get('preco', '') if pd.notna(produto_tiny.get('preco', '')) else ''
    linha_dict['Variações'] = produto_tiny.get('variacoes', '') if pd.notna(produto_tiny.get('variacoes', '')) else ''
    linha_dict['Tipo do produto'] = tipo_esperado
    linha_dict['Código do pai'] = codigo_pai
    
    # Conserva regra para campo "sob encomenda" se houver
    sob_encomenda = produto_tiny.get('sob_encomenda', '')
    if pd.notna(sob_encomenda):
        linha_dict['Sob encomenda'] = sob_encomenda
            
    return linha_dict


def verificar_tipos_produto(
    skus_para_verificar: set[str],
    df_tiny_produtos_norm: pd.DataFrame | None,
    tipo_esperado: str = 'K',
) -> tuple[list[dict], list[dict]]:
    """
    Verifica se os SKUs de Kits possuem o 'Tipo do produto' correto no Tiny.
    
    Apenas os SKUs dos Kits (coluna SKU KIT) devem ser verificados.
    Componentes são produtos simples e não precisam ser do tipo K.

    Retorna
    -------
    alertas : list[dict]
        Lista de alertas descrevendo os produtos com tipo incorreto.
    correcoes : list[dict]
        Linhas formatadas para a planilha de correção.
    """
    alertas: list[dict] = []
    correcoes: list[dict] = []

    if df_tiny_produtos_norm is None or df_tiny_produtos_norm.empty:
        return alertas, correcoes

    for sku in skus_para_verificar:
        produto = _buscar_produto_tiny(sku, df_tiny_produtos_norm)
        if produto is None:
            continue  # Produto não existe no Tiny — validado em outra etapa

        tipo_atual = str(produto.get('tipo_produto', '')).strip().upper()

        if tipo_atual != tipo_esperado:
            alertas.append({
                'sku': sku,
                'titulo': produto.get('titulo', ''),
                'tipo_atual': tipo_atual if tipo_atual else '(vazio)',
                'tipo_esperado': tipo_esperado,
            })
            correcoes.append(_montar_linha_correcao(produto, tipo_esperado))

    return alertas, correcoes


def gerar_planilha_importacao_tiny(
    df_magis_kits_raw: pd.DataFrame, 
    df_somente_magis: pd.DataFrame, 
    df_tiny_produtos_norm: pd.DataFrame | None = None
) -> tuple[pd.DataFrame, list[dict], pd.DataFrame, list[dict]]:
    """
    Gera as linhas padronizadas para a planilha de importação de kits Olist/Tiny.
    
    Retorna
    -------
    df_importacao : pd.DataFrame
        Planilha formatada para importação de kits.
    rejeitados : list[dict]
        Kits rejeitados com seus motivos.
    df_correcao_tipos : pd.DataFrame
        Planilha de correção de tipo de produto para importação no Tiny.
    alertas_tipo : list[dict]
        Alertas descritivos sobre produtos com tipo incorreto.
    """
    rejeitados = []
    importacao_rows = []
    
    if df_magis_kits_raw.empty or df_somente_magis.empty:
        return pd.DataFrame(), rejeitados, pd.DataFrame(), []
        
    skus_somente_magis = set(df_somente_magis['sku_kit'].unique())
    
    # Produtos disponíveis no Tiny
    tiny_skus = set()
    if df_tiny_produtos_norm is not None and not df_tiny_produtos_norm.empty:
        tiny_skus = set(df_tiny_produtos_norm['sku'].astype(str).unique())
    
    # ────────────────────────────────────────────
    # VALIDAÇÃO DE TIPO: Verificar apenas os SKUs de KIT (coluna A)
    # Componentes (coluna C) são produtos simples e NÃO devem ser alterados.
    # ────────────────────────────────────────────
    df_filtrado = df_magis_kits_raw[df_magis_kits_raw['sku_kit'].isin(skus_somente_magis)]
    
    # Coletar apenas os SKUs de KIT (não os componentes)
    skus_kits_unicos: set[str] = set(df_filtrado['sku_kit'].astype(str).unique())
    
    alertas_tipo, correcoes = verificar_tipos_produto(skus_kits_unicos, df_tiny_produtos_norm, tipo_esperado='K')
    
    # Montar o DataFrame de correção (agora com todas as colunas originais do Tiny)
    df_correcao_tipos = pd.DataFrame(correcoes) if correcoes else pd.DataFrame()
    
    # SKUs com tipo errado (que precisam correção antes de importar o kit)
    skus_tipo_errado = {a['sku'] for a in alertas_tipo}
    
    # ────────────────────────────────────────────
    # Geração da planilha de importação de Kits
    # ────────────────────────────────────────────
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
        
        # Validação 3: Verificar se algum SKU envolvido neste kit tem tipo errado
        skus_deste_kit = {str(sku_kit)} | {str(c) for c in gru['sku_componente'].unique()}
        skus_com_tipo_errado_neste_kit = skus_deste_kit & skus_tipo_errado
        
        if skus_com_tipo_errado_neste_kit:
            lista_errados = ", ".join(sorted(skus_com_tipo_errado_neste_kit))
            rejeitados.append({
                'sku_kit': sku_kit,
                'titulo_kit': titulo_kit_raw,
                'motivo': (
                    f'Produto(s) com Tipo incorreto no Tiny (não é Kit): {lista_errados}. '
                    f'Baixe a "Planilha de Correção de Tipos" e importe-a no Tiny antes de importar os Kits.'
                )
            })
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
    
    return df_importacao, rejeitados, df_correcao_tipos, alertas_tipo
