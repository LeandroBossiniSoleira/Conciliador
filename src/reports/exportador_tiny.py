"""
exportador_tiny.py
Lida com a exportação de rotinas específicas para o Tiny.
"""

import pandas as pd


# ────────────────────────────────────────────
# Colunas obrigatórias para planilha de correção de tipo de produto
# (Apenas colunas essenciais para evitar efeitos colaterais na importação)
# ────────────────────────────────────────────
import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

def _carregar_mapa_tiny_reverso() -> dict:
    """Lê o mapeamento do Tiny do YAML e inverte (Padronizado -> Original)."""
    try:
        with open(CONFIG_DIR / "mapa_campos.yaml", encoding="utf-8") as f:
            mapa = yaml.safe_load(f)
        mapa_tiny = mapa.get("tiny", {})
        return {v: k for k, v in mapa_tiny.items()}
    except Exception:
        # Fallback de segurança mínimo caso falhe a leitura
        return {
            'sku': 'Código (SKU)',
            'titulo': 'Descrição',
            'status': 'Situação',
            'tipo_produto': 'Tipo do produto',
            'codigo_pai': 'Código do pai'
        }


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


def _montar_linha_correcao(produto_tiny: pd.Series, tipo_esperado: str, mapa_tiny_reverso: dict) -> dict:
    """Monta uma linha para a planilha de correção mantendo TODAS as colunas originais do Tiny,
    mas limpando o conteúdo das que não são essenciais/obrigatórias para evitar sobrescrita."""
    linha = produto_tiny.copy()
    
    # Normaliza o status para o formato aceito pelo Tiny
    status_raw = linha.get('status', '')
    status_map = {'ATIVO': 'Ativo', 'INATIVO': 'Inativo'}
    situacao = status_map.get(str(status_raw).strip().upper(), str(status_raw) if pd.notna(status_raw) else 'Ativo')

    # Limpa o codigo_pai
    codigo_pai = linha.get('codigo_pai', '')
    if pd.isna(codigo_pai):
        codigo_pai = ''
        
    linha['status'] = situacao
    linha['tipo_produto'] = tipo_esperado
    linha['codigo_pai'] = codigo_pai
    
    # Reverte os nomes das colunas padronizadas para as originais
    linha_revertida = linha.rename(mapa_tiny_reverso)
    
    linha_dict = linha_revertida.to_dict()
    
    # Lista de colunas originais obrigatórias / essenciais para a atualização não destrutiva
    COLUNAS_MANTIDAS_LOWER = {
        'id',
        'código (sku)',
        'descrição',
        'situação',
        'tipo do produto',
        'código do pai',
        'sob encomenda'
    }
    
    # Limpar qualquer coluna que não esteja na lista de mantidas (preservando o layout)
    for col in linha_dict:
        if str(col).strip().lower() not in COLUNAS_MANTIDAS_LOWER:
            linha_dict[col] = ''
            
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
        
    mapa_tiny_reverso = _carregar_mapa_tiny_reverso()

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
            correcoes.append(_montar_linha_correcao(produto, tipo_esperado, mapa_tiny_reverso))

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
