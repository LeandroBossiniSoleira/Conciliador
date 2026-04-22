"""
aba_dicionario_sku.py
Aba "Dicionário SKU": CRUD dos códigos usados pelo corretor.

Estrutura:
  - 7 sub-tabs (PP, MP, T, QQQQ, EE, CC, GG).
  - Cada sub-tab tem UMA tabela com seleção de linha + três botões no topo:
      ➕ Novo                — sempre habilitado (abre modal de cadastro)
      ✏️ Editar selecionado  — habilitado quando há linha selecionada
      🗑️ Remover selecionado — habilitado quando a linha selecionada está
                                no aprendido (oficiais puros não removem)
  - Cada botão abre um diálogo modal (`st.dialog`) com o form mínimo.
  - Editar um código oficial cria um override em
    `config/dicionario_sku_aprendido.json` (o YAML oficial é preservado).
  - Remover um override apaga só a entrada do JSON e restaura a descrição
    oficial do YAML.
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
    """Monta DF unificado (oficial + aprendido) para um bloco, com coluna 'Origem'."""
    d_ofi, d_apr = _extrair_dicts_bloco(bloco)
    linhas: list[dict] = []
    for cod, desc in sorted(d_ofi.items()):
        if cod in d_apr:
            linhas.append(
                {"Código": cod, "Descrição": d_apr[cod], "Origem": "aprendido (override)"}
            )
        else:
            linhas.append({"Código": cod, "Descrição": desc, "Origem": "oficial"})
    for cod, desc in sorted(d_apr.items()):
        if cod not in d_ofi:
            linhas.append({"Código": cod, "Descrição": desc, "Origem": "aprendido"})
    return pd.DataFrame(linhas)


def _validar_codigo(bloco: str, codigo: str) -> str | None:
    """Retorna mensagem de erro se o código for inválido para o bloco; senão None."""
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


def _dica_tamanho(bloco: str) -> str:
    tamanho = _TAMANHOS_ESPERADOS[bloco]
    if not tamanho:
        return ""
    return f" ({tamanho} char{'s' if tamanho > 1 else ''})"


# ──────────────────────────── Diálogos modais ────────────────────────────

@st.dialog("➕ Novo código")
def _dialog_novo(bloco: str) -> None:
    st.caption(f"Bloco **{_LABELS_BLOCO[bloco]}**.")

    codigo = st.text_input(f"Código{_dica_tamanho(bloco)}", key=f"dlg_novo_cod_{bloco}")
    descricao = st.text_input("Descrição", key=f"dlg_novo_desc_{bloco}")

    c1, c2 = st.columns(2)
    cancelar = c1.button(
        "Cancelar", use_container_width=True, key=f"dlg_novo_cancel_{bloco}"
    )
    salvar = c2.button(
        "Adicionar", type="primary", use_container_width=True,
        key=f"dlg_novo_save_{bloco}",
    )

    if cancelar:
        st.rerun()
    if salvar:
        codigo_n = codigo.strip().upper()
        descricao_n = descricao.strip()
        d_ofi, d_apr = _extrair_dicts_bloco(bloco)
        erro = _validar_codigo(bloco, codigo_n)
        if erro:
            st.error(erro)
        elif not descricao_n:
            st.error("Informe a descrição.")
        elif codigo_n in d_ofi or codigo_n in d_apr:
            st.error(
                f"Código {codigo_n} já existe. Use **Editar selecionado** "
                "para alterar a descrição."
            )
        else:
            try:
                adicionar_codigo(bloco, codigo_n, descricao_n)
                st.toast(f"✅ Código {codigo_n} adicionado ao bloco {bloco}.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))


@st.dialog("✏️ Editar código")
def _dialog_editar(bloco: str, codigo: str) -> None:
    d_ofi, d_apr = _extrair_dicts_bloco(bloco)
    if codigo not in d_ofi and codigo not in d_apr:
        st.error(f"Código {codigo} não existe mais.")
        if st.button("Fechar", key=f"dlg_edit_close_{bloco}_{codigo}"):
            st.rerun()
        return

    cria_override = codigo in d_ofi and codigo not in d_apr
    desc_vigente = d_apr.get(codigo, d_ofi.get(codigo, ""))

    st.caption(f"Bloco **{_LABELS_BLOCO[bloco]}**, código **{codigo}**.")
    if cria_override:
        st.info(
            "Este é um código **oficial**. Editá-lo cria um override em "
            "`dicionario_sku_aprendido.json` (o YAML oficial é preservado)."
        )

    nova_desc = st.text_input(
        "Descrição",
        value=desc_vigente,
        key=f"dlg_edit_desc_{bloco}_{codigo}",
    )

    c1, c2 = st.columns(2)
    cancelar = c1.button(
        "Cancelar", use_container_width=True,
        key=f"dlg_edit_cancel_{bloco}_{codigo}",
    )
    salvar = c2.button(
        "Salvar", type="primary", use_container_width=True,
        key=f"dlg_edit_save_{bloco}_{codigo}",
    )

    if cancelar:
        st.rerun()
    if salvar:
        nova_n = nova_desc.strip()
        if not nova_n:
            st.error("Descrição não pode ser vazia.")
        elif nova_n == desc_vigente:
            st.info("Nenhuma alteração detectada.")
        else:
            try:
                adicionar_codigo(bloco, codigo, nova_n)
                if cria_override:
                    st.toast(f"✅ Override criado para {codigo} (oficial preservado).")
                else:
                    st.toast(f"✅ Descrição de {codigo} atualizada.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))


@st.dialog("🗑️ Remover código")
def _dialog_remover(bloco: str, codigo: str) -> None:
    d_ofi, d_apr = _extrair_dicts_bloco(bloco)
    if codigo not in d_apr:
        st.error(
            f"Código {codigo} não está em `aprendido` — apenas códigos aprendidos "
            "(ou overrides de oficiais) podem ser removidos."
        )
        if st.button("Fechar", key=f"dlg_rem_close_{bloco}_{codigo}"):
            st.rerun()
        return

    eh_override = codigo in d_ofi
    desc = d_apr[codigo]

    st.caption(f"Bloco **{_LABELS_BLOCO[bloco]}**.")
    if eh_override:
        st.warning(
            f"**{codigo} — {desc}** é um override de um código oficial. "
            "Remover apaga apenas o override e restaura a descrição oficial do YAML."
        )
    else:
        st.warning(f"Remover **{codigo} — {desc}** do dicionário aprendido?")

    c1, c2 = st.columns(2)
    cancelar = c1.button(
        "Cancelar", use_container_width=True,
        key=f"dlg_rem_cancel_{bloco}_{codigo}",
    )
    confirmar = c2.button(
        "Remover", type="primary", use_container_width=True,
        key=f"dlg_rem_confirm_{bloco}_{codigo}",
    )

    if cancelar:
        st.rerun()
    if confirmar:
        if remover_codigo(bloco, codigo):
            if eh_override:
                st.toast(f"🗑️ Override de {codigo} removido — descrição oficial restaurada.")
            else:
                st.toast(f"🗑️ Código {codigo} removido.")
            st.rerun()
        else:
            st.error(f"Código {codigo} não encontrado em aprendidos.")


# ──────────────────────────── Render da sub-tab ────────────────────────────

def _renderizar_sub_tab(bloco: str) -> None:
    st.markdown(f"##### {_LABELS_BLOCO[bloco]}")

    df = _montar_df_bloco(bloco)
    _, d_apr = _extrair_dicts_bloco(bloco)

    # Reserva o espaço dos botões no topo para preenchê-lo após ler a seleção.
    botoes_slot = st.empty()

    if df.empty:
        st.info("Nenhum código cadastrado neste bloco. Use **➕ Novo** para começar.")
        with botoes_slot.container():
            col_n, _spacer = st.columns([1, 5])
            clicou_novo = col_n.button(
                "➕ Novo", key=f"btn_novo_{bloco}", use_container_width=True
            )
        st.caption(
            "🔒 Códigos oficiais são preservados no YAML; editá-los cria um override."
        )
        if clicou_novo:
            _dialog_novo(bloco)
        return

    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key=f"df_{bloco}",
    )

    selected_rows = event.selection.rows if event and event.selection else []
    cod_sel: str | None = None
    if selected_rows:
        cod_sel = str(df.iloc[selected_rows[0]]["Código"])

    pode_editar = cod_sel is not None
    pode_remover = cod_sel is not None and cod_sel in d_apr

    with botoes_slot.container():
        col_n, col_e, col_r, _spacer = st.columns([1.2, 1.8, 1.8, 5])
        clicou_novo = col_n.button(
            "➕ Novo", key=f"btn_novo_{bloco}", use_container_width=True
        )
        clicou_editar = col_e.button(
            "✏️ Editar selecionado",
            key=f"btn_edit_{bloco}",
            disabled=not pode_editar,
            use_container_width=True,
        )
        clicou_remover = col_r.button(
            "🗑️ Remover selecionado",
            key=f"btn_rem_{bloco}",
            disabled=not pode_remover,
            use_container_width=True,
        )

    st.caption(
        "🔒 Códigos oficiais são preservados no YAML; editá-los cria um override em "
        "`dicionario_sku_aprendido.json`. Apenas aprendidos (ou overrides) podem ser removidos."
    )

    if clicou_novo:
        _dialog_novo(bloco)
    elif clicou_editar and cod_sel is not None:
        _dialog_editar(bloco, cod_sel)
    elif clicou_remover and cod_sel is not None:
        _dialog_remover(bloco, cod_sel)


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
