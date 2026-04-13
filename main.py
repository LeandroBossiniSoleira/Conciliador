#!/usr/bin/env python3
"""
main.py
Script principal do comparador de produtos Magis 5 × Olist Tiny.

Uso:
    python main.py
    python main.py --magis data/input/raw_magis.xlsx --tiny data/input/raw_tiny.xlsx
    python main.py --magis FILE --tiny FILE --output data/output/resultado.xlsx
    python main.py --magis-kits FILE --tiny-kits FILE   (apenas kits)
    python main.py --magis FILE --tiny FILE --magis-kits FILE --tiny-kits FILE  (tudo)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# Garante que o diretório raiz do projeto está no sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.loaders.magis_loader import carregar_magis
from src.loaders.tiny_loader import carregar_tiny
from src.loaders.kits_loader import carregar_kits_magis, carregar_kits_tiny, enriquecer_status_kits
from src.normalizers.normalizador import normalizar_dataframe
from src.comparators.comparador_produtos import executar_comparacao
from src.comparators.comparador_kits import comparar_kits
from src.reports.gerar_relatorios import gerar_excel, imprimir_resumo
from src.reports.exportador_tiny import (
    gerar_planilha_importacao_produtos_tiny,
    gerar_planilha_importacao_tiny,
)


def main():
    parser = argparse.ArgumentParser(
        description="Comparador de Produtos e Kits — Magis 5 × Olist Tiny",
    )
    parser.add_argument(
        "--magis",
        default=None,
        help="Caminho para o arquivo .xlsx de Produtos do Magis",
    )
    parser.add_argument(
        "--tiny",
        default=None,
        help="Caminho para o arquivo .xlsx de Produtos do Tiny",
    )
    parser.add_argument(
        "--magis-kits",
        default=None,
        help="Caminho para o arquivo .xlsx de Kits do Magis",
    )
    parser.add_argument(
        "--tiny-kits",
        default=None,
        help="Caminho para o arquivo .xlsx de Kits do Tiny",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Caminho do arquivo Excel de saída (default: data/output/comparativo_<timestamp>.xlsx)",
    )
    parser.add_argument(
        "--export-importacao",
        default=None,
        help="Caminho para gerar planilha de importação de produtos no formato Tiny (64 colunas)",
    )
    args = parser.parse_args()

    tem_produtos = args.magis and args.tiny
    tem_kits = args.magis_kits and args.tiny_kits

    if not tem_produtos and not tem_kits:
        parser.error("Informe ao menos --magis/--tiny (produtos) ou --magis-kits/--tiny-kits (kits).")

    resultados: dict[str, pd.DataFrame] = {}
    magis_norm = None
    tiny_norm = None

    # ──────────── Produtos ────────────
    if tem_produtos:
        print("📂 Carregando planilha do Magis...")
        magis = carregar_magis(args.magis)
        print(f"   ✔ {len(magis)} registros carregados do Magis")

        print("📂 Carregando planilha do Tiny...")
        tiny = carregar_tiny(args.tiny)
        print(f"   ✔ {len(tiny)} registros carregados do Tiny")

        print("🔧 Normalizando dados...")
        magis_norm = normalizar_dataframe(magis, sistema="magis")
        tiny_norm = normalizar_dataframe(tiny, sistema="tiny")

        print("⚙️  Executando comparação de produtos...")
        resultados = executar_comparacao(magis_norm, tiny_norm)

        # Planilha de importação (produtos que faltam no Tiny)
        somente_magis = resultados.get("somente_magis", pd.DataFrame())
        if not somente_magis.empty and "sku" in somente_magis.columns:
            skus_importar = set(somente_magis["sku"].dropna().astype(str))
            df_para_importar = magis_norm[magis_norm["sku"].astype(str).isin(skus_importar)]
            if not df_para_importar.empty:
                df_imp_prod = gerar_planilha_importacao_produtos_tiny(df_para_importar)
                caminho_imp = args.export_importacao
                if caminho_imp is None:
                    output_dir = ROOT / "data" / "output"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    caminho_imp = str(output_dir / "importacao_produtos_tiny.xlsx")
                df_imp_prod.to_excel(caminho_imp, index=False)
                print(f"📥 Planilha de importação gerada: {caminho_imp}")

    # ──────────── Kits ────────────
    if tem_kits:
        print("📦 Carregando planilhas de Kits...")
        magis_kits_raw = carregar_kits_magis(args.magis_kits)
        print(f"   ✔ {len(magis_kits_raw)} registros de kits do Magis")

        if not magis_kits_raw.empty:
            magis_kits_raw = enriquecer_status_kits(magis_kits_raw, magis_norm)

        tiny_kits_raw = carregar_kits_tiny(args.tiny_kits)
        print(f"   ✔ {len(tiny_kits_raw)} registros de kits do Tiny")

        print("⚙️  Executando comparação de kits...")
        res_kits = comparar_kits(magis_kits_raw, tiny_kits_raw)

        resultados["kits_somente_magis"] = res_kits["somente_magis"]
        resultados["kits_somente_magis_inativos"] = res_kits.get("somente_magis_inativos", pd.DataFrame())
        resultados["kits_somente_magis_desconhecido"] = res_kits.get("somente_magis_desconhecido", pd.DataFrame())
        resultados["kits_somente_tiny"] = res_kits["somente_tiny"]
        resultados["kits_divergentes"] = res_kits["divergentes"]
        resultados["kits_nos_dois"] = res_kits.get("nos_dois", pd.DataFrame())

        # Gerar planilha de importação de kits
        df_import_kits, rejeitados, df_correcao, alertas = gerar_planilha_importacao_tiny(
            magis_kits_raw, res_kits["somente_magis"], tiny_norm
        )
        if not df_import_kits.empty:
            output_dir = ROOT / "data" / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            caminho_kits = str(output_dir / "importacao_kits_tiny.xlsx")
            df_import_kits.to_excel(caminho_kits, index=False)
            print(f"📥 Planilha de importação de kits: {caminho_kits}")

        if rejeitados:
            print(f"⚠️  {len(rejeitados)} kit(s) rejeitado(s):")
            for r in rejeitados:
                print(f"   - {r['sku_kit']}: {r['motivo']}")

        if alertas:
            print(f"🚨 {len(alertas)} produto(s) com tipo incorreto no Tiny:")
            for a in alertas:
                print(f"   - {a['sku']}: tipo atual={a['tipo_atual']}, esperado={a['tipo_esperado']}")
            if not df_correcao.empty:
                caminho_corr = str(output_dir / "correcao_tipos_tiny.xlsx")
                df_correcao.to_excel(caminho_corr, index=False)
                print(f"🔧 Planilha de correção de tipos: {caminho_corr}")

    # ──────────── Relatório ────────────
    imprimir_resumo(resultados)

    caminho = gerar_excel(resultados, args.output)
    print(f"📊 Relatório gerado com sucesso: {caminho}")
    print("✅ Processo concluído!")


if __name__ == "__main__":
    main()
