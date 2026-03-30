#!/usr/bin/env bash
# run.sh - Script para criar ambiente virtual e rodar o Streamlit
# Usado para evitar o erro "externally-managed-environment" em distribuições como Ubuntu/Debian

set -e

# Diretório base
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

VENV_DIR=".venv"

echo "🔄 Verificando ambiente Python isolado..."

# Se a pasta .venv não existe, cria o virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Criando ambiente virtual em $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Ativa o ambiente virtual
source "$VENV_DIR/bin/activate"

# Instala as dependências se o streamlit não estiver instalado ainda (ou para certificar que tudo está lá)
if ! python -c "import streamlit" &> /dev/null; then
    echo "📥 Instalando dependências (isso pode levar alguns segundos na primeira vez)..."
    pip install --upgrade pip -q
    pip install -r requirements.txt
    echo "✅ Dependências instaladas!"
fi

echo "🚀 Iniciando a interface visual com Streamlit..."
streamlit run app.py
