"""
estilos.py
CSS centralizado para o Streamlit UI.
"""

CSS_GLOBAL = """
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

    /* Health panel */
    .health-panel {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 20px;
    }
    .health-panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .health-panel-title {
        font-weight: 700;
        color: #1e293b;
        font-size: 15px;
    }
    .health-panel-pct {
        font-weight: 800;
        font-size: 22px;
    }
    .health-bar-track {
        background: #f1f5f9;
        border-radius: 99px;
        height: 10px;
        overflow: hidden;
    }
    .health-bar-fill {
        height: 100%;
        border-radius: 99px;
    }
    .health-panel-stats {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        margin-top: 12px;
        font-size: 13px;
        color: #64748b;
    }

</style>
"""
