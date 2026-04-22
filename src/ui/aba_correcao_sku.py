"""
aba_correcao_sku.py
Aba "Correção de SKUs": diagnostica SKUs do Tiny contra o padrão MEF,
permite o usuário aprovar/editar sugestões e exporta lista de renomeação
+ planilha Tiny 64 colunas com SKUs renomeados.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.sku.exportador import gerar_lista_renomeacao, gerar_planilha_tiny_renomeada
from src.sku.validator import analisar_dataframe
from src.ui.componentes import converter_dataframe, exibir_metricas_4_colunas


def _badge_status(status: str, tipo_erro: str | None) -> str:
    if status == "correto":
        return "✅ Correto"
    if status == "incompleto":
        return "⚠️ Incompleto"
    if tipo_erro == "estrutural":
        return "✕ Estrutural"
    if tipo_erro == "semantico":
        return "✕ Semântico"
    return "✕ Erro"


def renderizar(tiny_norm: pd.DataFrame, formato_download: str) -> None:
    st.markdown("### ✅ Correção de SKUs")
    st.caption(
        "Diagnóstico de cada SKU contra o padrão oficial **PP-MPT-QQQQ-EECC-[GG]**. "
        "Edite a coluna **SKU sugerido** se necessário, marque **Aprovar** nas linhas "
        "desejadas e gere os arquivos de renomeação."
    )

    if tiny_norm is None or tiny_norm.empty:
        st.info("Nenhum dado do Tiny carregado.")
        return

    cache_key = f"analise_sku::{id(tiny_norm)}::{len(tiny_norm)}"
    if cache_key not in st.session_state:
        with st.spinner("Analisando SKUs..."):
            st.session_state[cache_key] = analisar_dataframe(tiny_norm)
    df_analise: pd.DataFrame = st.session_state[cache_key].copy()

    total = len(df_analise)
    n_corretos = int((df_analise["status"] == "correto").sum())
    n_erros = int((df_analise["status"] == "erro").sum())
    n_manual = int(df_analise["precisa_acao_manual"].sum())

    exibir_metricas_4_colunas("📊 Visão Geral", [
        (total,      "Total SKUs",        "nos-dois"),
        (n_corretos, "Corretos ✅",       "nos-dois"),
        (n_erros,    "Com erro ✕",        "magis"),
        (n_manual,   "Ação manual ⚠️",    "tiny"),
    ])

    # ── Filtros ──
    st.markdown("#### 🔍 Filtros")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filtro_erro = st.checkbox("Apenas com erro", value=True, key="sku_filtro_erro")
    with col2:
        filtro_kit = st.checkbox("Apenas kits", value=False, key="sku_filtro_kit")
    with col3:
        filtro_sem_sugestao = st.checkbox(
            "Apenas sem sugestão automática", value=False, key="sku_filtro_sem_sug"
        )
    with col4:
        filtro_baixa_conf = st.checkbox(
            "Apenas baixa confiança (<60)", value=False, key="sku_filtro_baixa_conf"
        )

    busca = st.text_input(
        "Buscar por SKU ou título",
        key="sku_filtro_busca",
        placeholder="Digite parte do SKU ou do título...",
    ).strip()

    df = df_analise
    if filtro_erro:
        df = df[df["status"] == "erro"]
    if filtro_kit:
        df = df[df["eh_kit"] == True]  # noqa: E712
    if filtro_sem_sugestao:
        df = df[df["sku_sugerido"].isna() | (df["sku_sugerido"] == "")]
    if filtro_baixa_conf:
        df = df[df["confianca"] < 60]
    if busca:
        mask = (
            df["sku_original"].astype(str).str.contains(busca, case=False, na=False)
            | df["titulo"].astype(str).str.contains(busca, case=False, na=False)
        )
        df = df[mask]

    if df.empty:
        st.info("Nenhum SKU corresponde aos filtros atuais.")
        return

    # ── Tabela editável ──
    st.markdown(f"#### 📋 SKUs ({len(df)})")

    df_editor = df[[
        "sku_original", "titulo", "status", "tipo_erro",
        "problemas_txt", "sku_sugerido", "confianca",
    ]].copy()
    df_editor["status"] = df_editor.apply(
        lambda r: _badge_status(r["status"], r["tipo_erro"]), axis=1
    )
    df_editor.drop(columns=["tipo_erro"], inplace=True)
    df_editor["sku_sugerido"] = df_editor["sku_sugerido"].fillna("")
    df_editor.insert(len(df_editor.columns), "aprovar", False)

    df_editor = df_editor.rename(columns={
        "sku_original":  "SKU atual",
        "titulo":        "Título",
        "status":        "Status",
        "problemas_txt": "Problemas",
        "sku_sugerido":  "SKU sugerido",
        "confianca":     "Confiança (%)",
        "aprovar":       "Aprovar",
    })

    editado = st.data_editor(
        df_editor,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "SKU atual":     st.column_config.TextColumn(disabled=True, width="small"),
            "Título":        st.column_config.TextColumn(disabled=True, width="large"),
            "Status":        st.column_config.TextColumn(disabled=True, width="small"),
            "Problemas":     st.column_config.TextColumn(disabled=True, width="medium"),
            "SKU sugerido":  st.column_config.TextColumn(
                help="Edite o SKU sugerido se necessário antes de aprovar.",
                width="medium",
            ),
            "Confiança (%)": st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%d%%", width="small",
            ),
            "Aprovar":       st.column_config.CheckboxColumn(
                help="Marque para incluir na renomeação em massa.",
                width="small",
            ),
        },
        key="sku_editor",
    )

    # ── Monta mapa de renomeação aprovado ──
    aprovados = editado[editado["Aprovar"] == True]  # noqa: E712
    aprovados = aprovados[
        aprovados["SKU sugerido"].astype(str).str.strip() != ""
    ]
    aprovados = aprovados[
        aprovados["SKU sugerido"].astype(str).str.strip()
        != aprovados["SKU atual"].astype(str).str.strip()
    ]

    mapa_renomeacao: dict[str, str] = {
        str(r["SKU atual"]).strip(): str(r["SKU sugerido"]).strip()
        for _, r in aprovados.iterrows()
    }

    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.metric("SKUs aprovados", len(mapa_renomeacao))
    with c2:
        if st.button("🔄 Reanalisar", help="Reexecuta o diagnóstico (após editar o dicionário)."):
            st.session_state.pop(cache_key, None)
            st.rerun()

    # ── Downloads ──
    st.markdown("#### 📥 Exportar")
    col_a, col_b = st.columns(2)

    with col_a:
        # Lista de renomeação (auditoria) — sempre disponível, com todo o diagnóstico
        lista_completa = gerar_lista_renomeacao(df_analise)
        dados, mime, ext = converter_dataframe(
            lista_completa, formato_download, "Correcao_SKUs"
        )
        st.download_button(
            label=f"📋 Baixar lista de renomeação (diagnóstico) — {formato_download}",
            data=dados,
            file_name=f"Correcao_SKUs_diagnostico{ext}",
            mime=mime,
            use_container_width=True,
        )

    with col_b:
        if mapa_renomeacao:
            planilha_tiny = gerar_planilha_tiny_renomeada(tiny_norm, mapa_renomeacao)
            if not planilha_tiny.empty:
                dados, mime, ext = converter_dataframe(
                    planilha_tiny, formato_download, "Importacao_Tiny"
                )
                st.download_button(
                    label=f"📦 Baixar planilha Tiny renomeada ({len(mapa_renomeacao)}) — {formato_download}",
                    data=dados,
                    file_name=f"Importacao_Tiny_SKUs_renomeados{ext}",
                    mime=mime,
                    type="primary",
                    use_container_width=True,
                )
            else:
                st.info("Os SKUs aprovados não foram encontrados no catálogo Tiny.")
        else:
            st.caption(
                "Marque **Aprovar** em ao menos uma linha para gerar a planilha Tiny renomeada."
            )
