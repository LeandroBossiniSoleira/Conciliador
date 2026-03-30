"""
gerar_relatorios.py
Exporta os resultados da comparação para um arquivo Excel
com múltiplas abas.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def gerar_excel(
    resultados: dict[str, pd.DataFrame],
    caminho_saida: str | None = None,
) -> str:
    """
    Gera um arquivo Excel com uma aba para cada resultado.

    Parameters
    ----------
    resultados : dict[str, pd.DataFrame]
        Dicionário retornado por `executar_comparacao()`.
    caminho_saida : str, optional
        Caminho completo do arquivo .xlsx de saída.
        Se não informado, gera em data/output/ com timestamp.

    Returns
    -------
    str
        Caminho do arquivo gerado.
    """
    if caminho_saida is None:
        output_dir = Path(__file__).resolve().parents[2] / "data" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho_saida = str(output_dir / f"comparativo_{timestamp}.xlsx")

    # Mapeamento de chaves → nome amigável na aba
    nomes_abas = {
        "comparativo_geral": "Comparativo Geral",
        "somente_magis": "Somente Magis",
        "somente_tiny": "Somente Tiny",
        "presente_nos_dois": "Nos Dois Sistemas",
        "divergencias_fiscais": "Divergências Fiscais",
        "duplicidades_sku_magis": "Dup SKU Magis",
        "duplicidades_ean_magis": "Dup EAN Magis",
        "duplicidades_sku_tiny": "Dup SKU Tiny",
        "duplicidades_ean_tiny": "Dup EAN Tiny",
        "sugestao_match_ean": "Sugestão Match EAN",
        "sugestao_match_titulo": "Sugestão Match Título",
        "erros_fiscais_magis": "Erros Fiscais Magis",
        "erros_fiscais_tiny": "Erros Fiscais Tiny",
        "kits_somente_magis": "Kits Somente Magis",
        "kits_somente_tiny": "Kits Somente Tiny",
        "kits_divergentes": "Kits Divergentes",
    }

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        for chave, nome_aba in nomes_abas.items():
            df = resultados.get(chave, pd.DataFrame())
            if df.empty:
                # Cria aba vazia com cabeçalho informativo
                pd.DataFrame({"info": ["Nenhum registro encontrado"]}).to_excel(
                    writer, sheet_name=nome_aba, index=False
                )
            else:
                # Trunca nome da aba para 31 chars (limite do Excel)
                df.to_excel(writer, sheet_name=nome_aba[:31], index=False)

    return caminho_saida


def gerar_resumo(resultados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Gera um DataFrame de resumo com contagens de cada categoria.

    Returns
    -------
    pd.DataFrame
        Colunas: categoria, quantidade
    """
    resumo = []

    for chave, df in resultados.items():
        resumo.append({"categoria": chave, "quantidade": len(df)})

    return pd.DataFrame(resumo)


def imprimir_resumo(resultados: dict[str, pd.DataFrame]) -> None:
    """Imprime um resumo formatado no console."""
    print("\n" + "=" * 60)
    print("  RESUMO DA COMPARAÇÃO MAGIS × TINY")
    print("=" * 60)

    labels = {
        "comparativo_geral": "Total comparativo geral",
        "somente_magis": "Somente Magis",
        "somente_tiny": "Somente Tiny",
        "presente_nos_dois": "Presente nos dois sistemas",
        "divergencias_fiscais": "Divergências fiscais",
        "duplicidades_sku_magis": "Duplicidades SKU (Magis)",
        "duplicidades_ean_magis": "Duplicidades EAN (Magis)",
        "duplicidades_sku_tiny": "Duplicidades SKU (Tiny)",
        "duplicidades_ean_tiny": "Duplicidades EAN (Tiny)",
        "sugestao_match_ean": "Sugestões match por EAN",
        "sugestao_match_titulo": "Sugestões match por título",
        "erros_fiscais_magis": "Erros fiscais (Magis)",
        "erros_fiscais_tiny": "Erros fiscais (Tiny)",
    }

    for chave, label in labels.items():
        df = resultados.get(chave, pd.DataFrame())
        print(f"  {label:<40} {len(df):>6}")

    print("=" * 60 + "\n")
