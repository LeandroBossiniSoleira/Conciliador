# 🔄 Comparador de Catálogo (Magis 5 × Olist Tiny)

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Framework-FF4B4B)
![Status](https://img.shields.io/badge/Status-Ativo-success)

Ferramenta de diagnóstico e ação para comparar, sanear e migrar catálogos de produtos entre os ERPs **Magis 5** e **Olist Tiny**. Vai além da simples visualização: classifica cada item por status de sincronização, filtra automaticamente o que não exige ação e gera planilhas prontas para importação diretamente no Tiny.

---

## ✨ Funcionalidades

### Painel de Saúde do Catálogo
- **Barra de progresso de sincronização** separada para Produtos e Kits
- KPIs em tempo real: `% sincronizado`, `ações pendentes`, `erros críticos`
- Cards de status com semântica visual: ✅ OK · → Ação · ⚠️ Alerta · ✕ Erro

### Análise de Produtos
- **Match exato por SKU** entre os dois sistemas
- **Filtro automático de inativos** — produtos INATIVO/EXCLUIDO não aparecem como problema
- **Erros Críticos (tab unificada):**
  - Divergências fiscais (NCM, CEST, Origem, EAN tributável) entre sistemas
  - Duplicidades de SKU e EAN dentro de cada sistema
- **Importar no Tiny** — lista de produtos ativos do Magis ausentes no Tiny + planilha de importação no formato exato de 64 colunas aceito pelo Tiny
- **Revisar no Tiny** — produtos ativos exclusivos do Tiny (possíveis órfãos)
- **Sugestões de Match por similaridade** (Fuzzy) para SKUs divergentes com títulos parecidos
- **Sincronizados** — auditoria do que já está correto nos dois sistemas

### Análise de Kits
- **Filtro automático de kits inativos/excluídos** no Magis — não aparecem como problema
- Kits com status desconhecido sinalizados separadamente (ocorre quando a planilha de produtos não é carregada junto)
- **Composição Divergente** — kits presentes nos dois sistemas com componentes ou quantidades diferentes
- **Importar no Tiny** — kits ativos do Magis ausentes no Tiny, com:
  - Validação de tipo de produto (deve ser `K`) e planilha de correção automática
  - Validação de componentes presentes no Tiny
  - Rejeição com motivo para kits que não podem ser importados
  - Planilha de importação no formato aceito pelo Tiny
- **Revisar no Tiny** — kits ativos exclusivos do Tiny
- **Sincronizados** — kits com composição idêntica nos dois sistemas

### Correção de SKUs (padrão MEF)
Diagnostica os SKUs do Tiny contra o padrão oficial `PP-MPT-QQQQ-EECC-[GG]` (SOP SKU-01) e gera planilha de reimportação com os SKUs renomeados.

- **Parser tolerante** — quebra o SKU em blocos (PP produto, MPT matéria-prima+tamanho, QQQQ quantidade, EECC estampa+cor, GG gênero) e classifica erros como **estruturais** ou **semânticos**
- **Motor de sugestão** a partir do título, com:
  - Longest-match contra o dicionário oficial + aprendido
  - Tolerância a plural, diminutivo e variação de gênero (`FRALDA ↔ FRALDAS/FRALDINHAS`, `FEMININO ↔ FEMININA`)
  - Heurísticas de kit — `+` no título força `PP=KT`; `Kit N unidades` mantém PP específico + `QQQQ=NNNU`
  - Nunca inventa códigos fora do dicionário; nunca sugere `EE=LS` automaticamente
  - Score de **confiança 0–100** por SKU (barra de progresso na tabela)
- **Tabela editável** (`st.data_editor`) — o usuário pode ajustar a sugestão antes de exportar e marca com checkbox **Aprovar** apenas as linhas que entram na reimportação
- **Filtros** — apenas com erro, apenas kits, sem sugestão automática, baixa confiança (<60) + busca livre
- **Exportações:**
  - 📋 Lista de renomeação (diagnóstico completo — auditoria)
  - 📦 Planilha Tiny 64 colunas com apenas os SKUs aprovados, já renomeados

### Dicionário SKU (CRUD)
- **7 sub-tabs** (PP, MP, T, QQQQ, EE, CC, GG) para gerenciar os códigos usados pelo corretor
- Códigos **oficiais** vêm de `config/dicionario_sku.yaml` (seed do SOP SKU-01) e são readonly
- Códigos **aprendidos** são persistidos em `config/dicionario_sku_aprendido.json` — adicionados/removidos pela UI e reconhecidos imediatamente pelo corretor
- Validação de tamanho por bloco (ex.: T = 1 char G/M/P; GG = FM/MS/NT; MP = 3 chars)

### Exportações contextuais
Cada seção oferece o botão de download relevante para a ação:

| Seção | Arquivo gerado |
|---|---|
| Erros Críticos | `Erros_Criticos_Produtos.xlsx` — todos os erros com coluna `tipo_erro` |
| Importar Produtos | `Importacao_Produtos_Tiny.xlsx` — 64 colunas, pronta para importar |
| Importar Kits | `Importacao_Kits_Tiny.xlsx` + `Correcao_Tipos_Produto_Tiny.xlsx` |
| Revisar Produtos | `Revisao_Produtos_Tiny.xlsx` |
| Revisar Kits | `Revisao_Kits_Tiny.xlsx` |
| Correção de SKUs | `Correcao_SKUs_diagnostico.xlsx` + `Importacao_Tiny_SKUs_renomeados.xlsx` (64 colunas) |
| Relatório Consolidado | `Diagnostico_Catalogo_Magis_Tiny.xlsx` — todas as abas |

Formato de exportação configurável na sidebar: **XLSX** (padrão) · **CSV** · **XLS**

---

## 🚀 Como executar

### Pré-requisitos
- Python 3.10+
- `git` e `bash`

### Passo a passo

```bash
git clone https://github.com/LeandroBossiniSoleira/Conciliador.git
cd Conciliador

# Cria e ativa o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt

# Inicia a aplicação
./run.sh         # Linux (cria o .venv automaticamente se necessário)
# ou
streamlit run app.py
```

A aplicação abre automaticamente em `http://localhost:8501`.

---

## 🛠️ Como utilizar

**Passo 1 — Exportar os arquivos dos sistemas**
- No **Magis 5**: exporte a planilha de Produtos e, opcionalmente, de Kits (`.xlsx`)
- No **Olist Tiny**: exporte Produtos e Kits (`.xlsx`). O Tiny limita linhas por arquivo — a ferramenta aceita múltiplos arquivos de uma vez

**Passo 2 — Fazer upload no painel lateral**
- Arraste os arquivos nas zonas correspondentes (Produtos Magis, Produtos Tiny, Kits Magis, Kits Tiny)
- Produtos e Kits são independentes — você pode enviar só um dos pares

**Passo 3 — Processar e agir**
- Clique em **"🚀 Processar Comparação"**
- Leia o painel de saúde no topo para entender o estado geral
- Navegue pelas tabs em ordem de prioridade (erros primeiro, depois ações)
- Use os botões de download contextuais em cada tab para gerar as planilhas necessárias

> **Fluxo recomendado:** Corrija os Erros Críticos → Importe os Produtos faltantes → Corrija tipos de produto → Importe os Kits → Verifique a aba Sincronizados

---

## 📁 Estrutura técnica

```
app.py                          # Entrypoint Streamlit — UI, KPIs, tabs
config/
  mapa_campos.yaml              # Mapeamento de colunas dos ERPs para schema interno
  regras_normalizacao.yaml      # Regras de limpeza de texto, status, campos fiscais
  dicionario_sku.yaml           # Dicionário oficial de códigos de SKU (SOP SKU-01)
  dicionario_sku_aprendido.json # Códigos aprendidos via UI (PP/MP/T/QQQQ/EE/CC/GG)
src/
  loaders/                      # Carregamento e concatenação de planilhas (multi-arquivo)
    magis_loader.py
    tiny_loader.py
    kits_loader.py              # Inclui enriquecimento de status de kits via produtos
  normalizers/
    normalizador.py             # Limpeza de texto, normalização de status/códigos
  matchers/
    sku_matcher.py              # Merge outer por SKU
    ean_matcher.py              # Match por EAN para sem-match de SKU
    similaridade_matcher.py     # Fuzzy match por título (rapidfuzz)
  comparators/
    comparador_produtos.py      # Pipeline: match → segmentação → filtro inativos → divergências
    comparador_kits.py          # Comparação de composição + separação por status
  validators/
    fiscal_validator.py         # Validação de NCM, CEST, Origem
    duplicidades.py             # Detecção de SKU/EAN duplicados por sistema
  sku/                          # Padronização de SKUs (padrão MEF PP-MPT-QQQQ-EECC-[GG])
    dicionario.py               # Load/merge oficial+aprendido + reverse-index
    parser.py                   # Quebra SKU em blocos (tolerante a variações)
    validator.py                # Classifica erro estrutural × semântico × incompleto
    corretor.py                 # Motor de sugestão a partir do título
    exportador.py               # Lista de renomeação + planilha Tiny 64 col. renomeada
  ui/
    aba_correcao_sku.py         # Aba "Correção de SKUs" (diagnóstico + edição + export)
    aba_dicionario_sku.py       # Aba "Dicionário SKU" (CRUD de códigos)
    componentes.py              # Cards de métricas, painel de saúde, downloads
  reports/
    exportador_tiny.py          # Planilhas de importação de produtos e kits no formato Tiny
    gerar_relatorios.py         # Relatório consolidado Excel multi-abas
```

### Configuração de colunas (`mapa_campos.yaml`)

Se um dos ERPs renomear uma coluna na exportação, basta atualizar o mapeamento correspondente em `config/mapa_campos.yaml` — nenhuma alteração no código é necessária.

---

## 🔄 Regras de negócio

### Produtos

| Classificação | Status | Ação sugerida |
|---|---|---|
| Presentes nos dois sistemas | ✅ OK | Nenhuma |
| Apenas no Magis (ativos) | → Ação | Importar no Tiny |
| Apenas no Tiny (ativos) | ⚠️ Alerta | Revisar |
| Divergência fiscal ou duplicidade | ✕ Erro | Corrigir antes de sincronizar |
| Inativos/Excluídos | — | Ignorados automaticamente |

### Kits

| Classificação | Status | Ação sugerida |
|---|---|---|
| Presentes nos dois (composição igual) | ✅ OK | Nenhuma |
| Apenas no Magis (ativos) | → Ação | Importar no Tiny |
| Apenas no Tiny (ativos) | ⚠️ Alerta | Revisar |
| Composição divergente | ✕ Erro | Corrigir composição |
| Inativos/Excluídos no Magis | — | Ignorados automaticamente |
| Status desconhecido | ℹ️ Info | Carregar planilha de produtos para classificar |

### Padrão de SKU (MEF) — `PP-MPT-QQQQ-EECC-[GG]`

Os SKUs da MEF Enxovais seguem a estrutura documentada no SOP SKU-01:

| Bloco | Tamanho | Descrição |
|---|---|---|
| **PP** | 2 chars | Produto (ex.: `AM` = Almofada de Amamentação, `FR` = Fralda, `KT` = Kit) |
| **MP** | 3 chars | Matéria-prima / acabamento (ex.: `POM`, `ALG`, `OVL`) — opcional |
| **T** | 1 char | Tamanho `G`/`M`/`P` — opcional |
| **QQQQ** | até 4 chars | Quantidade (`011U` = 11 unidades, `002A` = 2 anos, `05B5O` = 5 boca × 5 ombro, `6M18` = 6 a 18 meses, `ADUL`) |
| **EE** | 2 chars | Estampa (ex.: `BL` = Balão, `NV` = Nuvem) — opcional |
| **CC** | 2 chars | Cor (ex.: `AZ` = Azul, `RO` = Rosa) |
| **GG** | 2 chars | Gênero (`FM`/`MS`/`NT`) — obrigatório apenas para produtos sortidos |

**Classificação na aba Correção de SKUs:**

| Classificação | Status | Ação sugerida |
|---|---|---|
| SKU bate com o padrão e todos os códigos existem | ✅ Correto | Nenhuma |
| Estrutura quebrada (sem hífens, tamanho de bloco inválido) | ✕ Estrutural | Corrigir manualmente |
| Estrutura OK, mas algum código não está no dicionário | ✕ Semântico | Aprovar sugestão ou cadastrar o código novo |
| Sugestão com confiança < 60% | ⚠️ Ação manual | Revisar título e ajustar antes de aprovar |
