"""
dicionario.py
Carrega, persiste e consulta o dicionário de códigos de SKU.

Fontes:
  - config/dicionario_sku.yaml             (oficial, readonly pelo app)
  - config/dicionario_sku_aprendido.json   (aprendido via UI, editável)

O dicionário final é o merge dos dois (aprendido sobrescreve oficial se
houver conflito — por decisão do usuário).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

import yaml
from unidecode import unidecode

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
PATH_OFICIAL = CONFIG_DIR / "dicionario_sku.yaml"
PATH_APRENDIDO = CONFIG_DIR / "dicionario_sku_aprendido.json"

Bloco = Literal["PP", "MP", "T", "QQQQ", "EE", "CC", "GG"]
BLOCOS_EDITAVEIS: tuple[Bloco, ...] = ("PP", "MP", "T", "QQQQ", "EE", "CC", "GG")


def _normalizar_descricao(texto: str) -> str:
    """Uppercase + sem acentos — usado como chave reversa."""
    return unidecode(str(texto)).upper().strip()


def carregar_oficial() -> dict:
    with open(PATH_OFICIAL, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def carregar_aprendido() -> dict:
    if not PATH_APRENDIDO.exists():
        return {b: {} for b in BLOCOS_EDITAVEIS}
    with open(PATH_APRENDIDO, encoding="utf-8") as f:
        dados = json.load(f) or {}
    for b in BLOCOS_EDITAVEIS:
        dados.setdefault(b, {})
    return dados


def _salvar_aprendido(dados: dict) -> None:
    PATH_APRENDIDO.parent.mkdir(parents=True, exist_ok=True)
    with open(PATH_APRENDIDO, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2, sort_keys=True)


def carregar_dicionario() -> dict:
    """Retorna o dicionário consolidado (oficial + aprendido).

    Estrutura:
        {
          "PP": {"AM": "Almofada de Amamentação", ...},
          "MP": {...},
          ...
          "QQQQ": {
              "regex": [{"padrao": "...", "desc": "..."}, ...],
              "literais": {"ADUL": "Tamanho Adulto", ...},
          },
          "GG": {...},
        }
    """
    oficial = carregar_oficial()
    aprendido = carregar_aprendido()

    final: dict = {}
    for bloco in ("PP", "MP", "T", "EE", "CC", "GG"):
        final[bloco] = {**oficial.get(bloco, {}), **aprendido.get(bloco, {})}

    # QQQQ tem estrutura especial
    qqqq_oficial = oficial.get("QQQQ", {}) or {}
    qqqq_aprendido = aprendido.get("QQQQ", {}) or {}
    final["QQQQ"] = {
        "regex": list(qqqq_oficial.get("regex", [])),  # regex só no oficial
        "literais": {
            **(qqqq_oficial.get("literais", {}) or {}),
            **(qqqq_aprendido if isinstance(qqqq_aprendido, dict) else {}),
        },
    }
    return final


# ─────────────────────────────────────────────
# Reverse-index (descrição → código) para o corretor
# ─────────────────────────────────────────────

def construir_indice_reverso(dicionario: dict) -> dict[str, list[tuple[str, str]]]:
    """Para cada bloco, retorna lista de (descrição_normalizada, código),
    ordenada por tamanho decrescente da descrição — permite longest-match.
    """
    indice: dict[str, list[tuple[str, str]]] = {}
    for bloco in ("PP", "MP", "T", "EE", "CC", "GG"):
        pares = [
            (_normalizar_descricao(desc), cod)
            for cod, desc in dicionario.get(bloco, {}).items()
        ]
        # Para cada descrição, também decompor em termos alternativos (split por " / ")
        pares_expandidos: list[tuple[str, str]] = []
        vistos: set[str] = set()

        def _add(termo: str, codigo: str) -> None:
            termo = termo.strip()
            if termo and (termo, codigo) not in vistos:
                pares_expandidos.append((termo, codigo))
                vistos.add((termo, codigo))

        for desc, cod in pares:
            _add(desc, cod)
            # "REAL / REALEZA" → ["REAL", "REALEZA"] como alternativas
            for alt in desc.split(" / "):
                alt = alt.strip()
                if alt and alt != desc:
                    _add(alt, cod)
            # "COM POMPOM" → também tentar "POMPOM"
            if desc.startswith("COM "):
                _add(desc[4:], cod)
            # "ACABAMENTO EM VIES" → "EM VIES" e "VIES"
            if desc.startswith("ACABAMENTO EM "):
                _add(desc[14:], cod)
            if desc.startswith("ACABAMENTO "):
                _add(desc[11:], cod)
            # "ALMOFADA DE AMAMENTACAO" → também sem "DE" e só "AMAMENTACAO"
            if " DE " in desc:
                sem_de = desc.replace(" DE ", " ")
                _add(sem_de, cod)
                depois_de = desc.split(" DE ", 1)[1]
                _add(depois_de, cod)
            # "POLIESTER/MICROFIBRA" (sem espaço) → quebra por /
            if "/" in desc:
                for alt in desc.split("/"):
                    _add(alt.strip(), cod)
        # Ordena: mais longo primeiro, depois alfabético
        pares_expandidos.sort(key=lambda p: (-len(p[0]), p[0]))
        indice[bloco] = pares_expandidos
    return indice


# ─────────────────────────────────────────────
# CRUD do aprendido
# ─────────────────────────────────────────────

def adicionar_codigo(bloco: Bloco, codigo: str, descricao: str) -> None:
    """Persiste novo código no arquivo aprendido. Se bloco=QQQQ, vai em 'literais'."""
    if bloco not in BLOCOS_EDITAVEIS:
        raise ValueError(f"Bloco inválido: {bloco}")
    codigo = codigo.strip().upper()
    descricao = descricao.strip()
    if not codigo or not descricao:
        raise ValueError("Código e descrição são obrigatórios")

    dados = carregar_aprendido()
    if bloco == "QQQQ":
        # Literais de QQQQ ficam num dict achatado no arquivo aprendido
        dados.setdefault("QQQQ", {})[codigo] = descricao
    else:
        dados.setdefault(bloco, {})[codigo] = descricao
    _salvar_aprendido(dados)


def remover_codigo(bloco: Bloco, codigo: str) -> bool:
    """Remove um código do arquivo aprendido. Retorna True se removido."""
    dados = carregar_aprendido()
    codigo = codigo.strip().upper()
    if bloco in dados and codigo in dados[bloco]:
        del dados[bloco][codigo]
        _salvar_aprendido(dados)
        return True
    return False


def eh_oficial(bloco: Bloco, codigo: str) -> bool:
    """Retorna True se o código veio do YAML oficial (não pode ser removido pela UI)."""
    oficial = carregar_oficial()
    if bloco == "QQQQ":
        literais = (oficial.get("QQQQ", {}) or {}).get("literais", {}) or {}
        return codigo in literais
    return codigo in (oficial.get(bloco, {}) or {})


def validar_codigo_bloco(bloco: Bloco, codigo: str, dicionario: dict | None = None) -> bool:
    """Retorna True se o código é válido para o bloco (considerando oficial + aprendido)."""
    dic = dicionario or carregar_dicionario()
    if bloco == "QQQQ":
        if codigo in dic["QQQQ"]["literais"]:
            return True
        for regra in dic["QQQQ"]["regex"]:
            if re.fullmatch(regra["padrao"], codigo):
                return True
        return False
    if bloco == "T":
        # T aceita só G/M/P
        return codigo in dic.get("T", {})
    return codigo in dic.get(bloco, {})
