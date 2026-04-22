"""
aba_dicionario_sku.py
Aba "Dicionário SKU": CRUD dos códigos usados pelo corretor.

Estrutura:
  - 7 sub-tabs (PP, MP, T, QQQQ, EE, CC, GG)
  - Cada sub-tab lista os códigos (oficiais + aprendidos) e permite
    adicionar novos códigos/remover os aprendidos.
  - Códigos oficiais (YAML) não podem ser removidos pela UI.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.sku.dicionario import (
    BLOCOS_EDITAVEIS,
    adicionar_codigo,
    carregar_aprendido,
    carregar_dicionario,
    carregar_oficial,
    eh_oficial,
    remover_codigo,
)

_LABELS_BLOCO: dict[str, str] = {
    "PP":   "PP — Produto (2 chars)",
    "MP":   "MP — Matéria-prima / Acabamento (3 chars)",
    "T":    "T — Tamanho (1 char: G/M/P)",
    "QQQQ": "QQQQ — Quantidade (literais)",
    "EE":   "EE — Estampa (2 chars)",
    "CC":   "CC — Cor (2 chars)",
    "GG":   "GG — Gênero (2 chars: FM/MS/NT)",
}

_TAMANHOS_ESPERADOS: dict[str, int | None] = {
    "PP": 2, "MP": 3, "T": 1, "QQQQ": None, "EE": 2, "CC": 2, "GG": 2,
}


def _montar_df_bloco(bloco: str) -> pd.DataFrame:
    """Monta DF unificado (oficial + aprendido) para um bloco, com coluna 'Origem'."""
    oficial = carregar_oficial() or {}
    aprendido = carregar_aprendido() or {}

    if bloco == "QQQQ":
        literais_oficial = (oficial.get("QQQQ", {}) or {}).get("literais", {}) or {}
        literais_aprendido = aprendido.get("QQQQ", {}) or {}
        linhas = [
            {"Código": cod, "Descrição": desc, "Origem": "oficial"}
            for cod, desc in sorted(literais_oficial.items())
        ]
        linhas += [
            {"Código": cod, "Descrição": desc, "Origem": "aprendido"}
            for cod, desc in sorted(literais_aprendido.items())
            if cod not in literais_oficial
        ]
        return pd.DataFrame(linhas)

    d_ofi = oficial.get(bloco, {}) or {}
    d_apr = aprendido.get(bloco, {}) or {}
    linhas = [
        {"Código": cod, "Descrição": desc, "Origem": "oficial"}
        for cod, desc in sorted(d_ofi.items())
    ]
    linhas += [
        {"Código": cod, "Descrição": desc, "Origem": "aprendido"}
        for cod, desc in sorted(d_apr.items())
        if cod not in d_ofi
    ]
    return pd.DataFrame(linhas)


def _renderizar_sub_tab(bloco: str) -> None:
    st.markdown(f"##### {_LABELS_BLOCO[bloco]}")

    df = _montar_df_bloco(bloco)
    if df.empty:
        st.info("Nenhum código cadastrado neste bloco.")
    else:
        # Exibe a tabela como referência
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Formulário de adicionar ──
    st.markdown("**➕ Adicionar código**")
    tamanho = _TAMANHOS_ESPERADOS[bloco]
    dica_tamanho = f" ({tamanho} char{'s' if tamanho and tamanho > 1 else ''})" if tamanho else ""

    with st.form(key=f"form_add_{bloco}", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            codigo = st.text_input(f"Código{dica_tamanho}", key=f"cod_{bloco}")
        with c2:
            descricao = st.text_input("Descrição", key=f"desc_{bloco}")
        with c3:
            st.write("")
            st.write("")
            submit = st.form_submit_button("Adicionar", use_container_width=True)

        if submit:
            codigo_n = codigo.strip().upper()
            if not codigo_n or not descricao.strip():
                st.error("Informe código e descrição.")
            elif tamanho and len(codigo_n) != tamanho:
                st.error(f"Código deve ter {tamanho} caractere(s).")
            elif bloco == "T" and codigo_n not in ("G", "M", "P"):
                st.error("Bloco T só aceita G, M ou P.")
            elif bloco == "GG" and codigo_n not in ("FM", "MS", "NT"):
                st.error("Bloco GG só aceita FM, MS ou NT.")
            else:
                try:
                    adicionar_codigo(bloco, codigo_n, descricao.strip())
                    st.success(f"Código {codigo_n} adicionado ao bloco {bloco}.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    # ── Remover aprendido ──
    aprendidos = df[df["Origem"] == "aprendido"] if not df.empty else pd.DataFrame()
    if not aprendidos.empty:
        st.markdown("**🗑️ Remover código aprendido**")
        opcoes = [
            f"{row['Código']} — {row['Descrição']}"
            for _, row in aprendidos.iterrows()
        ]
        col_sel, col_btn = st.columns([3, 1])
        with col_sel:
            escolha = st.selectbox(
                "Selecione um código aprendido",
                options=opcoes,
                key=f"rem_sel_{bloco}",
                label_visibility="collapsed",
            )
        with col_btn:
            if st.button("Remover", key=f"rem_btn_{bloco}", use_container_width=True):
                codigo_rem = escolha.split(" — ", 1)[0].strip()
                if eh_oficial(bloco, codigo_rem):
                    st.error("Código oficial não pode ser removido pela UI.")
                elif remover_codigo(bloco, codigo_rem):
                    st.success(f"Código {codigo_rem} removido.")
                    st.rerun()
                else:
                    st.warning(f"Código {codigo_rem} não encontrado em aprendidos.")


def renderizar() -> None:
    st.markdown("### 📖 Dicionário SKU")
    st.caption(
        "Códigos usados pelo corretor. Os **oficiais** vêm do YAML (SOP SKU-01) e "
        "não podem ser removidos. Os **aprendidos** são persistidos em "
        "`config/dicionario_sku_aprendido.json` e podem ser adicionados/removidos aqui."
    )

    dic = carregar_dicionario()
    resumo = [
        (len(dic.get(b, {})) if b != "QQQQ" else len(dic["QQQQ"]["literais"]))
        for b in ("PP", "MP", "EE", "CC")
    ]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PP (Produtos)", resumo[0])
    c2.metric("MP (Matéria-prima)", resumo[1])
    c3.metric("EE (Estampas)", resumo[2])
    c4.metric("CC (Cores)", resumo[3])

    sub_tabs = st.tabs([b for b in BLOCOS_EDITAVEIS])
    for bloco, container in zip(BLOCOS_EDITAVEIS, sub_tabs):
        with container:
            _renderizar_sub_tab(bloco)
