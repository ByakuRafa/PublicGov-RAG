"""Constantes de domínio legislativo do PublicGov-RAG."""

from typing import Dict, Tuple

DOC_TYPES: Tuple[str, ...] = (
    "Pauta_Sessao",
    "Ata_Sessao",
    "Projeto_de_Lei",
    "Lei_Municipal",
    "Mocao",
    "Parecer_Comissao",
    "Requerimento_Legislativo",
    "Regimento_e_LOM",
)

DOC_TYPE_ALIASES: Dict[str, str] = {
    "Pauta_Legislativa": "Pauta_Sessao",
}
