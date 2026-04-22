"""
parser.py
Parser tolerante que quebra um SKU na estrutura oficial
PP-MPT-QQQQ-EECC-[GG].

Estratégia: conta hífens para decidir a forma, depois sub-parseia cada bloco
com validação contra o dicionário (os tamanhos sozinhos não são suficientes
porque há ambiguidade entre códigos de mesmo tamanho em blocos diferentes).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.sku.dicionario import carregar_dicionario, validar_codigo_bloco


@dataclass
class ParsedSKU:
    sku_original: str
    pp: str | None = None
    mp: str | None = None
    t: str | None = None
    qqqq: str | None = None
    ee: str | None = None
    cc: str | None = None
    gg: str | None = None
    # Diagnóstico
    erros_estruturais: list[str] = field(default_factory=list)
    blocos_invalidos: list[str] = field(default_factory=list)  # ex.: ["PP=XX", "EE=ZZ"]
    bloco_nao_reconhecido: str | None = None  # segmento que o parser não conseguiu classificar

    @property
    def tem_erro_estrutural(self) -> bool:
        return bool(self.erros_estruturais)

    @property
    def tem_erro_semantico(self) -> bool:
        return bool(self.blocos_invalidos) or bool(self.bloco_nao_reconhecido)

    def reconstruir(self) -> str:
        """Remonta o SKU na ordem oficial, a partir dos blocos parseados (debug)."""
        partes: list[str] = []
        if self.pp:
            partes.append(self.pp)
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


# ──────────────────────────────────────────────
# Sub-parsers
# ──────────────────────────────────────────────

def _parsear_mpt(segmento: str, dic: dict) -> tuple[str | None, str | None, bool]:
    """Tenta parsear MP (3 chars) + T opcional (1 char). Retorna (mp, t, ok)."""
    seg = segmento.upper()
    if len(seg) == 3:
        if validar_codigo_bloco("MP", seg, dic):
            return seg, None, True
        return seg, None, False
    if len(seg) == 4:
        mp, t = seg[:3], seg[3]
        ok_mp = validar_codigo_bloco("MP", mp, dic)
        ok_t = validar_codigo_bloco("T", t, dic)
        return mp, t, (ok_mp and ok_t)
    # Tamanho inválido
    return seg, None, False


def _parsear_qqqq(segmento: str, dic: dict) -> tuple[str, bool]:
    seg = segmento.upper()
    return seg, validar_codigo_bloco("QQQQ", seg, dic)


def _parsear_var(segmento: str, dic: dict) -> tuple[str | None, str | None, str | None, list[str]]:
    """Parseia variação EE+CC (+GG opcional).

    Tamanhos esperados:
        2 = só CC (ou só EE)
        4 = EE+CC
        6 = EE+CC+GG

    Retorna (ee, cc, gg, problemas).
    """
    seg = segmento.upper()
    problemas: list[str] = []

    if len(seg) == 2:
        # Pode ser só cor (TR-NVAZ tem AZ como CC, mas lá são 4 chars NVAZ)
        # Casos puros de 2 chars: ambiguidade CC vs EE.
        if validar_codigo_bloco("CC", seg, dic):
            return None, seg, None, []
        if validar_codigo_bloco("EE", seg, dic):
            return seg, None, None, []
        problemas.append(f"VAR={seg} não é CC nem EE válido")
        return None, None, None, problemas

    if len(seg) == 4:
        ee, cc = seg[:2], seg[2:]
        if not validar_codigo_bloco("EE", ee, dic):
            problemas.append(f"EE={ee} inválido")
        if not validar_codigo_bloco("CC", cc, dic):
            problemas.append(f"CC={cc} inválido")
        return ee, cc, None, problemas

    if len(seg) == 6:
        ee, cc, gg = seg[:2], seg[2:4], seg[4:]
        if not validar_codigo_bloco("EE", ee, dic):
            problemas.append(f"EE={ee} inválido")
        if not validar_codigo_bloco("CC", cc, dic):
            problemas.append(f"CC={cc} inválido")
        if not validar_codigo_bloco("GG", gg, dic):
            problemas.append(f"GG={gg} inválido")
        return ee, cc, gg, problemas

    problemas.append(f"Variação de tamanho inválido ({len(seg)} chars): {seg}")
    return None, None, None, problemas


# ──────────────────────────────────────────────
# Parser principal
# ──────────────────────────────────────────────

def parsear_sku(sku: str, dic: dict | None = None) -> ParsedSKU:
    """Quebra o SKU em blocos. Não tenta corrigir — só diagnostica."""
    dic = dic or carregar_dicionario()
    bruto = (sku or "").strip().upper()
    resultado = ParsedSKU(sku_original=sku or "")

    if not bruto:
        resultado.erros_estruturais.append("SKU vazio")
        return resultado

    partes = bruto.split("-")
    n_hifens = len(partes) - 1

    # PP sempre é o primeiro bloco
    pp = partes[0]
    if len(pp) != 2:
        resultado.erros_estruturais.append(f"PP deve ter 2 caracteres, recebeu {len(pp)}: '{pp}'")
    resultado.pp = pp
    if pp and not validar_codigo_bloco("PP", pp, dic):
        resultado.blocos_invalidos.append(f"PP={pp}")

    if n_hifens == 0:
        resultado.erros_estruturais.append(
            "SKU sem delimitadores '-' — estrutura não reconhecível"
        )
        return resultado

    if n_hifens == 1:
        # PP-VAR
        var = partes[1]
        ee, cc, gg, probs = _parsear_var(var, dic)
        resultado.ee = ee
        resultado.cc = cc
        resultado.gg = gg
        resultado.blocos_invalidos.extend(probs)
        return resultado

    if n_hifens == 2:
        # Dois casos possíveis: PP-MPT-VAR  ou  PP-QQQQ-VAR
        # Tenta QQQQ primeiro (match estrito via regex/literal); se falhar, cai em MPT.
        qqqq_candidato, ok_qqqq = _parsear_qqqq(partes[1], dic)
        if ok_qqqq:
            resultado.qqqq = qqqq_candidato
        else:
            mp, t, ok_mpt = _parsear_mpt(partes[1], dic)
            resultado.mp = mp
            resultado.t = t
            if not ok_mpt:
                if len(partes[1]) not in (3, 4):
                    resultado.erros_estruturais.append(
                        f"Bloco intermediário deve ter 3 ou 4 chars, recebeu {len(partes[1])}: '{partes[1]}'"
                    )
                if mp and not validar_codigo_bloco("MP", mp, dic):
                    resultado.blocos_invalidos.append(f"MP={mp}")
                if t and not validar_codigo_bloco("T", t, dic):
                    resultado.blocos_invalidos.append(f"T={t}")

        ee, cc, gg, probs = _parsear_var(partes[2], dic)
        resultado.ee = ee
        resultado.cc = cc
        resultado.gg = gg
        resultado.blocos_invalidos.extend(probs)
        return resultado

    if n_hifens == 3:
        # PP-MPT-QQQQ-VAR
        mp, t, ok_mpt = _parsear_mpt(partes[1], dic)
        resultado.mp = mp
        resultado.t = t
        if not ok_mpt:
            if mp and not validar_codigo_bloco("MP", mp, dic):
                resultado.blocos_invalidos.append(f"MP={mp}")
            if t and not validar_codigo_bloco("T", t, dic):
                resultado.blocos_invalidos.append(f"T={t}")

        qqqq, ok_qqqq = _parsear_qqqq(partes[2], dic)
        resultado.qqqq = qqqq
        if not ok_qqqq:
            resultado.blocos_invalidos.append(f"QQQQ={qqqq}")

        ee, cc, gg, probs = _parsear_var(partes[3], dic)
        resultado.ee = ee
        resultado.cc = cc
        resultado.gg = gg
        resultado.blocos_invalidos.extend(probs)
        return resultado

    # 4+ hífens → estrutura desconhecida
    resultado.erros_estruturais.append(
        f"SKU com {n_hifens} hífens — padrão aceita no máximo 3"
    )
    resultado.bloco_nao_reconhecido = bruto
    return resultado


def eh_valido(sku: str, dic: dict | None = None) -> bool:
    """Helper: True se o SKU está perfeitamente alinhado ao padrão."""
    parsed = parsear_sku(sku, dic)
    return not parsed.tem_erro_estrutural and not parsed.tem_erro_semantico
