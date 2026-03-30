#!/usr/bin/env python3
"""
main.py
Script principal do comparador de produtos Magis 5 × Olist Tiny.

Uso:
    python main.py
    python main.py --magis data/input/raw_magis.xlsx --tiny data/input/raw_tiny.xlsx
    python main.py --magis data/input/raw_magis.xlsx --tiny data/input/raw_tiny.xlsx --output data/output/resultado.xlsx
"""

import argparse
import sys
from pathlib import Path

# Garante que o diretório raiz do projeto está no sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.loaders.magis_loader import carregar_magis
from src.loaders.tiny_loader import carregar_tiny
from src.normalizers.normalizador import normalizar_dataframe
from src.comparators.comparador_produtos import executar_comparacao
from src.reports.gerar_relatorios import gerar_excel, imprimir_resumo


def main():
    parser = argparse.ArgumentParser(
        description="Comparador de Produtos — Magis 5 × Olist Tiny",
    )
    parser.add_argument(
        "--magis",
        default=str(ROOT / "data" / "input" / "raw_magis.xlsx"),
        help="Caminho para o arquivo .xlsx do Magis (default: data/input/raw_magis.xlsx)",
    )
    parser.add_argument(
        "--tiny",
        default=str(ROOT / "data" / "input" / "raw_tiny.xlsx"),
        help="Caminho para o arquivo .xlsx do Tiny (default: data/input/raw_tiny.xlsx)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Caminho do arquivo Excel de saída (default: data/output/comparativo_<timestamp>.xlsx)",
    )
    args = parser.parse_args()

    # ──────────── 1. Carregar ────────────
    print("📂 Carregando planilha do Magis...")
    magis = carregar_magis(args.magis)
    print(f"   ✔ {len(magis)} registros carregados do Magis")

    print("📂 Carregando planilha do Tiny...")
    tiny = carregar_tiny(args.tiny)
    print(f"   ✔ {len(tiny)} registros carregados do Tiny")

    # ──────────── 2. Normalizar ────────────
    print("🔧 Normalizando dados do Magis...")
    magis = normalizar_dataframe(magis, sistema="magis")

    print("🔧 Normalizando dados do Tiny...")
    tiny = normalizar_dataframe(tiny, sistema="tiny")

    # ──────────── 3. Comparar ────────────
    print("⚙️  Executando comparação completa...")
    resultados = executar_comparacao(magis, tiny)

    # ──────────── 4. Relatório ────────────
    imprimir_resumo(resultados)

    caminho = gerar_excel(resultados, args.output)
    print(f"📊 Relatório gerado com sucesso: {caminho}")
    print("✅ Processo concluído!")


if __name__ == "__main__":
    main()
