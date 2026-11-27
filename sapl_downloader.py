"""Extrator e Downloader em Lote (Batch ETL) do SAPL para o PublicGov-RAG.

Analisa os endpoints REST do SAPL (Interlegis 3.1+), carrega dinamicamente as
tabelas de lookup (sem hardcode de IDs), classifica os documentos nas 8 categorias
oficiais (DOC_TYPES), valida assinatura PDF (%PDF-) e persiste um manifesto de
checkpoint para execuções incrementais e idempotentes.

Uso típico:
    python sapl_downloader.py --ano 2025 --dry-run
    python sapl_downloader.py --ano 2025 --sources all --workers 3
    python sapl_downloader.py --since 2026-11-01T00:00:00Z
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import logging
import os
import random
import re
import threading
import time
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin

import requests

from app.core.constants import DOC_TYPES

DEFAULT_SAPL_URL = os.getenv("SAPL_BASE_URL", "https://sapl.santanadolivramento.rs.leg.br")
DEFAULT_OUT_DIR = Path(os.getenv("PASTA_DOCUMENTOS", "./pautas_camara"))
MANIFEST_FILENAME = "sapl_manifest.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sapl_downloader")


# ---------------------------------------------------------------------------
# Utilitários de normalização e validação
# ---------------------------------------------------------------------------

def normalize_text(value: Optional[str]) -> str:
    """Remove acentos e converte para minúsculas para comparação segura."""
    if not value:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(value))
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_text.strip().lower()


def normalize_since_date(since: Optional[str]) -> Optional[str]:
    """Extrai YYYY-MM-DD de datas ISO, pois o DjangoFilter do SAPL rejeita timestamps com 'T'/'Z' (HTTP 500)."""
    if not since:
        return None
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", since.strip())
    if not match:
        raise ValueError(f"Formato inválido para --since '{since}'. Use YYYY-MM-DD.")
    return match.group(1)


def normalize_sapl_url(base_url: str, url_or_path: str) -> str:
    """Resolve URL relativa e preserva HTTPS quando base_url usa HTTPS (evita redirects http->https)."""
    resolved = url_or_path if url_or_path.startswith("http") else urljoin(f"{base_url.rstrip('/')}/", url_or_path.lstrip("/"))
    if base_url.startswith("https://") and resolved.startswith("http://"):
        base_host = base_url.split("://", 1)[1].split("/", 1)[0]
        if resolved.startswith(f"http://{base_host}"):
            resolved = "https://" + resolved[len("http://"):]
    return resolved


def sanitize_filename(name: str, max_len: int = 120) -> str:
    """Normaliza nome de arquivo mantendo caracteres seguros para filesystem."""
    cleaned = re.sub(r"[^\w.\-]+", "_", name.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "documento"
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    if len(cleaned) > max_len:
        stem = cleaned[:-4][: max_len - 4]
        cleaned = f"{stem}.pdf"
    return cleaned


# ---------------------------------------------------------------------------
# Cliente HTTP resiliente com backoff e paginação SAPL
# ---------------------------------------------------------------------------

class SaplClient:
    """Cliente HTTP para a API REST do SAPL com retry/backoff e controle de taxa."""

    RETRY_STATUSES = {429, 500, 502, 503, 504}

    def __init__(self, base_url: str, timeout: int = 30, delay_seconds: float = 0.25) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.delay_seconds = delay_seconds
        self._thread_local = threading.local()

    def _get_session(self) -> requests.Session:
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update(
                {
                    "Accept": "application/json",
                    "User-Agent": "PublicGov-RAG-SAPL-ETL/1.0",
                }
            )
            self._thread_local.session = session
        return session

    def request_with_retry(
        self,
        url_or_path: str,
        params: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        max_retries: int = 4,
    ) -> requests.Response:
        full_url = normalize_sapl_url(self.base_url, url_or_path)
        session = self._get_session()

        for attempt in range(max_retries + 1):
            if self.delay_seconds > 0:
                time.sleep(self.delay_seconds)
            try:
                resp = session.get(full_url, params=params, timeout=self.timeout, stream=stream)
                if resp.status_code not in self.RETRY_STATUSES:
                    resp.raise_for_status()
                    return resp

                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else (2 ** attempt) + random.uniform(0.1, 0.7)
                logger.warning("HTTP %s em %s — aguardando %.1fs (tentativa %d/%d)", resp.status_code, full_url, wait, attempt + 1, max_retries)
                resp.close()
                time.sleep(wait)
            except requests.RequestException as exc:
                if attempt >= max_retries:
                    raise
                wait = (2 ** attempt) + random.uniform(0.1, 0.7)
                logger.warning("Falha de rede em %s (%s) — retry em %.1fs", full_url, exc, wait)
                time.sleep(wait)

        raise RuntimeError(f"Excedido limite de tentativas para {full_url}")

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        resp = self.request_with_retry(path, params=params, stream=False)
        return resp.json()

    def fetch_lookup(self, path: str) -> Dict[int, Dict[str, Any]]:
        """Carrega tabela de lookup pequena com ?get_all=true e indexa por ID."""
        data = self.get_json(path, params={"get_all": "true"})
        items = data.get("results", data) if isinstance(data, dict) else data
        lookup: Dict[int, Dict[str, Any]] = {}
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and "id" in item:
                    lookup[int(item["id"])] = item
        return lookup

    def iter_paginated(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        max_pages: Optional[int] = None,
    ) -> Iterable[Dict[str, Any]]:
        """Itera sobre endpoints paginados do SAPL usando page_size=100 e ordenação o=id."""
        query = dict(params or {})
        query.setdefault("page_size", 100)
        query.setdefault("o", "id")

        next_url: Optional[str] = path
        next_params: Optional[Dict[str, Any]] = query
        page_num = 1

        while next_url:
            if max_pages is not None and page_num > max_pages:
                logger.info("Limite de páginas atingido (%d) em %s", max_pages, path)
                break

            payload = self.get_json(next_url, params=next_params)
            results = payload.get("results", []) if isinstance(payload, dict) else []
            for row in results:
                yield row

            pagination = payload.get("pagination", {}) if isinstance(payload, dict) else {}
            links = pagination.get("links", {}) if isinstance(pagination, dict) else {}
            next_url = links.get("next")
            next_params = None  # pagination.links.next já traz os query params
            page_num += 1


# ---------------------------------------------------------------------------
# Classificação e Modelos de Tarefa
# ---------------------------------------------------------------------------

@dataclass
class LookupCatalog:
    tipos_materia: Dict[int, Dict[str, Any]]
    tipos_documento_acessorio: Dict[int, Dict[str, Any]]
    tipos_norma: Dict[int, Dict[str, Any]]
    tipos_sessao: Dict[int, Dict[str, Any]]


@dataclass
class DownloadTask:
    source_endpoint: str
    record_id: int
    doc_type: str
    file_url: str
    filename: str
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def load_lookup_catalog(client: SaplClient) -> LookupCatalog:
    """Hidrata todas as lookup tables de tipos no início da execução."""
    logger.info("Carregando tabelas de lookup dinâmicas do SAPL...")
    return LookupCatalog(
        tipos_materia=client.fetch_lookup("/api/materia/tipomaterialegislativa/"),
        tipos_documento_acessorio=client.fetch_lookup("/api/materia/tipodocumento/"),
        tipos_norma=client.fetch_lookup("/api/norma/tiponormajuridica/"),
        tipos_sessao=client.fetch_lookup("/api/sessao/tiposessaoplenaria/"),
    )


def _extract_sigla_desc(lookup: Dict[int, Dict[str, Any]], tipo_id: Any) -> Tuple[str, str]:
    if tipo_id is None:
        return "", ""
    entry = lookup.get(int(tipo_id), {}) if str(tipo_id).isdigit() else {}
    sigla = normalize_text(entry.get("sigla"))
    desc = normalize_text(entry.get("descricao") or entry.get("nome"))
    return sigla, desc


def classify_materia(tipo_id: Any, catalog: LookupCatalog) -> str:
    """Classifica qualquer tipo de matéria legislativa do SAPL nas categorias oficiais."""
    sigla, desc = _extract_sigla_desc(catalog.tipos_materia, tipo_id)
    if (
        "mocao" in desc
        or "voto de congratulacao" in desc
        or "voto de pesar" in desc
        or sigla in {"moc", "mocao", "vc", "vp"}
    ):
        return "Mocao"
    if (
        "requerimento" in desc
        or "pedido de providencia" in desc
        or "pedido de informacao" in desc
        or "pedido de urgencia" in desc
        or "pedido de diligencia" in desc
        or "indicacao" in desc
        or "resp. pi" in desc
        or "resposta a pedido" in desc
        or sigla in {"req", "requerimento", "pedpr", "pin", "ind", "peddi", "pedur", "rpi", "rpp", "arpi"}
    ):
        return "Requerimento_Legislativo"
    if (
        "projeto" in desc
        or "emenda" in desc
        or "veto" in desc
        or "substitutivo" in desc
        or sigla in {"pl", "plo", "plc", "ple", "pll", "pdl", "pr", "emd", "sub", "vt", "antpr", "emimp"}
    ):
        return "Projeto_de_Lei"
    if "ordem do dia" in desc or sigla in {"od"}:
        return "Pauta_Sessao"
    if "parecer" in desc or sigla in {"par", "parecer"}:
        return "Parecer_Comissao"
    if "resolucao de mesa" in desc or sigla in {"rm", "resm"}:
        return "Lei_Municipal"
    return "Materia_Legislativa"


def classify_norma(row: Dict[str, Any], catalog: LookupCatalog) -> str:
    sigla, desc = _extract_sigla_desc(catalog.tipos_norma, row.get("tipo"))
    ementa_str = normalize_text(f"{row.get('__str__', '')} {row.get('ementa', '')}")

    # Verifica tipos dedicados ou fallback textual para LOM / Regimento Interno
    if (
        sigla in {"lom", "ri", "elom"}
        or "lei organica" in desc
        or "regimento interno" in desc
        or "lei organica" in ementa_str
        or "regimento interno" in ementa_str
    ):
        return "Regimento_e_LOM"
    return "Lei_Municipal"


def is_parecer_acessorio(row: Dict[str, Any], catalog: LookupCatalog) -> bool:
    sigla, desc = _extract_sigla_desc(catalog.tipos_documento_acessorio, row.get("tipo"))
    nome = normalize_text(row.get("nome"))
    return "parecer" in desc or "parecer" in nome or sigla == "par"


# ---------------------------------------------------------------------------
# Coletores por módulo SAPL
# ---------------------------------------------------------------------------

def collect_sessoes(
    client: SaplClient,
    ano: Optional[int],
    since: Optional[str],
    max_pages: Optional[int],
) -> List[DownloadTask]:
    params: Dict[str, Any] = {}
    if ano:
        params["data_inicio__year"] = ano
    if since:
        # SessaoPlenaria não possui campo data_ultima_atualizacao; filtra por data_inicio__gte
        params["data_inicio__gte"] = since

    tasks: List[DownloadTask] = []
    for row in client.iter_paginated("/api/sessao/sessaoplenaria/", params=params, max_pages=max_pages):
        rec_id = row.get("id")
        num = row.get("numero", "sn")
        data_ini = (row.get("data_inicio") or "sem_data")[:10]

        pauta_url = (row.get("upload_pauta") or "").strip()
        if pauta_url:
            tasks.append(
                DownloadTask(
                    source_endpoint="/api/sessao/sessaoplenaria/",
                    record_id=rec_id,
                    doc_type="Pauta_Sessao",
                    file_url=normalize_sapl_url(client.base_url, pauta_url),
                    filename=sanitize_filename(f"PAUTA_SESSAO_{rec_id}_N{num}_{data_ini}.pdf"),
                    metadata={"numero": num, "data_inicio": data_ini},
                )
            )

        ata_url = (row.get("upload_ata") or "").strip()
        if ata_url:
            tasks.append(
                DownloadTask(
                    source_endpoint="/api/sessao/sessaoplenaria/",
                    record_id=rec_id,
                    doc_type="Ata_Sessao",
                    file_url=normalize_sapl_url(client.base_url, ata_url),
                    filename=sanitize_filename(f"ATA_SESSAO_{rec_id}_N{num}_{data_ini}.pdf"),
                    metadata={"numero": num, "data_inicio": data_ini},
                )
            )
    return tasks


def collect_materias(
    client: SaplClient,
    catalog: LookupCatalog,
    ano: Optional[int],
    since: Optional[str],
    max_pages: Optional[int],
    unmapped_counter: Dict[str, int],
) -> List[DownloadTask]:
    params: Dict[str, Any] = {}
    if ano:
        params["ano"] = ano
    if since:
        params["data_ultima_atualizacao__gte"] = since

    tasks: List[DownloadTask] = []
    for row in client.iter_paginated("/api/materia/materialegislativa/", params=params, max_pages=max_pages):
        file_url = (row.get("texto_original") or "").strip()
        if not file_url:
            continue

        tipo_id = row.get("tipo")
        doc_type = classify_materia(tipo_id, catalog)
        if not doc_type:
            sigla, desc = _extract_sigla_desc(catalog.tipos_materia, tipo_id)
            key = f"{tipo_id}:{sigla}:{desc}"
            unmapped_counter[key] = unmapped_counter.get(key, 0) + 1
            continue

        rec_id = row.get("id")
        num = row.get("numero", "sn")
        ano_row = row.get("ano", "sa")
        sigla_raw = (catalog.tipos_materia.get(int(tipo_id), {}).get("sigla") or "MAT") if tipo_id else "MAT"

        tasks.append(
            DownloadTask(
                source_endpoint="/api/materia/materialegislativa/",
                record_id=rec_id,
                doc_type=doc_type,
                file_url=normalize_sapl_url(client.base_url, file_url),
                filename=sanitize_filename(f"{sigla_raw}_{num}_{ano_row}_id{rec_id}.pdf"),
                updated_at=row.get("data_ultima_atualizacao"),
                metadata={"tipo_id": tipo_id, "numero": num, "ano": ano_row},
            )
        )
    return tasks


def collect_normas(
    client: SaplClient,
    catalog: LookupCatalog,
    ano: Optional[int],
    since: Optional[str],
    max_pages: Optional[int],
) -> List[DownloadTask]:
    params: Dict[str, Any] = {}
    if ano:
        params["ano"] = ano
    if since:
        params["data_ultima_atualizacao__gte"] = since

    tasks: List[DownloadTask] = []
    for row in client.iter_paginated("/api/norma/normajuridica/", params=params, max_pages=max_pages):
        file_url = (row.get("texto_integral") or "").strip()
        if not file_url:
            continue

        doc_type = classify_norma(row, catalog)
        rec_id = row.get("id")
        num = row.get("numero", "sn")
        ano_row = row.get("ano", "sa")
        tipo_id = row.get("tipo")
        sigla_raw = (catalog.tipos_norma.get(int(tipo_id), {}).get("sigla") or "NORMA") if tipo_id else "NORMA"

        tasks.append(
            DownloadTask(
                source_endpoint="/api/norma/normajuridica/",
                record_id=rec_id,
                doc_type=doc_type,
                file_url=normalize_sapl_url(client.base_url, file_url),
                filename=sanitize_filename(f"{sigla_raw}_{num}_{ano_row}_id{rec_id}.pdf"),
                updated_at=row.get("data_ultima_atualizacao"),
                metadata={"origin_materia_id": row.get("materia"), "numero": str(num), "ano": ano_row},
            )
        )
    return tasks


def collect_pareceres(
    client: SaplClient,
    catalog: LookupCatalog,
    ano: Optional[int],
    since: Optional[str],
    max_pages: Optional[int],
) -> List[DownloadTask]:
    params: Dict[str, Any] = {}
    if ano:
        params["data__year"] = ano
    if since:
        params["data__gte"] = since

    tasks: List[DownloadTask] = []
    for row in client.iter_paginated("/api/materia/documentoacessorio/", params=params, max_pages=max_pages):
        file_url = (row.get("arquivo") or "").strip()
        if not file_url or not is_parecer_acessorio(row, catalog):
            continue

        rec_id = row.get("id")
        materia_id = row.get("materia", "sm")
        data_doc = (row.get("data") or "sd")[:10]
        tasks.append(
            DownloadTask(
                source_endpoint="/api/materia/documentoacessorio/",
                record_id=rec_id,
                doc_type="Parecer_Comissao",
                file_url=normalize_sapl_url(client.base_url, file_url),
                filename=sanitize_filename(f"PARECER_mat{materia_id}_{data_doc}_id{rec_id}.pdf"),
                updated_at=row.get("data_ultima_atualizacao"),
                metadata={"materia_id": materia_id},
            )
        )
    return tasks


# ---------------------------------------------------------------------------
# Manifesto de Checkpoint e Executor de Downloads
# ---------------------------------------------------------------------------

class DownloadManifest:
    """Persiste estado dos arquivos já baixados (sha256, etag, updated_at)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.entries: Dict[str, Dict[str, Any]] = {}
        if path.exists():
            try:
                self.entries = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Manifesto corrompido (%s), iniciando vazio: %s", path, exc)

    def should_skip(self, task: DownloadTask, dest_file: Path) -> bool:
        key = task.file_url
        with self._lock:
            entry = self.entries.get(key)
        if not entry:
            return False
        if entry.get("status") == "non_pdf":
            return True
        if dest_file.exists() and dest_file.stat().st_size > 0:
            if not task.updated_at or entry.get("updated_at") == task.updated_at:
                return True
        return False

    def record(self, key: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            self.entries[key] = payload

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self.path.write_text(json.dumps(self.entries, ensure_ascii=False, indent=2), encoding="utf-8")


def execute_download(
    client: SaplClient,
    task: DownloadTask,
    out_dir: Path,
    manifest: DownloadManifest,
) -> str:
    """Baixa um documento validando magic bytes %PDF-. Retorna status textual."""
    dest_file = out_dir / task.doc_type / task.filename
    if manifest.should_skip(task, dest_file):
        return "skipped_cached"

    dest_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = dest_file.with_suffix(".tmp")

    try:
        resp = client.request_with_retry(task.file_url, stream=True)
        content_type = (resp.headers.get("Content-Type") or "").lower()

        hasher = hashlib.sha256()
        first_chunk = b""
        total_bytes = 0

        with open(tmp_file, "wb") as f:
            for chunk in resp.iter_content(chunk_size=16384):
                if not chunk:
                    continue
                if not first_chunk:
                    first_chunk = chunk[:16]
                    if not first_chunk.startswith(b"%PDF-"):
                        resp.close()
                        tmp_file.unlink(missing_ok=True)
                        manifest.record(
                            task.file_url,
                            {
                                "status": "non_pdf",
                                "content_type": content_type,
                                "doc_type": task.doc_type,
                                "record_id": task.record_id,
                            },
                        )
                        return "skipped_non_pdf"
                hasher.update(chunk)
                f.write(chunk)
                total_bytes += len(chunk)

        if total_bytes == 0:
            tmp_file.unlink(missing_ok=True)
            return "error_empty"

        tmp_file.replace(dest_file)
        manifest.record(
            task.file_url,
            {
                "status": "downloaded",
                "doc_type": task.doc_type,
                "local_path": str(dest_file),
                "sha256": hasher.hexdigest(),
                "bytes": total_bytes,
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "updated_at": task.updated_at,
                "source_endpoint": task.source_endpoint,
                "record_id": task.record_id,
                "metadata": task.metadata or {},
            },
        )
        return "downloaded"
    except Exception as exc:
        tmp_file.unlink(missing_ok=True)
        logger.error("Erro ao baixar %s (%s): %s", task.filename, task.file_url, exc)
        return "error"


# ---------------------------------------------------------------------------
# Orquestração CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch downloader do SAPL para o PublicGov-RAG.")
    parser.add_argument("--base-url", default=DEFAULT_SAPL_URL, help="URL base do SAPL.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Diretório raiz de saída (compatível com batch_upload.py).")
    parser.add_argument("--ano", type=int, default=None, help="Filtrar por ano específico (ex.: 2025).")
    parser.add_argument("--since", type=str, default=None, help="Filtro incremental ISO (ex.: 2026-01-01T00:00:00Z).")
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["all"],
        choices=["all", "sessoes", "materias", "normas", "pareceres"],
        help="Módulos do SAPL a extrair.",
    )
    parser.add_argument("--max-pages", type=int, default=None, help="Limite de páginas (100 registros/pág) por endpoint.")
    parser.add_argument("--workers", type=int, default=3, help="Workers paralelos para download de PDFs (recomendado: 2-4).")
    parser.add_argument("--delay", type=float, default=0.25, help="Intervalo em segundos entre requisições HTTP por thread.")
    parser.add_argument("--dry-run", action="store_true", help="Apenas lista e contabiliza os documentos sem baixar PDFs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    since_date = normalize_since_date(args.since)
    sources = {"sessoes", "materias", "normas", "pareceres"} if "all" in args.sources else set(args.sources)

    client = SaplClient(base_url=args.base_url, delay_seconds=args.delay)
    catalog = load_lookup_catalog(client)

    all_tasks: List[DownloadTask] = []
    unmapped_materias: Dict[str, int] = {}

    if "sessoes" in sources:
        logger.info("Coletando Sessões Plenárias (Pautas e Atas)...")
        all_tasks.extend(collect_sessoes(client, args.ano, since_date, args.max_pages))
    if "materias" in sources:
        logger.info("Coletando Matérias Legislativas (PLs, Moções, Requerimentos)...")
        all_tasks.extend(collect_materias(client, catalog, args.ano, since_date, args.max_pages, unmapped_materias))
    if "normas" in sources:
        logger.info("Coletando Normas Jurídicas (Leis, LOM, Regimento)...")
        all_tasks.extend(collect_normas(client, catalog, args.ano, since_date, args.max_pages))
    if "pareceres" in sources:
        logger.info("Coletando Documentos Acessórios (Pareceres de Comissão)...")
        all_tasks.extend(collect_pareceres(client, catalog, args.ano, since_date, args.max_pages))

    by_type: Dict[str, int] = {dt: 0 for dt in DOC_TYPES}
    for t in all_tasks:
        by_type[t.doc_type] = by_type.get(t.doc_type, 0) + 1

    logger.info("Total de arquivos candidatos encontrados: %d", len(all_tasks))
    for dt in DOC_TYPES:
        logger.info("  - %-25s: %d", dt, by_type.get(dt, 0))

    if unmapped_materias:
        logger.warning("Tipos de matéria não mapeados (ignorados): %s", unmapped_materias)

    if args.dry_run or not all_tasks:
        logger.info("Modo dry-run ou lista vazia — nenhum download executado.")
        return

    manifest = DownloadManifest(args.out_dir / MANIFEST_FILENAME)
    stats: Dict[str, int] = {}

    logger.info("Iniciando downloads com %d worker(s)...", args.workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(execute_download, client, task, args.out_dir, manifest) for task in all_tasks]
        for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            status = future.result()
            stats[status] = stats.get(status, 0) + 1
            if idx % 25 == 0 or idx == len(all_tasks):
                manifest.save()
                logger.info("Progresso: %d/%d (%s)", idx, len(all_tasks), stats)

    manifest.save()
    logger.info("Concluído! Resumo final: %s", stats)
    logger.info("Próximo passo: execute `python batch_upload.py` para indexar no PublicGov-RAG.")


if __name__ == "__main__":
    main()
