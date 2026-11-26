import argparse
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import urlsplit, urlunsplit

import requests

from app.core.constants import DOC_TYPES

# Configurações padrão (podem ser sobrescritas por env ou CLI)
DEFAULT_API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/documents/upload")
PASTA_DOCUMENTOS = os.getenv("PASTA_DOCUMENTOS", "./pautas_camara")


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


def _build_base_url(api_url: str) -> str:
    parts = urlsplit(api_url)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def verificar_api_disponivel(api_url: str) -> bool:
    """Valida /health antes de iniciar o lote (fail-fast contra porta errada ou servidor desligado)."""
    base_url = _build_base_url(api_url)
    health_url = f"{base_url}/health"
    try:
        resp = requests.get(health_url, timeout=5)
        if resp.status_code != 200:
            print(f"❌ [FALHA] '{health_url}' respondeu HTTP {resp.status_code} (esperado 200 do PublicGov-RAG).")
            print("   Verifique se outra aplicação (ex.: Laravel/Docker) está ocupando essa porta e passe --api-url.")
            return False
        payload = resp.json()
        if not isinstance(payload, dict) or "vector_backend" not in payload:
            print(f"❌ [FALHA] '{health_url}' não parece ser a API do PublicGov-RAG: {payload}")
            return False
        print(f"✅ API PublicGov-RAG online em {base_url} (LLM: {payload.get('llm_model')})")
        return True
    except requests.exceptions.RequestException as exc:
        print(f"❌ [FALHA] Não foi possível conectar em '{health_url}': {exc}")
        return False


def carregar_documentos_existentes(api_url: str) -> Set[str]:
    """Consulta GET /api/v1/documents/ para evitar re-upload de arquivos já indexados."""
    base_url = _build_base_url(api_url)
    docs_url = f"{base_url}/api/v1/documents/"
    try:
        resp = requests.get(docs_url, timeout=15)
        if resp.status_code == 200:
            items = resp.json()
            if isinstance(items, list):
                return {str(item.get("filename")) for item in items if item.get("filename")}
    except Exception as exc:
        print(f"⚠️ Não foi possível consultar documentos existentes ({exc}). Prosseguindo sem filtro.")
    return set()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload em lote de PDFs para o PublicGov-RAG.")
    parser.add_argument("default_doc_type", nargs="?", default="Pauta_Sessao", help="Tipo padrão para PDFs na raiz.")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="Endpoint completo de upload (ex.: http://127.0.0.1:8003/api/v1/documents/upload).")
    parser.add_argument("--pasta", default=PASTA_DOCUMENTOS, help="Pasta raiz contendo os PDFs ou subpastas doc_type.")
    parser.add_argument("--no-skip-existing", action="store_true", help="Reenvia arquivos mesmo que o filename já exista no catálogo.")
    parser.add_argument("--dry-run", action="store_true", help="Apenas valida a API e lista quantos arquivos seriam enviados.")
    return parser.parse_args()


def iniciar_upload_em_lote() -> None:
    args = parse_args()
    pasta_docs = args.pasta
    tipo_documento = args.default_doc_type
    api_url = args.api_url

    if not os.path.exists(pasta_docs):
        os.makedirs(pasta_docs)
        print(f"Pasta '{pasta_docs}' criada. Coloque seus PDFs nela e rode novamente.")
        return

    caminho_pasta = Path(pasta_docs)
    itens = descobrir_arquivos_para_upload(caminho_pasta, tipo_documento)

    if not itens:
        print(f"Nenhum arquivo .pdf encontrado em '{pasta_docs}' ou nas subpastas de doc_type.")
        return

    print(f"API alvo: {api_url}")
    if not verificar_api_disponivel(api_url):
        return

    existentes: Set[str] = set() if args.no_skip_existing else carregar_documentos_existentes(api_url)
    pendentes = [(p, dt) for (p, dt) in itens if p.name not in existentes]
    pulados = len(itens) - len(pendentes)

    print(f"Foram encontrados {len(itens)} documentos ({pulados} já indexados, {len(pendentes)} pendentes).")
    print(f"Tipo padrão para arquivos na raiz: '{tipo_documento}'")
    print(f"Categorias oficiais suportadas ({len(DOC_TYPES)}): {', '.join(DOC_TYPES)}")

    if args.dry_run or not pendentes:
        print("Modo dry-run ou nenhum arquivo pendente para envio.")
        return

    print("Iniciando indexação no RAG...\n")

    sucessos = 0
    erros = 0
    contagem_por_tipo: Dict[str, int] = {dt: 0 for dt in DOC_TYPES}

    for caminho_arquivo, doc_type in pendentes:
        nome_arquivo = caminho_arquivo.name
        print(f"Processando: {nome_arquivo} (doc_type={doc_type})...")

        with open(caminho_arquivo, "rb") as arquivo:
            files = {"file": (nome_arquivo, arquivo, "application/pdf")}
            data = {"doc_type": doc_type}

            try:
                resposta = requests.post(api_url, files=files, data=data, timeout=180)

                if resposta.status_code == 201:
                    dados_resposta = resposta.json()
                    chunks = dados_resposta.get("chunks_created", 0)
                    print(f"✅ [SUCESSO] Indexado! Gerou {chunks} fragmentos (chunks).")
                    sucessos += 1
                    contagem_por_tipo[doc_type] = contagem_por_tipo.get(doc_type, 0) + 1
                else:
                    print(f"❌ [ERRO] {resposta.status_code} - {resposta.text[:300]}")
                    erros += 1

            except requests.exceptions.ConnectionError:
                print("❌ [FALHA] Conexão perdida com o servidor FastAPI.")
                break
            except Exception as e:
                print(f"❌ [FALHA] Erro inesperado ao enviar {nome_arquivo}: {e}")
                erros += 1

    print(f"\nResumo da Operação: {sucessos} com sucesso | {erros} com erro | {pulados} já indexados.")
    print("Cobertura deste lote por doc_type:")
    for dt in DOC_TYPES:
        print(f"  - {dt}: {contagem_por_tipo.get(dt, 0)} arquivo(s)")


if __name__ == "__main__":
    iniciar_upload_em_lote()
