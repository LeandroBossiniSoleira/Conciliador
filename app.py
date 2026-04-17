import logging

import streamlit as st
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuração da página
st.set_page_config(
    page_title="Comparador Magis × Tiny",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Adiciona o diretório raiz ao sys.path para importar os módulos
import sys
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.loaders.magis_loader import carregar_magis
from src.loaders.tiny_loader import carregar_tiny
from src.loaders.kits_loader import carregar_kits_magis, carregar_kits_tiny, enriquecer_status_kits
from src.normalizers.normalizador import normalizar_dataframe
from src.comparators.comparador_produtos import executar_comparacao
from src.comparators.comparador_kits import comparar_kits
from src.reports.gerar_relatorios import gerar_excel
from src.reports.exportador_tiny import (
    gerar_planilha_importacao_tiny,
    gerar_planilha_importacao_produtos_tiny,
    gerar_planilha_importacao_kits_divergentes,
)
from src.ui.estilos import CSS_GLOBAL
from src.ui.componentes import (
    exibir_metricas_4_colunas,
    exibir_painel_saude,
    converter_dataframe,
    montar_df_erros,
)

# Aplica estilos globais
st.markdown(CSS_GLOBAL, unsafe_allow_html=True)


def _calcular_kpis_produtos(resultados: dict) -> dict:
    nos_dois      = len(resultados.get('presente_nos_dois', []))
    s_magis       = len(resultados.get('somente_magis', []))
    s_tiny        = len(resultados.get('somente_tiny', []))
    div_fiscal    = len(resultados.get('divergencias_fiscais', []))
    dup_sku_m     = len(resultados.get('duplicidades_sku_magis', []))
    dup_sku_t     = len(resultados.get('duplicidades_sku_tiny', []))
    dup_ean_m     = len(resultados.get('duplicidades_ean_magis', []))
    dup_ean_t     = len(resultados.get('duplicidades_ean_tiny', []))

    total_magis   = nos_dois + s_magis
    pct           = round(nos_dois / total_magis * 100) if total_magis > 0 else 0
    erros         = div_fiscal + dup_sku_m + dup_sku_t + dup_ean_m + dup_ean_t

    return {
        'pct': pct, 'nos_dois': nos_dois, 'total_magis': total_magis,
        'acoes_pendentes': s_magis + s_tiny, 'erros_criticos': erros,
        's_magis': s_magis, 's_tiny': s_tiny,
        'div_fiscal': div_fiscal,
        'dup_sku_m': dup_sku_m, 'dup_sku_t': dup_sku_t,
        'dup_ean_m': dup_ean_m, 'dup_ean_t': dup_ean_t,
    }


def _calcular_kpis_kits(resultados: dict) -> dict:
    nos_dois    = len(resultados.get('kits_nos_dois', []))
    s_magis     = len(resultados.get('kits_somente_magis', []))
    s_tiny      = len(resultados.get('kits_somente_tiny', []))
    divergentes = len(resultados.get('kits_divergentes', []))

    total_magis = nos_dois + s_magis + divergentes
    pct         = round(nos_dois / total_magis * 100) if total_magis > 0 else 0

    return {
        'pct': pct, 'nos_dois': nos_dois, 'total_magis': total_magis,
        'acoes_pendentes': s_magis + s_tiny, 'erros_criticos': divergentes,
        's_magis': s_magis, 's_tiny': s_tiny, 'divergentes': divergentes,
    }


def exibir_metricas_produtos(resultados: dict[str, pd.DataFrame]):
    """Exibe cards de métricas para Produtos."""
    exibir_metricas_4_colunas("📊 Visão Geral de Produtos", [
        (len(resultados.get('presente_nos_dois', [])), "✅ Sincronizados (OK)", "nos-dois"),
        (len(resultados.get('somente_magis', [])), "→ Importar no Tiny", "magis"),
        (len(resultados.get('somente_tiny', [])), "⚠️ Revisar no Tiny", "tiny"),
        (len(resultados.get('divergencias_fiscais', [])), "✕ Divergência Fiscal", "divergente"),
    ])

    # Nota sobre inativos filtrados
    ignorados_magis = len(resultados.get('somente_magis_inativos', []))
    ignorados_tiny  = len(resultados.get('somente_tiny_inativos', []))
    total_ignorados = ignorados_magis + ignorados_tiny
    if total_ignorados > 0:
        partes = []
        if ignorados_magis:
            partes.append(f"{ignorados_magis} no Magis")
        if ignorados_tiny:
            partes.append(f"{ignorados_tiny} no Tiny")
        st.caption(f"ℹ️ {total_ignorados} produto(s) inativo(s) ignorado(s) nesta análise ({', '.join(partes)}).")

def exibir_metricas_kits(resultados: dict[str, pd.DataFrame]):
    """Exibe cards de métricas para Kits."""
    exibir_metricas_4_colunas("📦 Visão Geral de Kits", [
        (len(resultados.get('kits_nos_dois', [])), "✅ Sincronizados (OK)", "nos-dois"),
        (len(resultados.get('kits_somente_magis', [])), "→ Importar no Tiny", "magis"),
        (len(resultados.get('kits_somente_tiny', [])), "⚠️ Revisar no Tiny", "tiny"),
        (len(resultados.get('kits_divergentes', [])), "✕ Composição Divergente", "divergente"),
    ])

    # Nota sobre inativos/desconhecidos filtrados
    ignorados = len(resultados.get('kits_somente_magis_inativos', []))
    desconhecidos = len(resultados.get('kits_somente_magis_desconhecido', []))
    partes = []
    if ignorados:
        partes.append(f"{ignorados} inativo(s)")
    if desconhecidos:
        partes.append(f"{desconhecidos} com status desconhecido")
    if partes:
        st.caption(
            f"ℹ️ {sum([ignorados, desconhecidos])} kit(s) do Magis ignorado(s) nesta análise "
            f"({', '.join(partes)}). Status desconhecido ocorre quando a planilha de produtos não foi carregada."
        )


def _renderizar_aba_produtos(resultados: dict, formato_download: str):
    """Renderiza a aba de análise de Produtos (KPIs, métricas e 5 sub-tabs)."""
    kpis_p = _calcular_kpis_produtos(resultados)
    exibir_painel_saude(kpis_p, "Produtos")
    exibir_metricas_produtos(resultados)

    st.markdown("#### 📑 Detalhamento dos Produtos")

    n_div   = kpis_p['div_fiscal']
    n_dup   = kpis_p['dup_sku_m'] + kpis_p['dup_sku_t'] + kpis_p['dup_ean_m'] + kpis_p['dup_ean_t']
    n_erros = n_div + n_dup
    n_imp   = kpis_p['s_magis']
    n_rev   = kpis_p['s_tiny']
    n_match = len(resultados.get('sugestao_match_titulo', []))
    n_ok    = kpis_p['nos_dois']

    tabs = st.tabs([
        f"✕ Erros Críticos ({n_erros})",
        f"→ Importar no Tiny ({n_imp})",
        f"⚠️ Revisar no Tiny ({n_rev})",
        f"~ Sugestões de Match ({n_match})",
        f"✅ Sincronizados ({n_ok})",
    ])

    # TAB 0 — Erros Críticos (Divergências Fiscais + Duplicidades)
    with tabs[0]:
        dup_sku_m = resultados.get("duplicidades_sku_magis", pd.DataFrame())
        dup_ean_m = resultados.get("duplicidades_ean_magis", pd.DataFrame())
        dup_sku_t = resultados.get("duplicidades_sku_tiny", pd.DataFrame())
        dup_ean_t = resultados.get("duplicidades_ean_tiny", pd.DataFrame())
        df_div    = resultados.get("divergencias_fiscais", pd.DataFrame())
        total_dup = len(dup_sku_m) + len(dup_ean_m) + len(dup_sku_t) + len(dup_ean_t)

        if n_erros == 0:
            st.success("Nenhum erro crítico encontrado. Seu catálogo está pronto para sincronização.")
        else:
            col_msg, col_btn = st.columns([3, 1])
            with col_msg:
                st.error(
                    f"**{n_erros} erro(s) crítico(s) encontrado(s)** — corrija antes de sincronizar. "
                    f"{n_div} divergência(s) fiscal(is) · {total_dup} duplicidade(s)."
                )
            with col_btn:
                df_erros = montar_df_erros(resultados)
                if not df_erros.empty:
                    data_err, mime_err, ext_err = converter_dataframe(df_erros, formato_download, "Erros Críticos")
                    st.download_button(
                        label=f"📋 Exportar erros ({formato_download})",
                        data=data_err,
                        file_name=f"Erros_Criticos_Produtos{ext_err}",
                        mime=mime_err,
                        use_container_width=True,
                    )

        # — Divergências Fiscais —
        st.markdown("##### Divergências Fiscais entre sistemas")
        if df_div.empty:
            st.success("Nenhuma divergência fiscal entre Magis e Tiny.")
        else:
            st.caption(
                f"{len(df_div)} campo(s) divergente(s) (NCM, CEST, Origem, EAN tributável). "
                "Produtos com dados fiscais diferentes podem gerar rejeição de NF."
            )
            st.dataframe(df_div, use_container_width=True)

        st.markdown("---")

        # — Duplicidades —
        st.markdown("##### Duplicidades de SKU / EAN")
        if total_dup == 0:
            st.success("Nenhuma duplicidade de SKU ou EAN encontrada.")
        else:
            st.caption(
                f"{total_dup} registro(s) duplicado(s). "
                "Produtos com o mesmo SKU ou EAN causarão falha na importação."
            )
            colA, colB = st.columns(2)
            with colA:
                st.markdown("**Magis 5**")
                if not dup_sku_m.empty:
                    st.caption(f"SKU duplicado: {len(dup_sku_m)} registro(s)")
                    st.dataframe(dup_sku_m, use_container_width=True)
                if not dup_ean_m.empty:
                    st.caption(f"EAN duplicado: {len(dup_ean_m)} registro(s)")
                    st.dataframe(dup_ean_m, use_container_width=True)
                if dup_sku_m.empty and dup_ean_m.empty:
                    st.success("Sem duplicidades.")
            with colB:
                st.markdown("**Olist Tiny**")
                if not dup_sku_t.empty:
                    st.caption(f"SKU duplicado: {len(dup_sku_t)} registro(s)")
                    st.dataframe(dup_sku_t, use_container_width=True)
                if not dup_ean_t.empty:
                    st.caption(f"EAN duplicado: {len(dup_ean_t)} registro(s)")
                    st.dataframe(dup_ean_t, use_container_width=True)
                if dup_sku_t.empty and dup_ean_t.empty:
                    st.success("Sem duplicidades.")

    # TAB 1 — Importar no Tiny
    with tabs[1]:
        df = resultados.get("somente_magis", pd.DataFrame())
        if df.empty:
            st.success("Todos os produtos ativos do Magis já estão no Tiny.")
        else:
            col_msg, col_btn = st.columns([3, 1])
            with col_msg:
                st.info(f"**{len(df)} produto(s) ativo(s) no Magis** que ainda não existem no Tiny.")
            with col_btn:
                magis_norm_ref = resultados.get("magis_norm", pd.DataFrame())
                if not magis_norm_ref.empty and "sku" in df.columns:
                    skus_importar = set(df["sku"].dropna().astype(str))
                    df_para_importar = magis_norm_ref[
                        magis_norm_ref["sku"].astype(str).isin(skus_importar)
                    ]
                    if not df_para_importar.empty:
                        df_imp_prod = gerar_planilha_importacao_produtos_tiny(df_para_importar)
                        data_ip, mime_ip, ext_ip = converter_dataframe(
                            df_imp_prod, formato_download, "Importação Produtos"
                        )
                        st.download_button(
                            label=f"📥 Gerar planilha Tiny ({formato_download})",
                            data=data_ip,
                            file_name=f"Importacao_Produtos_Tiny{ext_ip}",
                            mime=mime_ip,
                            use_container_width=True,
                            type="primary",
                        )
            cols = ["sku", "titulo", "ean", "preco_custo", "estoque"]
            valid_cols = [c for c in cols if c in df.columns] or \
                         [f"{c}_magis" for c in cols if f"{c}_magis" in df.columns]
            st.dataframe(df[valid_cols], use_container_width=True)
            st.caption(
                "⬆️ Use **Tiny → Cadastros → Produtos → Mais Ações → Importar produtos de uma planilha** "
                "para importar. A planilha já está no formato aceito pelo Tiny (64 colunas)."
            )

    # TAB 2 — Revisar no Tiny
    with tabs[2]:
        df = resultados.get("somente_tiny", pd.DataFrame())
        if df.empty:
            st.success("Nenhum produto exclusivo do Tiny encontrado.")
        else:
            cols = ["sku", "titulo", "ean", "preco_custo", "estoque"]
            valid_cols = [c for c in cols if c in df.columns] or \
                         [f"{c}_tiny" for c in cols if f"{c}_tiny" in df.columns]

            col_msg, col_btn = st.columns([3, 1])
            with col_msg:
                st.warning(
                    f"**{len(df)} produto(s) existem apenas no Tiny** (ativos). "
                    "Podem ser cadastros órfãos ou produtos que ainda não chegaram ao Magis."
                )
            with col_btn:
                df_rev = df[valid_cols].copy() if valid_cols else df
                data_rv, mime_rv, ext_rv = converter_dataframe(df_rev, formato_download, "Revisar Tiny")
                st.download_button(
                    label=f"📋 Exportar lista ({formato_download})",
                    data=data_rv,
                    file_name=f"Revisao_Produtos_Tiny{ext_rv}",
                    mime=mime_rv,
                    use_container_width=True,
                )
            st.dataframe(df[valid_cols], use_container_width=True)

    # TAB 3 — Sugestões de Match
    with tabs[3]:
        df = resultados.get("sugestao_match_titulo", pd.DataFrame())
        if df.empty:
            st.info("Nenhuma sugestão de match por similaridade de título.")
        else:
            st.caption(
                "Produtos sem match por SKU mas com títulos similares. "
                "Confirme manualmente se são o mesmo produto com SKU diferente."
            )
            def color_score(val):
                color = '#059669' if val >= 90 else '#d97706'
                return f'color: {color}; font-weight: 600;'
            st.dataframe(df.style.map(color_score, subset=['score']), use_container_width=True)

    # TAB 4 — Sincronizados (OK)
    with tabs[4]:
        df = resultados.get("presente_nos_dois", pd.DataFrame())
        if df.empty:
            st.info("Nenhum produto sincronizado entre os dois sistemas.")
        else:
            st.success(f"**{len(df)} produto(s)** presentes nos dois sistemas. Nenhuma ação necessária.")
            cols = ["sku", "titulo_magis", "status_magis", "status_tiny"]
            valid_cols = [c for c in cols if c in df.columns]
            if not valid_cols:
                valid_cols = [c for c in df.columns if c not in ("_merge", "classificacao")][:6]
            st.dataframe(df[valid_cols], use_container_width=True)


def _renderizar_aba_catalogo_tiny(tiny_norm: pd.DataFrame, formato_download: str):
    """Catálogo do Tiny com filtro de produtos pai (Código do pai vazio)."""
    from src.filtros.catalogo_tiny import filtrar_produtos_pai

    if tiny_norm is None or tiny_norm.empty:
        st.info("Nenhum dado do Tiny carregado.")
        return

    total = len(tiny_norm)
    pais = filtrar_produtos_pai(tiny_norm)
    n_pais = len(pais)
    n_filhos = total - n_pais

    exibir_metricas_4_colunas("📚 Visão Geral do Catálogo (Tiny)", [
        (total,    "Total no Tiny",         "nos-dois"),
        (n_pais,   "Produtos pai",          "magis"),
        (n_filhos, "Variações (filhos)",    "tiny"),
        (round(n_pais / total * 100) if total else 0, "% Pais", "divergente"),
    ])

    if "codigo_pai" not in tiny_norm.columns:
        st.info(
            "ℹ️ A planilha enviada não contém a coluna **Código do pai**. "
            "Todos os SKUs estão sendo tratados como produtos pai por padrão."
        )

    st.markdown("#### 📑 Lista de SKUs")

    modo = st.radio(
        "Visualização",
        options=["Apenas produtos pai", "Catálogo completo"],
        horizontal=True,
        key="catalogo_tiny_modo",
    )
    df_exibir = pais if modo == "Apenas produtos pai" else tiny_norm

    busca = st.text_input(
        "🔎 Buscar por SKU ou título",
        key="catalogo_tiny_busca",
        placeholder="Digite parte do SKU ou do título...",
    ).strip()
    if busca:
        mask = pd.Series(False, index=df_exibir.index)
        if "sku" in df_exibir.columns:
            mask = mask | df_exibir["sku"].astype(str).str.contains(busca, case=False, na=False)
        if "titulo" in df_exibir.columns:
            mask = mask | df_exibir["titulo"].astype(str).str.contains(busca, case=False, na=False)
        df_exibir = df_exibir.loc[mask]

    colunas_preferidas = [
        "sku", "titulo", "codigo_pai", "tipo_produto",
        "ncm", "cest", "estoque", "preco", "status",
    ]
    colunas_visiveis = [c for c in colunas_preferidas if c in df_exibir.columns]
    if not colunas_visiveis:
        colunas_visiveis = list(df_exibir.columns[:8])

    col_msg, col_btn = st.columns([3, 1])
    with col_msg:
        rotulo = "produto(s) pai" if modo == "Apenas produtos pai" else "produto(s)"
        st.caption(f"Exibindo **{len(df_exibir)} {rotulo}**.")
    with col_btn:
        sufixo_arquivo = "pais" if modo == "Apenas produtos pai" else "completo"
        dados, mime, ext = converter_dataframe(df_exibir[colunas_visiveis], formato_download, "Catalogo_Tiny")
        st.download_button(
            label=f"📥 Exportar ({formato_download})",
            data=dados,
            file_name=f"Catalogo_Tiny_{sufixo_arquivo}{ext}",
            mime=mime,
            use_container_width=True,
        )

    st.dataframe(df_exibir[colunas_visiveis], use_container_width=True, hide_index=True)


def _renderizar_aba_kits(resultados: dict, formato_download: str):
    """Renderiza a aba de análise de Kits (KPIs, métricas e 4 sub-tabs)."""
    kpis_k = _calcular_kpis_kits(resultados)
    exibir_painel_saude(kpis_k, "Kits")
    exibir_metricas_kits(resultados)

    st.markdown("#### 📑 Detalhamento dos Kits")

    n_div_k = kpis_k['divergentes']
    n_imp_k = kpis_k['s_magis']
    n_rev_k = kpis_k['s_tiny']
    n_ok_k  = kpis_k['nos_dois']

    tabs_k = st.tabs([
        f"✕ Composição Divergente ({n_div_k})",
        f"→ Importar no Tiny ({n_imp_k})",
        f"⚠️ Revisar no Tiny ({n_rev_k})",
        f"✅ Sincronizados ({n_ok_k})",
    ])

    # TAB 0 — Composição Divergente
    with tabs_k[0]:
        df = resultados.get("kits_divergentes", pd.DataFrame())
        if df.empty:
            st.success("Nenhum kit com composição divergente entre os sistemas.")
        else:
            st.error(
                f"**{len(df)} kit(s)** presentes nos dois sistemas mas com componentes ou "
                "quantidades diferentes. Corrija a composição antes de sincronizar."
            )
            st.dataframe(df, use_container_width=True)

            df_imp_div = resultados.get("df_import_kits_divergentes", pd.DataFrame())
            if not df_imp_div.empty:
                data_d, mime_d, ext_d = converter_dataframe(
                    df_imp_div, formato_download, 'Kits Divergentes'
                )
                st.download_button(
                    label=f"📥 Baixar Planilha de Correção de Kits no Tiny ({formato_download})",
                    data=data_d,
                    file_name=f"Correcao_Kits_Divergentes_Tiny{ext_d}",
                    mime=mime_d,
                    use_container_width=True,
                    type="primary",
                )
                st.caption(
                    "⬆️ Essa planilha substitui a composição atual dos kits no Tiny "
                    "pela composição como está no Magis. Importe em "
                    "**Tiny → Cadastros → Produtos → Mais Ações → Importar kits/fabricados**."
                )
            rej_div = resultados.get("kits_divergentes_rejeitados", [])
            if rej_div:
                with st.expander(f"⚠️ {len(rej_div)} kit(s) divergente(s) não exportáveis"):
                    st.dataframe(pd.DataFrame(rej_div), use_container_width=True)

    # TAB 1 — Importar no Tiny
    with tabs_k[1]:
        df = resultados.get("kits_somente_magis", pd.DataFrame())

        df_desconhecido = resultados.get("kits_somente_magis_desconhecido", pd.DataFrame())
        if not df_desconhecido.empty:
            st.warning(
                f"⚠️ {len(df_desconhecido)} kit(s) com status **desconhecido** foram separados abaixo. "
                "Para classificá-los corretamente, carregue também a planilha de Produtos do Magis."
            )
            with st.expander(f"Ver {len(df_desconhecido)} kit(s) com status desconhecido"):
                st.dataframe(df_desconhecido, use_container_width=True)

        if df.empty:
            st.success("Todos os kits ativos do Magis já estão no Tiny.")
        else:
            st.info(f"**{len(df)} kit(s) ativo(s) no Magis** que precisam ser importados no Tiny.")
            st.dataframe(df, use_container_width=True)

        # ── Alerta de Tipo de Produto incorreto ──
        alertas_tipo = resultados.get("alertas_tipo", [])
        df_correcao  = resultados.get("df_correcao_tipos", pd.DataFrame())

        if alertas_tipo:
            st.markdown("---")
            st.error(
                f"🚨 **{len(alertas_tipo)} produto(s) com tipo incorreto no Tiny.** "
                "Esses SKUs precisam ser do tipo **K** (Kit). "
                "Importe a planilha de correção **antes** de importar os Kits."
            )
            df_alertas_display = pd.DataFrame(alertas_tipo).rename(columns={
                'sku': 'SKU', 'titulo': 'Descrição',
                'tipo_atual': 'Tipo Atual', 'tipo_esperado': 'Tipo Correto',
            })
            st.dataframe(df_alertas_display, use_container_width=True)
            if not df_correcao.empty:
                data_cor, mime_cor, ext_cor = converter_dataframe(df_correcao, formato_download, 'Correção Tipos')
                st.download_button(
                    label=f"🔧 Baixar Planilha de Correção ({formato_download})",
                    data=data_cor,
                    file_name=f"Correcao_Tipos_Produto_Tiny{ext_cor}",
                    mime=mime_cor,
                    use_container_width=True,
                    type="primary",
                )
                st.caption(
                    "⬆️ Importe em **Tiny → Cadastros → Produtos → Mais Ações → Importar produtos** "
                    "para corrigir o tipo. Depois processe os Kits novamente."
                )
            st.markdown("---")

        # ── Planilha de importação de Kits ──
        df_import_tiny = resultados.get("df_import_tiny_kits", pd.DataFrame())
        if not df_import_tiny.empty:
            data_imp, mime_imp, ext_imp = converter_dataframe(df_import_tiny, formato_download, 'Importação Kits')
            st.download_button(
                label=f"📥 Baixar Planilha de Importação Tiny ({formato_download})",
                data=data_imp,
                file_name=f"Importacao_Kits_Tiny{ext_imp}",
                mime=mime_imp,
                use_container_width=True,
                type="secondary",
            )
        rejeitados = resultados.get("kits_rejeitados_importacao", [])
        if rejeitados:
            st.warning(f"⚠️ {len(rejeitados)} kit(s) não podem ser exportados devido a regras do Olist.")
            with st.expander("Ver motivos de rejeição"):
                st.dataframe(pd.DataFrame(rejeitados), use_container_width=True)

    # TAB 2 — Revisar no Tiny
    with tabs_k[2]:
        df = resultados.get("kits_somente_tiny", pd.DataFrame())
        if df.empty:
            st.success("Nenhum kit exclusivo do Tiny encontrado.")
        else:
            col_msg, col_btn = st.columns([3, 1])
            with col_msg:
                st.warning(
                    f"**{len(df)} kit(s) existem apenas no Tiny** (ativos). "
                    "Verifique se são cadastros válidos ou órfãos."
                )
            with col_btn:
                data_rk, mime_rk, ext_rk = converter_dataframe(df, formato_download, "Revisar Kits Tiny")
                st.download_button(
                    label=f"📋 Exportar lista ({formato_download})",
                    data=data_rk,
                    file_name=f"Revisao_Kits_Tiny{ext_rk}",
                    mime=mime_rk,
                    use_container_width=True,
                )
            st.dataframe(df, use_container_width=True)

    # TAB 3 — Sincronizados (OK)
    with tabs_k[3]:
        df = resultados.get("kits_nos_dois", pd.DataFrame())
        if df.empty:
            st.info("Nenhum kit sincronizado entre os dois sistemas.")
        else:
            st.success(f"**{len(df)} kit(s)** com composição idêntica nos dois sistemas. Nenhuma ação necessária.")
            st.dataframe(df, use_container_width=True)


def main():
    # Cabeçalho
    st.markdown("<h1><span style='color:#2563eb;'>🔄 Comparador de Catálogo</span> Magis × Tiny</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 1.1rem; margin-bottom: 2rem;'>Ferramenta Analítica de Saneamento e Migração de Produtos e Kits</p>", unsafe_allow_html=True)
    
    # Menu lateral
    with st.sidebar:
        st.header("⚙️ Configurações de Arquivos")
        st.markdown("<p style='color: #64748b; font-size: 0.9rem;'>Faça upload das planilhas exportadas diretamente dos respectivos sistemas.</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### 🛒 Cadastros de Produtos (Opcional)")
        files_magis = st.file_uploader("Upload Planilha Magis 5 - Produtos", type=['xlsx', 'xls'], accept_multiple_files=True)
        files_tiny = st.file_uploader("Upload Planilha Olist Tiny - Produtos", type=['xlsx', 'xls'], accept_multiple_files=True)
        
        st.markdown("---")
        st.markdown("#### 📦 Cadastros de Kits (Opcional)")
        files_magis_kits = st.file_uploader("Upload Planilha Magis 5 - Kits", type=['xlsx', 'xls'], accept_multiple_files=True)
        files_tiny_kits = st.file_uploader("Upload Planilha Olist Tiny - Kits", type=['xlsx', 'xls'], accept_multiple_files=True)
        
        st.markdown("---")
        st.markdown("### ⚙️ Preferências de Download")
        formato_download = st.selectbox(
            "Formato de Exportação (Tiny)",
            options=["XLSX", "CSV", "XLS"],
            index=0
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        comecar = st.button("🚀 Processar Comparação", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🛠️ Funcionalidades Ativas:")
        st.markdown("✔ Match por SKU (Exato)")
        st.markdown("✔ Similaridade Fuzzy")
        st.markdown("✔ Validação Fiscal e Duplicidades")
        st.markdown("✔ Análise Estrutural de Kits")

    # Flags de contexto
    tem_produtos = bool(files_magis and files_tiny)
    tem_catalogo_tiny = bool(files_tiny)  # Tiny sozinho habilita visão de Catálogo
    tem_kits = bool(files_magis_kits or files_tiny_kits)

    # Área principal
    if not comecar:
        if not files_magis and not files_tiny and not files_magis_kits and not files_tiny_kits:
            st.info("👈 Adicione os arquivos no menu lateral (Produtos e/ou Kits) e clique em Processar.")

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("""
                <div style="text-align: center; margin-top: 50px; opacity: 0.4;">
                    <div style="font-size: 100px; margin-bottom: -20px;">📊</div>
                    <h2 style="color: #94a3b8;">Aguardando dados...</h2>
                </div>
                """, unsafe_allow_html=True)
        return

    if not tem_produtos and not tem_catalogo_tiny and not tem_kits:
        st.error("⚠️ Você precisa enviar ao menos um par de arquivos (Produtos **ou** Kits) do Magis e do Tiny, ou apenas a planilha do Tiny para ver o Catálogo.")
        return

    # Magis sozinho não tem uso — exige par com Tiny
    if files_magis and not files_tiny:
        st.error("⚠️ A planilha do **Magis** só pode ser usada em conjunto com a do **Tiny**. Envie também o Tiny ou use apenas a planilha do Tiny para ver o Catálogo.")
        return

    if (files_magis_kits and not files_tiny_kits) or (files_tiny_kits and not files_magis_kits):
        st.error("⚠️ Para comparar **Kits**, envie as planilhas de **ambos** os sistemas (Magis e Tiny).")
        return

    # ── Cache via session_state para evitar reprocessamento a cada interação ──
    def _gerar_cache_key(files_list: list | None) -> str:
        """Gera uma chave única baseada nos nomes e tamanhos dos arquivos."""
        if not files_list:
            return ""
        return "|".join(sorted(f"{f.name}:{f.size}" for f in files_list))

    cache_key = _gerar_cache_key(files_magis) + ";" + _gerar_cache_key(files_tiny) + ";" + \
                _gerar_cache_key(files_magis_kits) + ";" + _gerar_cache_key(files_tiny_kits)

    # Se já processou com os mesmos arquivos, reutiliza os resultados
    if not comecar and "resultados" in st.session_state and st.session_state.get("cache_key") == cache_key:
        resultados = st.session_state["resultados"]
        caminho_excel = st.session_state["caminho_excel"]
        tem_kits = st.session_state["tem_kits"]
        tiny_norm = st.session_state.get("tiny_norm")
        magis_norm = st.session_state.get("magis_norm")
    else:
        resultados: dict[str, pd.DataFrame] = {}
        tiny_norm = None
        magis_norm = None

        # Processamento de Produtos — Tiny é obrigatório quando há arquivos; Magis é opcional
        if tem_catalogo_tiny:
            with st.spinner('Lendo planilha do Tiny e normalizando dados...'):
                try:
                    tiny_raw = carregar_tiny(files_tiny)
                    if tiny_raw.empty:
                        st.error("⚠️ A planilha do **Tiny** está vazia ou não pôde ser lida. Verifique o arquivo enviado.")
                        return
                    if "sku" not in tiny_raw.columns:
                        st.error("⚠️ **Erro Crítico:** A coluna `SKU` não foi encontrada no **Tiny** após o mapeamento.")
                        return
                    tiny_norm = normalizar_dataframe(tiny_raw, sistema="tiny")
                except Exception as e:
                    st.error(f"Erro ao carregar e normalizar o Tiny: {str(e)}")
                    return

        if tem_produtos:
            with st.spinner('Lendo planilha do Magis e normalizando dados...'):
                try:
                    magis_raw = carregar_magis(files_magis)
                    if magis_raw.empty:
                        st.error("⚠️ A planilha do **Magis** está vazia ou não pôde ser lida. Verifique o arquivo enviado.")
                        return

                    colunas_obrigatorias = {"sku": "SKU"}
                    colunas_recomendadas = {"titulo": "Título/Descrição", "ncm": "NCM", "origem": "Origem"}

                    for col, label in colunas_obrigatorias.items():
                        if col not in magis_raw.columns:
                            st.error(f"⚠️ **Erro Crítico:** A coluna `{label}` não foi encontrada no **Magis** após o mapeamento.")
                            return

                    avisos = []
                    for col, label in colunas_recomendadas.items():
                        if col not in magis_raw.columns:
                            avisos.append(f"`{label}` ausente no Magis")
                        if col not in tiny_norm.columns:
                            avisos.append(f"`{label}` ausente no Tiny")
                    if avisos:
                        st.warning(f"⚠️ Coluna(s) recomendada(s) não encontrada(s): {', '.join(avisos)}. "
                                   "A comparação continuará, mas alguns relatórios podem ficar incompletos.")

                    magis_norm = normalizar_dataframe(magis_raw, sistema="magis")

                except Exception as e:
                    st.error(f"Erro ao carregar e normalizar o Magis: {str(e)}")
                    return

            with st.spinner('Cruzando bases de Produtos e identificando divergências...'):
                try:
                    resultados = executar_comparacao(magis_norm, tiny_norm)
                    resultados["magis_norm"] = magis_norm  # necessário para gerar planilha de importação
                except Exception as e:
                    st.error(f"Erro durante a comparação de Produtos: {str(e)}")
                    return

        # Processamento de Kits
        if tem_kits:
            with st.spinner('Processando e comparando planilhas de Kits...'):
                try:
                    magis_kits_raw = carregar_kits_magis(files_magis_kits) if files_magis_kits else pd.DataFrame()
                    if not magis_kits_raw.empty:
                        magis_kits_raw = enriquecer_status_kits(magis_kits_raw, magis_norm)
                    tiny_kits_raw = carregar_kits_tiny(files_tiny_kits) if files_tiny_kits else pd.DataFrame()

                    res_kits = comparar_kits(magis_kits_raw, tiny_kits_raw)

                    resultados["kits_somente_magis"]             = res_kits["somente_magis"]
                    resultados["kits_somente_magis_inativos"]    = res_kits.get("somente_magis_inativos", pd.DataFrame())
                    resultados["kits_somente_magis_desconhecido"] = res_kits.get("somente_magis_desconhecido", pd.DataFrame())
                    resultados["kits_somente_tiny"]              = res_kits["somente_tiny"]
                    resultados["kits_divergentes"]               = res_kits["divergentes"]
                    resultados["kits_nos_dois"]                  = res_kits.get("nos_dois", pd.DataFrame())

                    df_import_tiny_kits, kits_rejeitados, df_correcao_tipos, alertas_tipo = gerar_planilha_importacao_tiny(
                        magis_kits_raw,
                        res_kits["somente_magis"],
                        tiny_norm
                    )
                    resultados["df_import_tiny_kits"] = df_import_tiny_kits
                    resultados["kits_rejeitados_importacao"] = kits_rejeitados
                    resultados["df_correcao_tipos"] = df_correcao_tipos
                    resultados["alertas_tipo"] = alertas_tipo

                    df_import_div_kits, rej_div_kits = gerar_planilha_importacao_kits_divergentes(
                        magis_kits_raw,
                        res_kits["divergentes"],
                        tiny_norm,
                    )
                    resultados["df_import_kits_divergentes"] = df_import_div_kits
                    resultados["kits_divergentes_rejeitados"] = rej_div_kits

                except Exception as e:
                    st.error(f"Erro ao avaliar Kits: {str(e)}")
                    tem_kits = False

        # Só gera Excel consolidado se houve comparação ou kits a consolidar
        caminho_excel = None
        if tem_produtos or tem_kits:
            with st.spinner('Gerando Relatório Consolidado...'):
                try:
                    output_dir = ROOT / "data" / "output"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    caminho_excel = str(output_dir / "comparativo_temp.xlsx")
                    gerar_excel(resultados, caminho_excel)
                except Exception as e:
                    st.error(f"Erro ao gerar Excel: {str(e)}")
                    return

        # Salva no session_state para reutilizar em re-runs
        st.session_state["resultados"] = resultados
        st.session_state["caminho_excel"] = caminho_excel
        st.session_state["cache_key"] = cache_key
        st.session_state["tem_kits"] = tem_kits
        st.session_state["tiny_norm"] = tiny_norm
        st.session_state["magis_norm"] = magis_norm

    # Sucesso
    st.toast("Análise finalizada com sucesso!", icon="✅")

    # Exibições de UI — montar abas dinamicamente conforme o que foi enviado
    aba_specs: list[tuple[str, str]] = []
    if tem_produtos:
        aba_specs.append(("🛒 Análise de Produtos", "produtos"))
    if tem_catalogo_tiny:
        aba_specs.append(("📚 Catálogo Tiny", "catalogo_tiny"))
    if tem_kits:
        aba_specs.append(("📦 Análise de Kits", "kits"))

    if len(aba_specs) > 1:
        containers = st.tabs([label for label, _ in aba_specs])
    else:
        containers = [st.container()]

    for (label, chave), container in zip(aba_specs, containers):
        with container:
            if chave == "produtos":
                _renderizar_aba_produtos(resultados, formato_download)
            elif chave == "catalogo_tiny":
                _renderizar_aba_catalogo_tiny(tiny_norm, formato_download)
            elif chave == "kits":
                _renderizar_aba_kits(resultados, formato_download)

    # Botão de download do relatório consolidado (só quando houve comparação/kits)
    if caminho_excel:
        st.markdown("---")
        with open(caminho_excel, "rb") as file:
            file_data = file.read()
        st.download_button(
            label="📥 Exportar Relatório Consolidado (Excel)",
            data=file_data,
            file_name="Diagnostico_Catalogo_Magis_Tiny.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )

if __name__ == "__main__":
    main()
