"""
aba_dicionario_sku.py
Aba "Dicionário SKU": CRUD dos códigos usados pelo corretor.

Estrutura:
  - 7 sub-tabs (PP, MP, T, QQQQ, EE, CC, GG)
  - Cada sub-tab lista os códigos (oficiais + aprendidos) e permite:
      ➕ Adicionar novos códigos em `aprendido`
      ✏️ Editar descrição (oficial ou aprendido — edição de oficial cria
         override em `aprendido`)
      🗑️ Remover código aprendido. Se o código também existir no oficial,
         a remoção apaga apenas o override e restaura a descrição oficial.
  - Códigos puramente oficiais (sem override) não podem ser removidos.
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


def _extrair_dicts_bloco(bloco: str) -> tuple[dict, dict]:
    """Retorna (oficial_bloco, aprendido_bloco) achatados para o bloco."""
    oficial = carregar_oficial() or {}
    aprendido = carregar_aprendido() or {}
    if bloco == "QQQQ":
        d_ofi = (oficial.get("QQQQ", {}) or {}).get("literais", {}) or {}
        d_apr = aprendido.get("QQQQ", {}) or {}
    else:
        d_ofi = oficial.get(bloco, {}) or {}
        d_apr = aprendido.get(bloco, {}) or {}
    return d_ofi, d_apr


def _montar_df_bloco(bloco: str) -> pd.DataFrame:
    """Monta DF unificado (oficial + aprendido) para um bloco, com coluna 'Origem'.

    Se um código existe em ambos, aparece como 'aprendido (override)' com a
    descrição do aprendido (que prevalece).
    """
    d_ofi, d_apr = _extrair_dicts_bloco(bloco)

    linhas: list[dict] = []
    # Oficiais sem override
    for cod, desc in sorted(d_ofi.items()):
        if cod in d_apr:
            linhas.append(
                {"Código": cod, "Descrição": d_apr[cod], "Origem": "aprendido (override)"}
            )
        else:
            linhas.append({"Código": cod, "Descrição": desc, "Origem": "oficial"})
    # Aprendidos que não são override
    for cod, desc in sorted(d_apr.items()):
        if cod not in d_ofi:
            linhas.append({"Código": cod, "Descrição": desc, "Origem": "aprendido"})
    return pd.DataFrame(linhas)


def _validar_codigo(bloco: str, codigo: str) -> str | None:
    """Retorna uma mensagem de erro se o código for inválido para o bloco,
    ou None se estiver ok."""
    tamanho = _TAMANHOS_ESPERADOS[bloco]
    if not codigo:
        return "Informe o código."
    if tamanho and len(codigo) != tamanho:
        return f"Código deve ter {tamanho} caractere(s)."
    if bloco == "T" and codigo not in ("G", "M", "P"):
        return "Bloco T só aceita G, M ou P."
    if bloco == "GG" and codigo not in ("FM", "MS", "NT"):
        return "Bloco GG só aceita FM, MS ou NT."
    return None


def _renderizar_sub_tab(bloco: str) -> None:
    st.markdown(f"##### {_LABELS_BLOCO[bloco]}")

    df = _montar_df_bloco(bloco)
    if df.empty:
        st.info("Nenhum código cadastrado neste bloco.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    d_ofi, d_apr = _extrair_dicts_bloco(bloco)
    tamanho = _TAMANHOS_ESPERADOS[bloco]
    dica_tamanho = f" ({tamanho} char{'s' if tamanho and tamanho > 1 else ''})" if tamanho else ""

    # ── ➕ Adicionar ──
    st.markdown("**➕ Adicionar código**")
    with st.form(key=f"form_add_{bloco}", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            codigo = st.text_input(f"Código{dica_tamanho}", key=f"cod_add_{bloco}")
        with c2:
            descricao = st.text_input("Descrição", key=f"desc_add_{bloco}")
        with c3:
            st.write("")
            st.write("")
            submit_add = st.form_submit_button("Adicionar", use_container_width=True)

        if submit_add:
            codigo_n = codigo.strip().upper()
            descricao_n = descricao.strip()
            erro = _validar_codigo(bloco, codigo_n)
            if erro:
                st.error(erro)
            elif not descricao_n:
                st.error("Informe a descrição.")
            elif codigo_n in d_ofi or codigo_n in d_apr:
                st.error(
                    f"Código {codigo_n} já existe neste bloco. "
                    "Use a seção '✏️ Editar' para alterar a descrição."
                )
            else:
                try:
                    adicionar_codigo(bloco, codigo_n, descricao_n)
                    st.success(f"Código {codigo_n} adicionado ao bloco {bloco}.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    # ── ✏️ Editar ──
    todos_codigos = sorted(set(d_ofi) | set(d_apr))
    if todos_codigos:
        st.markdown("**✏️ Editar descrição**")
        st.caption(
            "Edição sempre grava em `dicionario_sku_aprendido.json`. "
            "Editar um código oficial cria um override (prevalece sobre o YAML)."
        )

        def _rotulo(cod: str) -> str:
            desc_atual = d_apr.get(cod, d_ofi.get(cod, ""))
            if cod in d_apr and cod in d_ofi:
                origem = "aprendido (override)"
            elif cod in d_apr:
                origem = "aprendido"
            else:
                origem = "oficial"
            return f"{cod} — {desc_atual}  ·  [{origem}]"

        col_sel, col_save = st.columns([3, 1])
        with col_sel:
            escolha_edit = st.selectbox(
                "Selecione um código para editar",
                options=todos_codigos,
                format_func=_rotulo,
                key=f"edit_sel_{bloco}",
            )
        desc_vigente = d_apr.get(escolha_edit, d_ofi.get(escolha_edit, ""))

        with st.form(key=f"form_edit_{bloco}", clear_on_submit=False):
            nova_desc = st.text_input(
                "Nova descrição",
                value=desc_vigente,
                key=f"edit_desc_{bloco}_{escolha_edit}",
            )
            submit_edit = st.form_submit_button("Salvar alteração", use_container_width=True)
            if submit_edit:
                nova_desc_n = nova_desc.strip()
                if not nova_desc_n:
                    st.error("Descrição não pode ser vazia.")
                elif nova_desc_n == desc_vigente:
                    st.info("Nenhuma alteração detectada.")
                else:
                    try:
                        adicionar_codigo(bloco, escolha_edit, nova_desc_n)
                        if escolha_edit in d_ofi and escolha_edit not in d_apr:
                            st.success(
                                f"Override criado para {escolha_edit} "
                                "(oficial preservado no YAML)."
                            )
                        else:
                            st.success(f"Descrição de {escolha_edit} atualizada.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    # ── 🗑️ Remover ──
    removíveis = sorted(d_apr.keys())
    if removíveis:
        st.markdown("**🗑️ Remover código aprendido / override**")

        def _rotulo_rem(cod: str) -> str:
            if cod in d_ofi:
                return (
                    f"{cod} — {d_apr[cod]}  ·  [remover override → volta ao oficial]"
                )
            return f"{cod} — {d_apr[cod]}  ·  [aprendido]"

        col_sel, col_btn = st.columns([3, 1])
        with col_sel:
            escolha_rem = st.selectbox(
                "Selecione um código",
                options=removíveis,
                format_func=_rotulo_rem,
                key=f"rem_sel_{bloco}",
                label_visibility="collapsed",
            )
        with col_btn:
            if st.button("Remover", key=f"rem_btn_{bloco}", use_container_width=True):
                if remover_codigo(bloco, escolha_rem):
                    if escolha_rem in d_ofi:
                        st.success(
                            f"Override de {escolha_rem} removido — descrição oficial restaurada."
                        )
                    else:
                        st.success(f"Código {escolha_rem} removido.")
                    st.rerun()
                else:
                    st.warning(f"Código {escolha_rem} não encontrado em aprendidos.")
    elif d_ofi:
        st.caption(
            "🔒 Apenas códigos aprendidos (ou overrides de oficiais) podem ser removidos. "
            "Os oficiais do YAML são preservados."
        )


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
