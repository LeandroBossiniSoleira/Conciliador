"""
componentes.py
Componentes reutilizáveis do Streamlit UI — painéis de saúde, cards de métricas,
helpers de conversão e consolidação.
"""

import io
import logging

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────
# Metric cards genérico
# ────────────────────────────────────────────

def exibir_metric_card(valor: int, label: str, css_class: str):
    """Renderiza um card de métrica individual."""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value {css_class}">{valor}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def exibir_metricas_4_colunas(
    titulo: str,
    metricas: list[tuple[int, str, str]],
):
    """
    Exibe 4 cards de métricas em colunas.

    Parameters
    ----------
    titulo : str
        Título da seção (markdown).
    metricas : list[tuple[int, str, str]]
        Lista de 4 tuplas (valor, label, css_class).
    """
    st.markdown(f"### {titulo}")
    colunas = st.columns(len(metricas))
    for col, (valor, label, css_class) in zip(colunas, metricas):
        with col:
            exibir_metric_card(valor, label, css_class)


# ────────────────────────────────────────────
# Painel de saúde (barra de progresso)
# ────────────────────────────────────────────

def exibir_painel_saude(kpis: dict, label: str):
    """Barra de progresso de sincronização + totais de ação/erro."""
    pct = kpis['pct']
    color = '#059669' if pct >= 80 else ('#d97706' if pct >= 50 else '#dc2626')

    st.markdown(f"""
    <div class="health-panel">
        <div class="health-panel-header">
            <span class="health-panel-title">Sincronização de {label}</span>
            <span class="health-panel-pct" style="color:{color};">{pct}%</span>
        </div>
        <div class="health-bar-track">
            <div class="health-bar-fill" style="width:{pct}%; background:{color};"></div>
        </div>
        <div class="health-panel-stats">
            <span>✅ <b style="color:#1e293b;">{kpis['nos_dois']}</b> de {kpis['total_magis']} sincronizados</span>
            <span>→ <b style="color:#2563eb;">{kpis['acoes_pendentes']}</b> ações pendentes</span>
            <span>✕ <b style="color:#dc2626;">{kpis['erros_criticos']}</b> erros críticos</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ────────────────────────────────────────────
# Conversão de DataFrame para download
# ────────────────────────────────────────────

def converter_dataframe(
    dataframe: pd.DataFrame, formato: str, sheet_name: str
) -> tuple[bytes, str, str]:
    """Serializa um DataFrame para o formato escolhido pelo usuário."""
    if formato == "CSV":
        return (
            dataframe.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
            "text/csv",
            ".csv",
        )
    if formato == "XLS":
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlwt') as writer:
                dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
            return output.getvalue(), "application/vnd.ms-excel", ".xls"
        except Exception:
            logger.warning("Falha ao exportar como XLS (xlwt), usando XLSX como fallback.", exc_info=True)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"


# ────────────────────────────────────────────
# Consolidação de erros para exportação
# ────────────────────────────────────────────

def montar_df_erros(resultados: dict) -> pd.DataFrame:
    """Consolida todos os erros críticos num único DataFrame para exportação."""
    partes = []
    mapeamentos = [
        ("divergencias_fiscais", "Divergência Fiscal"),
        ("duplicidades_sku_magis", "Duplicidade SKU (Magis)"),
        ("duplicidades_ean_magis", "Duplicidade EAN (Magis)"),
        ("duplicidades_sku_tiny", "Duplicidade SKU (Tiny)"),
        ("duplicidades_ean_tiny", "Duplicidade EAN (Tiny)"),
    ]
    for chave, label in mapeamentos:
        df = resultados.get(chave, pd.DataFrame())
        if not df.empty:
            d = df.copy()
            d.insert(0, "tipo_erro", label)
            partes.append(d)
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes, ignore_index=True)
