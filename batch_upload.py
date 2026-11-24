import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import requests

from app.core.constants import DOC_TYPES

# Configurações
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/documents/upload")
PASTA_DOCUMENTOS = os.getenv("PASTA_DOCUMENTOS", "./pautas_camara")
# Permite passar o tipo de documento padrão para PDFs na raiz da pasta
TIPO_DOCUMENTO = sys.argv[1] if len(sys.argv) > 1 else "Pauta_Sessao"


def descobrir_arquivos_para_upload(
    base_dir: Path,
    default_doc_type: str,
) -> List[Tuple[Path, str]]:
    """Descobre PDFs na raiz (usando default_doc_type) e em subpastas nomeadas pelas 8 categorias DOC_TYPES."""
    itens: List[Tuple[Path, str]] = []

    for pdf in sorted(base_dir.glob("*.pdf")):
        itens.append((pdf, default_doc_type))

    for category in DOC_TYPES:
        subpasta = base_dir / category
        if subpasta.is_dir():
            for pdf in sorted(subpasta.glob("*.pdf")):
                itens.append((pdf, category))

    return itens


def iniciar_upload_em_lote() -> None:
    if not os.path.exists(PASTA_DOCUMENTOS):
        os.makedirs(PASTA_DOCUMENTOS)
        print(f"Pasta '{PASTA_DOCUMENTOS}' criada. Coloque seus PDFs nela e rode novamente.")
        return

    caminho_pasta = Path(PASTA_DOCUMENTOS)
    itens = descobrir_arquivos_para_upload(caminho_pasta, TIPO_DOCUMENTO)

    if not itens:
        print(f"Nenhum arquivo .pdf encontrado em '{PASTA_DOCUMENTOS}' ou nas subpastas de doc_type.")
        return

    print(f"Foram encontrados {len(itens)} documentos.")
    print(f"Tipo padrão para arquivos na raiz: '{TIPO_DOCUMENTO}'")
    print(f"Categorias oficiais suportadas ({len(DOC_TYPES)}): {', '.join(DOC_TYPES)}")
    print("Iniciando indexação no RAG...\n")

    sucessos = 0
    erros = 0
    contagem_por_tipo: Dict[str, int] = {dt: 0 for dt in DOC_TYPES}

    for caminho_arquivo, doc_type in itens:
        nome_arquivo = caminho_arquivo.name
        print(f"Processando: {nome_arquivo} (doc_type={doc_type})...")

        with open(caminho_arquivo, "rb") as arquivo:
            files = {"file": (nome_arquivo, arquivo, "application/pdf")}
            data = {"doc_type": doc_type}

            try:
                resposta = requests.post(API_URL, files=files, data=data, timeout=120)

                if resposta.status_code == 201:
                    dados_resposta = resposta.json()
                    chunks = dados_resposta.get("chunks_created", 0)
                    print(f"✅ [SUCESSO] Indexado! Gerou {chunks} fragmentos (chunks).")
                    sucessos += 1
                    contagem_por_tipo[doc_type] = contagem_por_tipo.get(doc_type, 0) + 1
                else:
                    print(f"❌ [ERRO] {resposta.status_code} - {resposta.text}")
                    erros += 1

            except requests.exceptions.ConnectionError:
                print("❌ [FALHA] Não foi possível conectar. O servidor do FastAPI (Uvicorn) está rodando?")
                break
            except Exception as e:
                print(f"❌ [FALHA] Erro inesperado ao enviar {nome_arquivo}: {e}")
                erros += 1

    print(f"\nResumo da Operação: {sucessos} com sucesso | {erros} com erro.")
    print("Cobertura deste lote por doc_type:")
    for dt in DOC_TYPES:
        print(f"  - {dt}: {contagem_por_tipo.get(dt, 0)} arquivo(s)")


if __name__ == "__main__":
    iniciar_upload_em_lote()
