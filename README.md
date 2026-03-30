# 🔄 Comparador de Catálogo (Magis 5 × Olist Tiny)

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Framework-FF4B4B)
![Status](https://img.shields.io/badge/Status-Ativo-success)

Este projeto é uma ferramenta analítica desenvolvida para comparar as bases de dados exportadas diretamente de dois sistemas ERP/Hubs: **Magis 5** e **Olist Tiny**. O sistema é vital para fins de **saneamento, auditoria e migração** de catálogos de produtos.

A aplicação utiliza uma interface gráfica rica (*Premium UI*) feita em Streamlit para fornecer insights rápidos e gerar um diagnóstico completo e exportável para Excel.

---

## ✨ Funcionalidades

O sistema é dividido na análise de dois domínios principais: **Produtos** e **Kits (Bundles)**.

1. **Análise de Produtos:**
    - **Match Exato por SKU:** Identifica produtos presentes nos dois sistemas.
    - **Produtos Exclusivos:** Lista produtos presentes apenas no Magis ou apenas no Tiny.
    - **Sugestão de Similaridade Fuzzy:** Aponta "possíveis matches" baseando-se em inteligência de texto em títulos de produtos, caso o SKU seja diferente.
    - **Validação Fiscal:** Cruza NCM, CEST e Origem, apontando divergências onde o mesmo produto (mesmo SKU) possui tributação diferente entre as plataformas.
    - **Duplicidades Internas:** Mostra produtos com Cadastro Duplicado (por SKU ou EAN) cadastrados em um mesmo ERP.

2. **Análise de Kits:**
    - Suporte a verificação estrutural e combinatória de Kits.
    - Identificação de Kits faltantes de cada lado.
    - **Divergência de Composição:** Compara a hierarquia do Kit verificando se um Kit possui os mesmos **Componentes (SKUs)** e em **Quantidades correspondentes**. Se o Magis tem `(Cadeira 2x)` e o Tiny tem `(Cadeira 1x)` para o mesmo Kit, ele alerta erro de composição.

3. **Geração de Relatório:**
    - Possibilidade de baixar tudo que foi processado no Dashboard em uma planilha `.xlsx` com múltiplas abas limpas para trabalho tabular.

---

## 🚀 Como Configurar e Executar (Local)

### 1. Pré-requisitos
- Ter o **Python 3.10+** instalado em sua máquina.
- Recomendável ter as ferramentas do terminal (`git`, `bash`).

### 2. Passo a passo

Primeiro, clone este repositório e acesse a pasta do projeto:
```bash
git clone https://github.com/LeandroBossiniSoleira/Conciliador.git
cd Conciliador
```

Crie um ambiente virtual (recomendado) para isolar as dependências do projeto:
```bash
python3 -m venv .venv

# Ative o ambiente virtual (Linux/Mac):
source .venv/bin/activate
# (Se estiver no Windows, use: .venv\Scripts\activate)
```

Instale as dependências contidas no `requirements.txt`:
```bash
pip install -r requirements.txt
```

Por fim, inicie a aplicação Streamlit:
```bash
# Opcional: usar o run.sh se for linux
./run.sh

# Padrão via Streamlit:
streamlit run app.py
```

O sistema abrirá automaticamente no seu navegador padrão no endereço estático `http://localhost:8501`.

---

## 🛠️ Como Utilizar a Ferramenta

O fluxo é dividido em três passos simples:

1. **Exportar Arquivos:** 
   - No **Magis 5**, baixe o relatório/tabela de Produtos (e Opcionalmente de Kits). O arquivo precisa ser em formato Excel (`.xlsx`).
   - No **Olist Tiny**, baixe o relatório de Produtos e Kits (`.xlsx`). O Tiny costuma limitar as planilhas a uma certa quantidade de linhas. Sem problemas! A nossa ferramenta **aceita múltiplos arquivos de uma vez**.
2. **Importação:**
   - Arraste todos os arquivos do Magis 5 (Produtos) para a zona designada, listados no painel lateral esquerdo.
   - Arraste todos os arquivos do Olist Tiny (Produtos).
   - *Se quiser testar os Kits*, expanda e envie as planilhas do Magis Kits e do Tiny Kits na área estipulada abaixo da de produtos.
3. **Pausar e Processar:**
   - Clique no botão azul gigante gigante **"🚀 Processar Comparação"**.
   - Analise os Cards visuais com as informações e navegue nas Abas detalhadas ("Análise de Produtos" e "Análise de Kits").
   - Utilize o botão ao final da página para **Exportar o Relatório Final (.xlsx)**.

---

## 📁 Estrutura Técnica

* `app.py`: Entrada (entrypoint) principal de visualização da UI contendo Injeção de CSS personalizado e componentes lógicos do fluxo de vida de renderização.
* `/config/mapa_campos.yaml`: O coração parametrizado do App. Determina quais colunas em Português das planilhas (`Descrição`, `SKU Componente`) são carregadas pelos scripts nativos sob "alias" idênticos. Altere este arquivo caso algum dos ERPs mude o nome de uma coluna.
* `/src/`:
  - `loaders/`: Central de carregamento do Excel via Pandas. Concatena multi-arquivos e garante padronização.
  - `comparators/`: A *business-logic* responsável pela intersecção dos dados, junções `left`, cruzamentos (`merge`) que retornam dicionários e DFs.
  - `validators/`: Validadores fiscais e fiscais puros.
  - `reports/`: Empacota os resultados em Abas de Excel otimizadas (Truncates, Limits).
