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
    "Materia_Legislativa",
    "Regimento_e_LOM",
)

MATERIA_LEGISLATIVA_TYPES: Tuple[str, ...] = (
    "Projeto_de_Lei",
    "Parecer_Comissao",
    "Mocao",
    "Requerimento_Legislativo",
    "Materia_Legislativa",
)

OUTROS_DOCUMENTOS_TYPES: Tuple[str, ...] = (
    "Pauta_Sessao",
    "Ata_Sessao",
    "Lei_Municipal",
    "Regimento_e_LOM",
)

DOC_TYPE_ALIASES: Dict[str, str] = {
    "Pauta_Legislativa": "Pauta_Sessao",
}
