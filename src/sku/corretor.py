"""
corretor.py
Motor de sugestão de SKU a partir do título do produto.

Princípios:
  - Nunca inventa códigos: tudo vem do dicionário (oficial + aprendido).
  - Respeita a ordem oficial PP-MPT-QQQQ-EECC-[GG].
  - Blocos opcionais são de fato opcionais — não forçamos EE=LS nem T quando
    não há evidência no título.
  - Confiança = razão entre blocos identificados e blocos para os quais o
    título DAVA evidência (não penalizamos ausências legítimas).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from unidecode import unidecode

from src.normalizers.normalizador import limpar_texto
from src.sku.dicionario import carregar_dicionario, construir_indice_reverso

# Regex para match tolerante a plural/diminutivo (sufixos comuns em PT-BR)
_SUFIXO_VARIACAO = r"(?:S|ES|INHA|INHAS|INHO|INHOS|ZINHO|ZINHA)?"


def _norm(texto: str) -> str:
    return unidecode(str(texto)).upper()

TERMOS_KIT = ("KIT", "CONJUNTO", "COMBO")
# Quando o título tem vários produtos separados por "+", é sempre kit misto (PP=KT)
TERMOS_KIT_MISTO = ("+",)

# Regex de quantidade
_REGEX_MESES = re.compile(r"(\d{1,2})\s*(?:A|AO?)\s*(\d{1,2})\s*MESES?")
_REGEX_BOCA_OMBRO = re.compile(r"(\d{1,2})\s*BOCA\s*(\d{1,2})\s*OMBRO")
_REGEX_ADULTO = re.compile(r"\b(?:ADULTO?S?|TAMANHO\s*ADULTO)\b")
_REGEX_ANOS = re.compile(r"\b(\d{1,3})\s*ANOS?\b")
# "KIT 11 FRALDINHAS", "COM 11 UNIDADES", "2 PEÇAS", "Kit de 5 mantas"
_REGEX_QTD_UN = re.compile(
    r"\b(?:KIT\s*(?:DE\s*|COM\s*)?|COM\s*)?(\d{1,3})\s*"
    r"(?:UN|UNIDADES?|PECAS?|PECS?|ITENS?|FRALDINHAS?|FRALDAS?|MANTAS?|LENCOIS|NINHOS?|ALMOFADAS?)\b"
)


@dataclass
class Sugestao:
    pp: str | None = None
    mp: str | None = None
    t: str | None = None
    qqqq: str | None = None
    ee: str | None = None
    cc: str | None = None
    gg: str | None = None
    # Para cálculo de confiança: blocos onde o título DAVA evidência
    blocos_esperados: int = 0
    blocos_identificados: int = 0

    def montar_sku(self) -> str | None:
        if not self.pp:
            return None
        partes: list[str] = [self.pp]
        mpt = (self.mp or "") + (self.t or "")
        if mpt:
            partes.append(mpt)
        if self.qqqq:
            partes.append(self.qqqq)
        var = (self.ee or "") + (self.cc or "")
        if var:
            partes.append(var)
        sku = "-".join(partes)
        if self.gg:
            sku += self.gg
        return sku

    def confianca(self) -> int:
        if not self.pp:
            return 0
        if self.blocos_esperados == 0:
            return 80  # só PP — sugestão válida mas minimalista
        ratio = self.blocos_identificados / self.blocos_esperados
        # Piso 50 quando tem PP
        return max(50, min(100, int(ratio * 100)))


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _extrair_qqqq(texto: str, tem_kit: bool) -> tuple[str | None, bool]:
    """Retorna (codigo_qqqq_ou_None, titulo_tinha_pista_de_quantidade)."""
    # Faixa em meses (6M18)
    m = _REGEX_MESES.search(texto)
    if m:
        ini, fim = int(m.group(1)), int(m.group(2))
        if 0 <= ini <= 9 and 10 <= fim <= 99:
            return f"{ini}M{fim:02d}", True

    # Boca/Ombro (05B5O)
    m = _REGEX_BOCA_OMBRO.search(texto)
    if m:
        boca, ombro = int(m.group(1)), int(m.group(2))
        return f"{boca:02d}B{ombro}O", True

    # Adulto
    if _REGEX_ADULTO.search(texto):
        return "ADUL", True

    # Tamanho em anos (2A, 002A)
    m = _REGEX_ANOS.search(texto)
    if m:
        anos = int(m.group(1))
        if 0 <= anos <= 999:
            # Usar largura de 3 dígitos (padrão do PDF), mas aceitar menos
            return f"{anos:03d}A", True

    # Kit com N unidades
    m = _REGEX_QTD_UN.search(texto)
    if m:
        n = int(m.group(1))
        if n > 1:
            return f"{n:03d}U", True
        # Mesmo com n=1, o título tinha pista de quantidade
        return None, True

    return None, False


def _padroes_match(termo: str) -> list[str]:
    """Gera padrões regex para casar `termo` com variações de plural, diminutivo
    e troca de gênero (O↔A) quando aplicável.

    - FRALDA → FRALDA, FRALDAS, FRALDINHA, FRALDINHAS
    - FEMININO → FEMININO(S), FEMININA(S)
    - MASCULINO → MASCULINO(S), MASCULINA(S)
    """
    padroes = [rf"{re.escape(termo)}{_SUFIXO_VARIACAO}"]
    if len(termo) >= 4 and termo[-1] in "AO":
        # Troca O↔A para suportar variação de gênero
        alt = termo[:-1] + ("A" if termo[-1] == "O" else "O")
        padroes.append(rf"{re.escape(alt)}S?")
    if len(termo) >= 4 and termo[-1] in "AEIO":
        radical = termo[:-1]
        padroes.append(rf"{re.escape(radical)}(?:INHA|INHAS|INHO|INHOS|ZINHO|ZINHA)")
    return padroes


def _buscar_bloco(texto: str, bloco: str, indice: dict, ja_usado_spans: list[tuple[int, int]]) -> tuple[str | None, str | None, tuple[int, int] | None]:
    """Longest-match tolerante a plural/diminutivo."""
    for termo, codigo in indice.get(bloco, []):
        padrao_group = "|".join(_padroes_match(termo))
        pattern = rf"(?<![A-Z0-9])(?:{padrao_group})(?![A-Z0-9])"
        for m in re.finditer(pattern, texto):
            span = m.span()
            if any(span[0] < u[1] and u[0] < span[1] for u in ja_usado_spans):
                continue
            return codigo, termo, span
    return None, None, None


def _titulo_sugere_kit_misto(texto: str) -> bool:
    """True se o título indica múltiplos produtos diferentes (ex.: "Ninho + Almofada")."""
    return "+" in texto


def _titulo_sugere_kit(texto: str) -> bool:
    return any(re.search(rf"\b{t}\b", texto) for t in TERMOS_KIT)


def _titulo_sugere_sortido(texto: str) -> bool:
    return bool(re.search(r"\bSORTID[AO]S?\b", texto))


def _titulo_menciona_algum(texto: str, dic_bloco: dict, stopwords: set[str] | None = None) -> bool:
    """Heurística genérica: título menciona alguma palavra do dicionário do bloco.
    Aplica unidecode+upper na descrição para casar sem acento.
    """
    stopwords = stopwords or set()
    for _cod, desc in dic_bloco.items():
        for palavra in re.split(r"\s*/\s*| ", _norm(desc)):
            palavra = palavra.strip()
            if palavra in stopwords or len(palavra) < 3:
                continue
            if re.search(rf"\b{re.escape(palavra)}{_SUFIXO_VARIACAO}\b", texto):
                return True
    return False


def _titulo_sugere_estampa(texto: str, dic: dict) -> bool:
    return _titulo_menciona_algum(texto, dic.get("EE", {}))


def _titulo_sugere_cor(texto: str, dic: dict) -> bool:
    return _titulo_menciona_algum(texto, dic.get("CC", {}))


def _titulo_sugere_material(texto: str, dic: dict) -> bool:
    # Normaliza "Acabamento em Viés" → "ACABAMENTO EM VIES" → remove "EM"
    stopwords = {"COM", "E", "ACABAMENTO", "EM", "DE", "DO", "DA"}
    return _titulo_menciona_algum(texto, dic.get("MP", {}), stopwords)


def _titulo_sugere_tamanho(texto: str) -> bool:
    return bool(re.search(r"\bTAMANHO\s+(?:GRANDE|MEDIO|PEQUENO)\b|\bTAM\s+[GMP]\b", texto))


# ──────────────────────────────────────────────
# API
# ──────────────────────────────────────────────

def sugerir_sku(titulo: str | None, dic: dict | None = None, indice: dict | None = None) -> Sugestao:
    dic = dic or carregar_dicionario()
    indice = indice or construir_indice_reverso(dic)
    sug = Sugestao()

    texto = limpar_texto(titulo) or ""
    if not texto:
        return sug

    consumidos: list[tuple[int, int]] = []

    tem_kit = _titulo_sugere_kit(texto)
    tem_kit_misto = _titulo_sugere_kit_misto(texto)

    # ── PP ──
    # Sempre esperado
    sug.blocos_esperados += 1
    # Tenta PP específico a partir do dicionário primeiro
    cod_pp, termo_pp, span_pp = _buscar_bloco(texto, "PP", indice, consumidos)

    if tem_kit_misto:
        # Kit de produtos diferentes (tem "+") → PP=KT, ignorando PP específico
        sug.pp = "KT"
        sug.blocos_identificados += 1
    elif cod_pp:
        # Produto específico identificado: mantém — mesmo se título tem "KIT",
        # kits de um único produto (Kit N fraldinhas) usam PP do produto + QQQQ=NNNU
        sug.pp = cod_pp
        sug.blocos_identificados += 1
        if span_pp:
            consumidos.append(span_pp)
    elif tem_kit:
        # "Kit" mencionado mas sem PP específico → KT
        sug.pp = "KT"
        sug.blocos_identificados += 1

    # ── MP ──
    if _titulo_sugere_material(texto, dic):
        sug.blocos_esperados += 1
        cod, _termo, span = _buscar_bloco(texto, "MP", indice, consumidos)
        if cod:
            sug.mp = cod
            sug.blocos_identificados += 1
            if span:
                consumidos.append(span)

    # ── T ──
    if _titulo_sugere_tamanho(texto):
        sug.blocos_esperados += 1
        for codigo_t, desc_t in dic.get("T", {}).items():
            pad = rf"\bTAMANHO\s+{desc_t.upper()}\b|\bTAM\s+{codigo_t}\b"
            if re.search(pad, texto):
                sug.t = codigo_t
                sug.blocos_identificados += 1
                break

    # ── QQQQ ──
    qqqq, tinha_pista_qtd = _extrair_qqqq(texto, tem_kit)
    if tinha_pista_qtd or tem_kit:
        sug.blocos_esperados += 1
        if qqqq:
            sug.qqqq = qqqq
            sug.blocos_identificados += 1

    # ── EE ──
    if _titulo_sugere_estampa(texto, dic):
        sug.blocos_esperados += 1
        cod, _termo, span = _buscar_bloco(texto, "EE", indice, consumidos)
        # Nunca sugerir LS automaticamente
        if cod and cod != "LS":
            sug.ee = cod
            sug.blocos_identificados += 1
            if span:
                consumidos.append(span)

    # ── CC ──
    if _titulo_sugere_cor(texto, dic):
        sug.blocos_esperados += 1
        cod, _termo, span = _buscar_bloco(texto, "CC", indice, consumidos)
        if cod:
            sug.cc = cod
            sug.blocos_identificados += 1
            if span:
                consumidos.append(span)

    # ── GG (gênero) — só se título indicar sortido ──
    if _titulo_sugere_sortido(texto):
        sug.blocos_esperados += 1
        cod, _termo, span = _buscar_bloco(texto, "GG", indice, consumidos)
        if cod:
            sug.gg = cod
            sug.blocos_identificados += 1

    return sug
