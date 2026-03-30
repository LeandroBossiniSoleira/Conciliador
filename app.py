import streamlit as st
import pandas as pd
import tempfile
import os
from pathlib import Path

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
from src.loaders.kits_loader import carregar_kits_magis, carregar_kits_tiny
from src.normalizers.normalizador import normalizar_dataframe
from src.comparators.comparador_produtos import executar_comparacao
from src.comparators.comparador_kits import comparar_kits
from src.reports.gerar_relatorios import gerar_excel


# Estilização CSS Moderna (Premium, Glassmorphism, Animations)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #f6f8fd 0%, #f1f5f9 100%);
    }

    h1, h2, h3, h4 {
        color: #1e293b;
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    .metric-card {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.4);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
        text-align: center;
        margin-bottom: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    }
    
    .metric-value {
        font-size: 36px;
        font-weight: 800;
        line-height: 1.2;
        margin-bottom: 5px;
        background: linear-gradient(to right, #2563eb, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-value.nos-dois { background: linear-gradient(to right, #059669, #10b981); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .metric-value.magis { background: linear-gradient(to right, #dc2626, #ef4444); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .metric-value.tiny { background: linear-gradient(to right, #d97706, #f59e0b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .metric-value.divergente { background: linear-gradient(to right, #7c3aed, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    
    .metric-label {
        font-size: 14px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Style sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
        color: #0f172a;
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
        color: white;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(255,255,255,0.5);
        padding: 8px;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 8px;
        color: #475569;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        color: #1e293b;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

</style>
""", unsafe_allow_html=True)


def exibir_metricas_produtos(resultados: dict[str, pd.DataFrame]):
    """Exibe cards de métricas para Produtos."""
    st.markdown("### 📊 Visão Geral de Produtos")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_nos_dois = len(resultados.get('presente_nos_dois', []))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value nos-dois">{total_nos_dois}</div>
            <div class="metric-label">✅ Presentes nos Dois</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        total_somente_magis = len(resultados.get('somente_magis', []))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value magis">{total_somente_magis}</div>
            <div class="metric-label">🔍 Exclusivo Magis</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        total_somente_tiny = len(resultados.get('somente_tiny', []))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value tiny">{total_somente_tiny}</div>
            <div class="metric-label">📦 Exclusivo Tiny</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        total_erros_fiscais = len(resultados.get('divergencias_fiscais', []))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value divergente">{total_erros_fiscais}</div>
            <div class="metric-label">⚠️ Divergência Fiscal</div>
        </div>
        """, unsafe_allow_html=True)

def exibir_metricas_kits(resultados: dict[str, pd.DataFrame]):
    """Exibe cards de métricas para Kits."""
    st.markdown("### 📦 Visão Geral de Kits")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_somente_magis = len(resultados.get('kits_somente_magis', []))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value magis">{total_somente_magis}</div>
            <div class="metric-label">🔍 Kits Exclusivo Magis</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        total_somente_tiny = len(resultados.get('kits_somente_tiny', []))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value tiny">{total_somente_tiny}</div>
            <div class="metric-label">📦 Kits Exclusivo Tiny</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        total_divergentes = len(resultados.get('kits_divergentes', []))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value divergente">{total_divergentes}</div>
            <div class="metric-label">⚠️ Kits Divergentes (Composição)</div>
        </div>
        """, unsafe_allow_html=True)


def main():
    # Cabeçalho
    st.markdown("<h1><span style='color:#2563eb;'>🔄 Comparador de Catálogo</span> Magis × Tiny</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 1.1rem; margin-bottom: 2rem;'>Ferramenta Analítica de Saneamento e Migração de Produtos e Kits</p>", unsafe_allow_html=True)
    
    # Menu lateral
    with st.sidebar:
        st.header("⚙️ Configurações de Arquivos")
        st.markdown("<p style='color: #64748b; font-size: 0.9rem;'>Faça upload das planilhas exportadas diretamente dos respectivos sistemas.</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("#### 🛒 Cadastros de Produtos")
        files_magis = st.file_uploader("Upload Planilha Magis 5 (.xlsx) - Produtos", type=['xlsx'], accept_multiple_files=True)
        files_tiny = st.file_uploader("Upload Planilha Olist Tiny (.xlsx) - Produtos", type=['xlsx'], accept_multiple_files=True)
        
        st.markdown("---")
        st.markdown("#### 📦 Cadastros de Kits (Opcional)")
        files_magis_kits = st.file_uploader("Upload Planilha Magis 5 (.xlsx) - Kits", type=['xlsx'], accept_multiple_files=True)
        files_tiny_kits = st.file_uploader("Upload Planilha Olist Tiny (.xlsx) - Kits", type=['xlsx'], accept_multiple_files=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        comecar = st.button("🚀 Processar Comparação", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🛠️ Funcionalidades Ativas:")
        st.markdown("✔ Match por SKU (Exato)")
        st.markdown("✔ Similaridade Fuzzy")
        st.markdown("✔ Validação Fiscal e Duplicidades")
        st.markdown("✔ Análise Estrutural de Kits")

    # Área principal
    if not comecar:
        if not files_magis and not files_tiny:
            st.info("👈 Adicione os arquivos no menu lateral, para Produtos e opcionalmente para Kits, e clique em Iniciar.")
            
            # Exibe uma ilustração (placeholder)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("""
                <div style="text-align: center; margin-top: 50px; opacity: 0.4;">
                    <div style="font-size: 100px; margin-bottom: -20px;">📊</div>
                    <h2 style="color: #94a3b8;">Aguardando dados...</h2>
                </div>
                """, unsafe_allow_html=True)
        return

    if not files_magis or not files_tiny:
        st.error("⚠️ Você precisa enviar **ambos** os arquivos de Produtos (Magis e Tiny) para realizar a comparação principal.")
        return

    # Processamento e Análise
    with st.spinner('Lendo planilhas de Produtos e normalizando dados... Isto pode levar um tempo se houver vários arquivos.'):
        try:
            # Produtos
            magis_raw = carregar_magis(files_magis)
            tiny_raw = carregar_tiny(files_tiny)
            
            if magis_raw.empty or tiny_raw.empty:
                st.error("⚠️ Uma das planilhas de produto está vazia.")
                return
                
            if "sku" not in magis_raw.columns:
                st.error("⚠️ **Erro Crítico:** A coluna `sku` não foi encontrada no Magis após o mapeamento.")
                return
                
            if "sku" not in tiny_raw.columns:
                st.error("⚠️ **Erro Crítico:** A coluna `sku` não foi encontrada no Tiny após o mapeamento.")
                return
            
            magis_norm = normalizar_dataframe(magis_raw, sistema="magis")
            tiny_norm = normalizar_dataframe(tiny_raw, sistema="tiny")
            
        except Exception as e:
            st.error(f"Erro ao carregar e normalizar Produtos: {str(e)}")
            return

    with st.spinner('Cruzando bases de Produtos e identificando divergências...'):
        try:
            resultados = executar_comparacao(magis_norm, tiny_norm)
        except Exception as e:
            st.error(f"Erro durante a comparação de Produtos: {str(e)}")
            return

    # Processando Kits se houver arquivos
    tem_kits = bool(files_magis_kits or files_tiny_kits)
    if tem_kits:
        with st.spinner('Processando e comparando planilhas de Kits...'):
            try:
                magis_kits_raw = carregar_kits_magis(files_magis_kits) if files_magis_kits else pd.DataFrame()
                tiny_kits_raw = carregar_kits_tiny(files_tiny_kits) if files_tiny_kits else pd.DataFrame()
                
                res_kits = comparar_kits(magis_kits_raw, tiny_kits_raw)
                
                resultados["kits_somente_magis"] = res_kits["somente_magis"]
                resultados["kits_somente_tiny"] = res_kits["somente_tiny"]
                resultados["kits_divergentes"] = res_kits["divergentes"]
                
            except Exception as e:
                st.error(f"Erro ao avaliar Kits: {str(e)}")
                tem_kits = False

    with st.spinner('Gerando Relatório Consolidado...'):
        try:
            output_dir = ROOT / "data" / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            caminho_excel = str(output_dir / "comparativo_temp.xlsx")
            gerar_excel(resultados, caminho_excel)
        except Exception as e:
            st.error(f"Erro ao gerar Excel: {str(e)}")
            return

    # Sucesso
    st.toast("Análise finalizada com sucesso!", icon="✅")
    
    # Exibições de UI
    if tem_kits:
        aba_produtos, aba_kits = st.tabs(["🛒 Análise de Produtos", "📦 Análise de Kits"])
    else:
        aba_produtos = st.container()

    # -- ABA DE PRODUTOS --
    with aba_produtos:
        exibir_metricas_produtos(resultados)
        
        st.markdown("#### 📑 Detalhamento dos Produtos")
        tabs = st.tabs([
            "Somente Magis", 
            "Somente Tiny", 
            "Sugestões Match Título",
            "Divergências Fiscais",
            "Duplicidades Internas"
        ])
        
        with tabs[0]:
            df = resultados.get("somente_magis", pd.DataFrame())
            st.markdown(f"**{len(df)} produtos cadastrados apenas no Magis 5.**")
            if not df.empty:
                cols = ["sku", 'titulo', 'ean', 'preco_custo', 'estoque']
                valid_cols = []
                for c in cols:
                    if c in df.columns: valid_cols.append(c)
                    elif f"{c}_magis" in df.columns: valid_cols.append(f"{c}_magis")
                st.dataframe(df[valid_cols], use_container_width=True)
                
        with tabs[1]:
            df = resultados.get("somente_tiny", pd.DataFrame())
            st.markdown(f"**{len(df)} produtos cadastrados apenas no Olist Tiny.**")
            if not df.empty:
                cols = ["sku", 'titulo', 'ean', 'preco_custo', 'estoque']
                valid_cols = []
                for c in cols:
                    if c in df.columns: valid_cols.append(c)
                    elif f"{c}_tiny" in df.columns: valid_cols.append(f"{c}_tiny")
                st.dataframe(df[valid_cols], use_container_width=True)
                
        with tabs[2]:
            df = resultados.get("sugestao_match_titulo", pd.DataFrame())
            if not df.empty:
                def color_score(val):
                    color = '#059669' if val >= 90 else '#d97706'
                    return f'color: {color}; font-weight: 600;'
                st.dataframe(df.style.map(color_score, subset=['score']), use_container_width=True)
            else:
                st.info("Nenhuma sugestão forte de match por similaridade.")

        with tabs[3]:
            df = resultados.get("divergencias_fiscais", pd.DataFrame())
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.success("Nenhuma divergência nas propriedades fiscais encontrada.")
                
        with tabs[4]:
            colA, colB = st.columns(2)
            with colA:
                st.markdown("**Duplicados no Magis 5**")
                st.write("Por SKU:", len(resultados.get("duplicidades_sku_magis", [])))
                st.write("Por EAN:", len(resultados.get("duplicidades_ean_magis", [])))
            with colB:
                st.markdown("**Duplicados no Olist Tiny**")
                st.write("Por SKU:", len(resultados.get("duplicidades_sku_tiny", [])))
                st.write("Por EAN:", len(resultados.get("duplicidades_ean_tiny", [])))

    # -- ABA DE KITS --
    if tem_kits:
        with aba_kits:
            exibir_metricas_kits(resultados)
            
            st.markdown("#### 📑 Detalhamento dos Kits")
            tabs_k = st.tabs([
                "Kits Somente Magis",
                "Kits Somente Tiny",
                "Kits Composição Divergente"
            ])
            with tabs_k[0]:
                df = resultados.get("kits_somente_magis", pd.DataFrame())
                st.markdown(f"**{len(df)} Kits exclusivos do Magis.**")
                if not df.empty: st.dataframe(df, use_container_width=True)
            
            with tabs_k[1]:
                df = resultados.get("kits_somente_tiny", pd.DataFrame())
                st.markdown(f"**{len(df)} Kits exclusivos do Tiny.**")
                if not df.empty: st.dataframe(df, use_container_width=True)
                
            with tabs_k[2]:
                df = resultados.get("kits_divergentes", pd.DataFrame())
                st.markdown(f"**{len(df)} Kits com componentes diferentes (SKU ou Quantidade).**")
                if not df.empty: st.dataframe(df, use_container_width=True)

    st.markdown("---")
    
    # Botão de download gigante
    with open(caminho_excel, "rb") as file:
        st.download_button(
            label="📥 Exportar Relatório Consolidado (Excel)",
            data=file,
            file_name="Diagnostico_Catalogo_Magis_Tiny.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )

if __name__ == "__main__":
    main()
