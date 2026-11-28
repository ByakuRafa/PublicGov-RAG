# PublicGov-RAG — Legislação e Matérias Legislativas

### Sistema RAG Agêntico de Apoio ao Cidadão e ao Servidor Público
**Câmara Municipal de Vereadores de Santana do Livramento — RS**

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API%20%2B%20Workbench-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic%20RAG-1C3C3C)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL%2016-pgvector-336791?logo=postgresql&logoColor=white)
![MCP](https://img.shields.io/badge/FastMCP-HTTP%20%26%20stdio-6B4FBB)
![Evals](https://img.shields.io/badge/Evals-RAGAS%20%2B%20Golden%20Dataset-orange)

---

## 📑 Sumário

1. [Visão Geral e Propósito](#%EF%B8%8F-1-vis%C3%A3o-geral-e-prop%C3%B3sito)
2. [Delimitação Estrita de Escopo](#-2-delimita%C3%A7%C3%A3o-estrita-de-escopo)
3. [Categorias Documentais (`doc_type`) e Pipeline OCR](#-3-categorias-documentais-doc_type-e-pipeline-ocr)
4. [Arquitetura da Solução](#%EF%B8%8F-4-arquitetura-da-solu%C3%A7%C3%A3o)
5. [Instalação e Configuração](#-5-instala%C3%A7%C3%A3o-e-configura%C3%A7%C3%A3o)
6. [Workbench Web de Observabilidade & Experimentação](#%EF%B8%8F-6-workbench-web-de-observabilidade--experimenta%C3%A7%C3%A3o)
7. [Coleta SAPL (ETL) e Indexação de Documentos](#-7-coleta-sapl-etl-e-indexa%C3%A7%C3%A3o-de-documentos)
8. [Consultas, Endpoints da API e Servidor MCP](#-8-consultas-endpoints-da-api-e-servidor-mcp)
9. [Evals Automatizadas, Benchmark de Embeddings e Testes](#-9-evals-automatizadas-benchmark-de-embeddings-e-testes)
10. [Estrutura do Repositório](#-10-estrutura-do-reposit%C3%B3rio)
11. [Governança, Auditoria e Melhores Práticas](#-11-governan%C3%A7a-auditoria-e-melhores-pr%C3%A1ticas)

---

## 🏛️ 1. Visão Geral e Propósito

O **PublicGov-RAG** é uma plataforma de Inteligência Artificial baseada na arquitetura **RAG Agêntico (*Retrieval-Augmented Generation*)**, desenvolvida para facilitar, democratizar e auditar o acesso à informação pública legislativa da **Câmara Municipal de Vereadores de Santana do Livramento (RS)**.

O sistema integra coleta automatizada via API REST do **SAPL (Sistema de Apoio ao Processo Legislativo)**, extração híbrida de PDFs com **fallback automático para OCR em português**, **busca híbrida** (vetorial no `pgvector` + lexical `BM25` com tokenização legislativa + *Reciprocal Rank Fusion* + *Cross-Encoder Reranking*), orquestração multi-ferramenta via **LangGraph**, **Workbench Web** integrado, servidor **MCP (*Model Context Protocol*)**, telemetria de custos/latência e suíte automatizada de **Evals** com **RAGAS**.

O projeto atende a dois públicos principais:

1. **Cidadãos Santanenses**: Compreender de forma clara, didática e rastreável as leis municipais, direitos, deveres, matérias em votação no plenário, moções, requerimentos e a atuação dos vereadores, sempre com indicação explícita dos arquivos oficiais de origem.
2. **Servidores Públicos e Assessores Parlamentares**: Realizar pesquisas técnicas com celeridade, localizando precedentes regimentais, redações de projetos de lei, pareceres de comissões, justificativas jurídicas e dispositivos da Lei Orgânica ou do Regimento Interno.

---

## 🎯 2. Delimitação Estrita de Escopo

Para garantir confiabilidade factual, bloqueio de alucinações e aderência institucional, o agente (`AGENT_PROMPT_V2`) opera sob uma **fronteira de escopo estrita**:

### ✅ O que ESTÁ no escopo (Legislação e Processo Legislativo)
* **Atos Normativos e Leis Municipais**: Lei Orgânica do Município (LOM), Leis Ordinárias, Leis Complementares e Resoluções de Mesa promulgadas/sancionadas.
* **Proposições Legislativas**: Projetos de Lei Ordinária (PLO), Projetos de Lei Complementar (PLC), Projetos de Decreto Legislativo (PDL), Projetos de Resolução (PR), Emendas, Substitutivos e Vetos.
* **Pautas e Ordens do Dia das Sessões**: Documentos oficiais que detalham o Expediente, matérias para deliberação e projetos em discussão/votação nas sessões plenárias.
* **Atas e Registros de Votação**: Atas de sessões plenárias com registro de presenças, discussões em tribuna, votações nominais e desfecho das matérias.
* **Instrumentos de Fiscalização e Manifestação Parlamentar**:
  * **Moções** (Apoio, Pesar, Repúdio, Congratulação e Reconhecimento);
  * **Requerimentos Oficiais**, **Pedidos de Providência / Informação / Urgência / Diligência** e **Indicações Legislativas**.
* **Pareceres Técnicos das Comissões**: Análises de constitucionalidade, legalidade, redação e adequação orçamentária emitidas pelas comissões permanentes.
* **Demais Matérias e Expedientes Legislativos**: Ofícios, mensagens, recursos, convites e documentos acessórios vinculados à tramitação (`Materia_Legislativa`).
* **Regramento Institucional**: Regimento Interno da Câmara (ex.: Resolução nº 1.252/2016) e Lei Orgânica do Município.

### ❌ O que NÃO ESTÁ no escopo (Exclusões Deliberadas e Abstenção Obrigatória)
* **Rotinas e Gestão Administrativa Interna da Câmara**: Folha de pagamento, diárias de viagem, controle de ponto, cronograma de férias de servidores, licitações de suprimentos internos e portarias de RH.
* **Atos Administrativos do Poder Executivo (Prefeitura)**: Decretos exclusivos do prefeito, cobrança tributária, recursos contra autuações de trânsito, editais de concursos e licitações da Prefeitura — *exceto* quando objeto direto de proposição ou deliberação na Câmara.
* **Demandas Judiciais ou de Órgãos Externos**: Processos judiciais ou decisões de tribunais externos fora do acervo legislativo municipal.

> Quando uma pergunta está fora de escopo ou não possui evidência suficiente nos trechos recuperados, o agente é instruído a **abster-se explicitamente**, informando a ausência nos registros indexados sem especular nem citar arquivos indevidamente.

---

## 📄 3. Categorias Documentais (`doc_type`) e Pipeline OCR

O domínio legislativo está estruturado em **9 categorias oficiais** definidas em [`app/core/constants.py`](app/core/constants.py) (`DOC_TYPES`):

| `doc_type` (Metadado) | Categoria | Conteúdo Típico e Estrutura | Uso Principal |
| :--- | :--- | :--- | :--- |
| `Pauta_Sessao` | **Pauta das Sessões Plenárias** | Convocação, Ordem do Dia, lista de proposições para votação, regime de urgência e leitura de expedientes. *(Aceita o alias `Pauta_Legislativa` em consultas.)* | Acompanhar o que será deliberado nas sessões plenárias. |
| `Ata_Sessao` | **Ata de Sessão Plenária** | Registro de presenças/ausências, falas em tribuna, votações nominais e resultado das deliberações. | Transparência histórica sobre votos e posicionamento dos vereadores. |
| `Projeto_de_Lei` | **Projetos de Lei e Proposições** | Ementa, texto articulado, justificativa do autor, emendas, substitutivos, vetos e impacto financeiro/social (PLO, PLC, PDL, PR, PELOM). | Analisar novas propostas de regras municipais e embasar pareceres. |
| `Lei_Municipal` | **Leis e Normas Promulgadas** | Texto legal consolidado, vigência, revogações e Resoluções de Mesa. | Base de consulta sobre normas e direitos vigentes no município. |
| `Mocao` | **Moções Parlamentares** | Moções de Apoio, Pesar, Repúdio, Congratulação ou Reconhecimento, fundamentadas no Regimento Interno. | Entender manifestações políticas e institucionais da Câmara. |
| `Parecer_Comissao` | **Pareceres de Comissões** | Pareceres técnicos e documentos acessórios de análise jurídica, constitucionalidade e mérito. | Subsidiar segurança jurídica antes da votação em plenário. |
| `Requerimento_Legislativo` | **Requerimentos e Indicações** | Requerimentos, Pedidos de Providência, Pedidos de Informação, Pedidos de Urgência/Diligência e Indicações ao Executivo. | Fiscalização da gestão pública municipal e demandas de bairros/serviços. |
| `Materia_Legislativa` | **Outras Matérias Legislativas** | Ofícios, mensagens, recursos, convites e demais expedientes legislativos classificados fora das categorias específicas. | Cobertura integral do acervo protocolado no processo legislativo. |
| `Regimento_e_LOM` | **Lei Orgânica e Regimento Interno** | Lei Orgânica Municipal (LOM) e Regimento Interno (Resolução nº 1.252/2016 e alterações). | Consulta de ritos processuais, quóruns, prazos e competências. |

### 🔍 Pipeline Híbrida de Extração de PDFs (Texto Nativo + OCR)
Documentos legislativos históricos ou assinados fisicamente frequentemente chegam como PDFs escaneados sem camada de texto selecionável. Em [`app/services/pdf_service.py`](app/services/pdf_service.py), o sistema aplica extração em duas camadas:

1. **Extração Nativa Rápida (`PyPDFLoader`)**: Lê todas as páginas do PDF e considera válidas aquelas com mais de `30` caracteres úteis.
2. **Fallback Automático via OCR (`Poppler` + `Tesseract`)**: Se nenhuma página possuir texto nativo suficiente, o PDF é renderizado em imagens via `pdf2image` (`convert_from_path`) e processado página a página com `pytesseract` configurado com idioma português (`lang="por"`).
3. **Chunking & Indexação**: Os trechos extraídos recebem os metadados `doc_type`, `source_file` e `page`, são segmentados com `RecursiveCharacterTextSplitter` (`chunk_size=1000`, `chunk_overlap=150`), indexados no **PostgreSQL + `pgvector`** e invalidam automaticamente o cache em memória do índice lexical **BM25**.

---

## 🏗️ 4. Arquitetura da Solução

```mermaid
flowchart TD
    subgraph ETL ["1. Coleta SAPL & Pipeline de Ingestão"]
        S[SAPL Interlegis REST API] -->|sapl_downloader.py| P[PDFs classificados em 9 doc_types<br/>+ sapl_manifest.json]
        P -->|batch_upload.py| API_UP[POST /api/v1/documents/upload]
        UI_UP[Workbench Web / Swagger] --> API_UP
        API_UP --> B{PDF possui texto<br/>nativo > 30 chars/pág?}
        B -- Sim --> C[PyPDFLoader]
        B -- Não / Escaneado --> D[pdf2image Poppler +<br/>Tesseract OCR lang='por']
        C --> E[Metadados: doc_type, source_file, page]
        D --> E
        E --> F[RecursiveCharacterTextSplitter<br/>chunk_size: 1000 | overlap: 150]
        F --> G[Embedding Factory<br/>MiniLM-L12-v2 ou EmbeddingGemma 2 MRL]
        G --> H[(PostgreSQL 16 + pgvector<br/>Coleções isoladas por modelo/dim)]
        E --> I[(PostgreSQL DocumentModel)]
    end

    subgraph Query ["2. Agente LangGraph, Busca Híbrida, MCP & Observabilidade"]
        U1[Workbench Web /] --> AG
        U2[REST POST /api/v1/query/ask] --> AG
        U3[MCP Server /mcp ou stdio] --> AG
        AG[Agente LangGraph - Prompt v2<br/>MAX_TOOL_ROUNDS = 3] --> T1[consultar_legislacao_municipal]
        AG --> T2[consultar_pautas_e_votacoes]
        AG --> T3[listar_documentos_indexados]
        AG --> T4[pedir_esclarecimento_ao_cidadao]
        T1 & T2 --> V1[Busca Vetorial pgvector]
        T1 & T2 --> V2[Busca Lexical BM25Okapi<br/>Tokenização legislativa]
        H -.-> V1
        H -.-> V2
        V1 & V2 --> RRF[Reciprocal Rank Fusion - RRF k=60]
        RRF --> RR[Cross-Encoder Reranker<br/>FlashRank ms-marco-MultiBERT-L-12]
        RR --> LLM[ChatGoogleGenerativeAI<br/>gemini-2.5-flash | temp=0.1]
        LLM --> RES[Resposta Fundamentada + sources<br/>+ tools_used + tokens + custo USD]
        RES --> LOG[(PostgreSQL QueryLogModel)]
        AG -. Callbacks .-> LF[Langfuse Observability]
    end
```

### Principais Componentes

* **API REST, Workbench Web & Servidor MCP** ([`app/main.py`](app/main.py), [`app/mcp_server.py`](app/mcp_server.py)):
  * **FastAPI** com validação via **Pydantic V2** (incluindo sanitização automática de placeholders do Swagger como `"string"`/`"null"` e normalização de aliases em [`app/schemas/query.py`](app/schemas/query.py)).
  * **Workbench Web** servido diretamente em `GET /` ([`app/static/index.html`](app/static/index.html) e [`app/static/app.js`](app/static/app.js)).
  * **Servidor MCP** via **FastMCP**, montado em `/mcp` (HTTP Streamable) e executável via `stdio` (`python -m app.mcp_server`).
* **Agente LangGraph & Controle de Ferramentas** ([`app/services/agent_service.py`](app/services/agent_service.py)):
  * Suporta duas versões de prompt (`v1` simples e `v2` restritivo — padrão em produção) para experimentação e comparação controlada.
  * Roteia entre 4 ferramentas: `consultar_legislacao_municipal`, `consultar_pautas_e_votacoes`, `listar_documentos_indexados` e `pedir_esclarecimento_ao_cidadao`, com fallback automático para busca ampla no acervo caso o filtro por grupo não retorne trechos.
  * Limite de segurança `MAX_TOOL_ROUNDS = 3` (e `recursion_limit = 12`): ao atingir o teto, força resposta final sem chamadas adicionais de ferramentas.
* **Busca Híbrida & Reranking** ([`app/services/retrieval_service.py`](app/services/retrieval_service.py)):
  * **Busca Vetorial (`pgvector`)** combinada com **Busca Lexical (`BM25Okapi`)** usando tokenização específica para identificadores legislativos (ex.: `67/2025`, `1.252/2016`), com cache em memória invalidado a cada novo upload.
  * Fusão via **Reciprocal Rank Fusion (RRF)** (`rrf_k=60`) seguida de reordenação semântica com **Cross-Encoder FlashRank** (`ms-marco-MultiBERT-L-12`, configurável via `ENABLE_RERANKER`).
* **Fábrica de Embeddings Configurável** ([`app/services/embedding_factory.py`](app/services/embedding_factory.py)):
  * Padrão leve: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões).
  * Opcional de alta precisão: `google/embeddinggemma-2` com *Task-Steered Prompts* (`Document` / `SearchQuery`) e truncamento **Matryoshka (MRL)** em `128`, `256`, `512` ou `768` dimensões.
  * Coleções isoladas automaticamente no `pgvector` por modelo e dimensão via `sanitize_collection_name` (ex.: `publicgov_paraphrase_multilingual_minilm_l12_v2` ou `publicgov_embeddinggemma_2_d256`).
* **Banco Relacional, Telemetria e Observabilidade** ([`app/db/models.py`](app/db/models.py), [`app/core/telemetry.py`](app/core/telemetry.py), [`app/core/observability.py`](app/core/observability.py)):
  * **PostgreSQL 16 + `pgvector`** armazena embeddings (`langchain_pg_*`), catálogo de documentos (`documents`) e logs de auditoria (`query_logs`).
  * Migração segura automática (`ensure_query_logs_schema`) adiciona colunas de telemetria (`latency_ms`, `prompt_tokens`, `completion_tokens`, `estimated_cost_usd`) sem perda de dados.
  * Integração opcional com **Langfuse** (Cloud ou self-hosted via Docker profile).

---

## 🚀 5. Instalação e Configuração

### Opção A: Executando via Docker Compose (Recomendado)

O `Dockerfile` ([`.dockerfile`](.dockerfile)) já instala Python 3.12, PyTorch CPU, **Poppler** e **Tesseract OCR (`tesseract-ocr-por`)**, e o [`docker-compose.yml`](docker-compose.yml) orquestra a API e o PostgreSQL 16 com `pgvector`:

1. Clone o repositório e acesse a pasta:
   ```bash
   git clone <URL_DO_REPOSITORIO>
   cd PublicGov-RAG
   ```

2. Crie o arquivo `.env` a partir do modelo:
   ```bash
   cp .env.example .env
   ```
   Preencha ao menos `GOOGLE_API_KEY` com sua chave do Google AI Studio.

3. Suba os serviços principais (`db` + `api`):
   ```bash
   docker compose up -d --build
   ```

4. *(Opcional)* Suba também o **Langfuse self-hosted** em `http://localhost:3000`:
   ```bash
   docker compose --profile langfuse up -d --build
   ```
   Em seguida, crie um projeto no painel do Langfuse, preencha `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e `LANGFUSE_HOST=http://localhost:3000` no `.env` e reinicie o container `api`:
   ```bash
   docker compose restart api
   ```

Interfaces disponíveis após subir os containers:
* **Workbench Web**: `http://localhost:8000/`
* **Swagger UI**: `http://localhost:8000/docs`
* **Health Check**: `http://localhost:8000/health`
* **MCP Streamable HTTP**: `http://localhost:8000/mcp`
* **Langfuse** *(se habilitado)*: `http://localhost:3000`

---

### Opção B: Executando no Ambiente Local

#### 1. Pré-requisitos do Sistema
* **Python 3.10+** (recomendado Python 3.12).
* **PostgreSQL 16 com extensão `pgvector`** ativo e acessível via `DATABASE_URL` (você pode subir apenas o banco via Docker com `docker compose up -d db`).
* **Poppler Utilities e Tesseract OCR (Português)**:
  * *Linux (Ubuntu/Debian)*:
    ```bash
    sudo apt update && sudo apt install -y poppler-utils tesseract-ocr tesseract-ocr-por
    ```
  * *Windows*: Instale o Poppler para Windows e o Tesseract OCR (incluindo o pacote de idioma `por.traineddata`), adicionando ambos ao `PATH`.

#### 2. Ambiente Virtual e Dependências
```bash
python -m venv venv

# Linux / macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

pip install -r requirements.txt
```

#### 3. Configuração do `.env` e Inicialização
```bash
cp .env.example .env
# Edite o .env e defina GOOGLE_API_KEY e DATABASE_URL

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### ⚙️ Variáveis de Ambiente

Todas as configurações da aplicação são carregadas via Pydantic Settings em [`app/core/config.py`](app/core/config.py):

| Variável | Padrão | Descrição |
| :--- | :--- | :--- |
| `GOOGLE_API_KEY` | `""` *(obrigatória)* | Chave da API do Google Gemini (Google AI Studio). |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Modelo Gemini utilizado pelo agente LangGraph. |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/publicgov` | String de conexão PostgreSQL + `pgvector`. |
| `UPLOAD_DIR` | `./storage/uploads` | Diretório local onde os PDFs enviados via API são armazenados. |
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embeddings (ex.: `google/embeddinggemma-2`). |
| `EMBEDDING_DIM` | `None` | Truncamento Matryoshka para `google/embeddinggemma-2` (`128`, `256`, `512` ou `768`). |
| `HF_TOKEN` | `""` | Token do HuggingFace para modelos *gated* (necessário para `google/embeddinggemma-2`). |
| `RETRIEVAL_TOP_K` | `10` | Quantidade de candidatos recuperados por etapa (vetorial / BM25 / RRF). |
| `RERANK_TOP_N` | `4` | Quantidade final de trechos retornados após o reranking. |
| `ENABLE_RERANKER` | `true` | Habilita ou desabilita o Cross-Encoder Reranker (FlashRank). |
| `RERANKER_MODEL` | `ms-marco-MultiBERT-L-12` | Modelo utilizado pelo `flashrank.Ranker`. |
| `LANGFUSE_PUBLIC_KEY` | `""` | Chave pública do Langfuse (deixe vazio para desativar). |
| `LANGFUSE_SECRET_KEY` | `""` | Chave secreta do Langfuse. |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Host do Langfuse (`http://localhost:3000` para Docker local). |
| `LLM_INPUT_COST_PER_1M_USD` | `None` | Override opcional do preço por 1M de tokens de entrada (USD). |
| `LLM_OUTPUT_COST_PER_1M_USD` | `None` | Override opcional do preço por 1M de tokens de saída (USD). |

**Variáveis auxiliares para scripts de ETL, upload e Evals:**
* `SAPL_BASE_URL` (padrão `https://sapl.santanadolivramento.rs.leg.br`) — URL base usada pelo `sapl_downloader.py`.
* `PASTA_DOCUMENTOS` (padrão `./pautas_camara`) — pasta de saída do `sapl_downloader.py` e entrada do `batch_upload.py`.
* `API_URL` (padrão `http://127.0.0.1:8000/api/v1/documents/upload`) — endpoint alvo do `batch_upload.py`.
* `EVAL_JUDGE_MODEL` (padrão igual a `GEMINI_MODEL`) — modelo LLM juiz usado pelo RAGAS em `evals/run_eval.py`.

---

## 🖥️ 6. Workbench Web de Observabilidade & Experimentação

Ao iniciar a API, acesse **`http://localhost:8000/`** para utilizar o **Workbench Web** ([`app/static/index.html`](app/static/index.html)), uma interface em tema escuro dividida em 3 abas e barra de status persistente:

* **Barra de Status (`/health`)**: Exibe status da API em tempo real, versão, modelo LLM ativo, modelo/dimensão de embedding, backend vetorial (`pgvector`), estado do Langfuse e atalhos para `/docs` e Langfuse.
* **1. Playground RAG**:
  * Envio de perguntas (`Ctrl+Enter` / `Cmd+Enter`) com filtro opcional `doc_type_filter`.
  * **Presets de Teste Rápido** (consultas legislativas, Regimento/LOM, Projetos de Lei e teste de abstenção fora de escopo).
  * Renderização segura em Markdown (`marked` + `DOMPurify`), badges de `tools_used` e `sources`, exibição de latência (servidor e cliente), tokens, custo estimado, JSON bruto colapsável e **histórico da sessão atual** para comparação lado a lado.
* **2. Documentos & Ingestão**:
  * Upload direto de PDFs com escolha de `doc_type` e cronômetro de processamento/OCR.
  * **Grid de Cobertura** exibindo a contagem de arquivos em cada uma das **9 categorias** `doc_type` (destacando categorias vazias).
  * Tabela pesquisável e filtrável de todos os documentos indexados no PostgreSQL.
* **3. Telemetria & Auditoria**:
  * KPIs consolidados (`/api/v1/query/metrics`): total de consultas, latência média, tokens (prompt/completion) e custo estimado total em USD.
  * Tabela pesquisável do histórico persistido (`/api/v1/query/history`), com linhas expansíveis exibindo pergunta, resposta renderizada e metadados JSON completos.

---

## 📥 7. Coleta SAPL (ETL) e Indexação de Documentos

### 7.1 Coleta Automatizada da API REST do SAPL (`sapl_downloader.py`)

O script [`sapl_downloader.py`](sapl_downloader.py) extrai documentos diretamente do **SAPL (Interlegis 3.1+)** de Santana do Livramento (ou qualquer outra Câmara compatível via `--base-url`), hidrata dinamicamente as tabelas de tipos (sem IDs hardcoded), classifica os arquivos nas **9 categorias oficiais (`DOC_TYPES`)**, valida a assinatura binária `%PDF-` + hash `SHA-256` e mantém um manifesto incremental (`pautas_camara/sapl_manifest.json`) para execuções idempotentes.

```bash
# 1. Simular coleta do ano de 2025 (apenas contabiliza por doc_type, sem baixar)
python sapl_downloader.py --ano 2025 --dry-run

# 2. Baixar de todos os módulos (sessoes, materias, normas, pareceres) com 3 workers
python sapl_downloader.py --ano 2025 --sources all --workers 3

# 3. Coleta incremental a partir de uma data (normaliza ISO para YYYY-MM-DD)
python sapl_downloader.py --since 2026-01-01T00:00:00Z --sources materias sessoes

# 4. Limitar páginas durante testes (100 registros por página)
python sapl_downloader.py --ano 2026 --max-pages 2 --delay 0.25
```

Os arquivos são gravados automaticamente em subpastas de categoria dentro de `./pautas_camara/<doc_type>/`, no formato exato esperado pelo `batch_upload.py`.

---

### 7.2 Indexação em Lote (`batch_upload.py`)

O script [`batch_upload.py`](batch_upload.py) descobre PDFs tanto na raiz de `pautas_camara/` (atribuindo `default_doc_type`, padrão `Pauta_Sessao`) quanto nas 9 subpastas nomeadas com cada `doc_type`. Antes de iniciar o envio, ele valida `/health` (*fail-fast*) e consulta `GET /api/v1/documents/` para **pular arquivos já indexados**.

```bash
# Visualizar o que será enviado sem fazer upload
python batch_upload.py --dry-run

# Enviar todos os PDFs pendentes de ./pautas_camara/
python batch_upload.py

# Apontar para outra URL/pasta e forçar reenvio mesmo se filename já existir
python batch_upload.py Projeto_de_Lei \
  --api-url http://127.0.0.1:8000/api/v1/documents/upload \
  --pasta ./pautas_camara \
  --no-skip-existing
```

---

### 7.3 Indexação Individual via API

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@storage/uploads/4429.pdf" \
  -F "doc_type=Mocao"
```

---

## 💬 8. Consultas, Endpoints da API e Servidor MCP

### Exemplo de Consulta via REST (`POST /api/v1/query/ask`)

```bash
curl -X POST "http://localhost:8000/api/v1/query/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual é a justificativa da Moção de Apoio referente ao teto do MEI?",
    "doc_type_filter": "Mocao"
  }'
```

#### Exemplo de Resposta (`QueryResponse`):
```json
{
  "question": "Qual é a justificativa da Moção de Apoio referente ao teto do MEI?",
  "answer": "A Moção de Apoio nº 02/2025 ao Projeto de Lei Complementar nº 67/2025 justifica que o número de MEIs no Brasil dobrou entre 2018 e 2025, mas o teto anual de faturamento de R$ 81 mil, fixado desde 2018, encontra-se defasado pela inflação, podendo estimular o subfaturamento e limitar o crescimento de pequenos negócios.\n\nFonte: 4429.pdf",
  "sources": [
    "4429.pdf"
  ],
  "tools_used": [
    "consultar_pautas_e_votacoes"
  ],
  "latency_ms": 2845.12,
  "prompt_tokens": 1840,
  "completion_tokens": 118,
  "estimated_cost_usd": 0.000347
}
```

### Mapa Completo de Endpoints

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/` | Workbench Web de Observabilidade & Experimentação (Playground, Ingestão e Telemetria). |
| `GET` | `/health` | Saúde da API, versão, `llm_model`, `embedding_model`, `embedding_dim`, `vector_backend` e `langfuse_enabled`. |
| `GET` | `/api/v1/documents/` | Lista todos os documentos catalogados no PostgreSQL (`id`, `filename`, `doc_type`, `chunks_count`, `uploaded_at`). |
| `POST` | `/api/v1/documents/upload` | Recebe PDF (`multipart/form-data`), extrai texto (com OCR fallback), faz chunking, indexa no `pgvector` e invalida cache BM25. |
| `POST` | `/api/v1/query/ask` | Executa o agente LangGraph com busca híbrida + reranking, persiste log e retorna resposta com fontes e telemetria. |
| `GET` | `/api/v1/query/history?limit=10` | Histórico de auditoria (`QueryLogModel`) ordenado do mais recente para o mais antigo. |
| `GET` | `/api/v1/query/metrics` | Telemetria agregada: `total_queries`, `avg_latency_ms`, `total_prompt_tokens`, `total_completion_tokens` e `total_estimated_cost_usd`. |
| `ALL` | `/mcp` | Endpoint HTTP/Streamable do servidor **MCP** (`FastMCP`). |
| `GET` | `/docs` | Documentação interativa OpenAPI / Swagger UI. |

### Integração via MCP (Model Context Protocol)

O servidor MCP expõe **4 ferramentas** em [`app/mcp_server.py`](app/mcp_server.py):
* `consultar_legislacao_municipal(consulta, top_k=4)`
* `consultar_pautas_e_votacoes(consulta, top_k=4)`
* `listar_documentos_camara()`
* `perguntar_oraculo_legislativo(pergunta, doc_type_filter=None)`

**Via HTTP Streamable** (com a API rodando): conecte seu cliente MCP em `http://localhost:8000/mcp`.

**Via `stdio`** (Claude Desktop, Cursor, etc.):
```bash
python -m app.mcp_server
```
Exemplo de configuração em clientes MCP (`stdio`):
```json
{
  "mcpServers": {
    "publicgov-rag": {
      "command": "/caminho/para/PublicGov-RAG/venv/bin/python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/caminho/para/PublicGov-RAG"
    }
  }
}
```

---

## 🧪 9. Evals Automatizadas, Benchmark de Embeddings e Testes

### 9.1 Suíte de Evals Comparativas (`evals/run_eval.py`)

O arquivo [`evals/golden_dataset.json`](evals/golden_dataset.json) reúne **30 perguntas reais** (25 respondíveis baseadas no acervo de Santana do Livramento + 5 sem resposta ou fora de escopo para aferir abstenção e bloqueio de falsa citação):

```bash
# 1. Verificar cobertura atual das 9 categorias doc_type no PostgreSQL
python -m evals.run_eval --coverage-only

# 2. Comparar Prompt v1 (simples) vs. Prompt v2 (restritivo) com métricas RAGAS
python -m evals.run_eval --prompts v1 v2

# 3. Rodar apenas métricas determinísticas (Recall@4, precisão de citação e abstenção) sem juiz RAGAS
python -m evals.run_eval --prompts v1 v2 --skip-ragas

# 4. Rodar amostra reduzida com dataset customizado
python -m evals.run_eval --prompts v2 --limit 10 --dataset evals/golden_dataset.json
```

Os relatórios são gerados automaticamente em [`evals/results/latest_report.json`](evals/results/latest_report.json) e [`evals/results/prompt_comparison.md`](evals/results/prompt_comparison.md).

#### Resultados Registrados — Comparativo `v1` vs. `v2` (`evals/results/prompt_comparison.md`)
*Snapshot registrado com **308 documentos indexados** no PostgreSQL (6/9 categorias `doc_type`: `Pauta_Sessao`, `Projeto_de_Lei`, `Mocao`, `Parecer_Comissao`, `Requerimento_Legislativo`, `Regimento_e_LOM`; ausentes no momento dessa coleta: `Ata_Sessao`, `Lei_Municipal`, `Materia_Legislativa`), utilizando `gemini-3.5-flash-lite` e `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` sobre as 30 perguntas do `golden_dataset.json`:*

| Versão Prompt | Faithfulness (RAGAS) | Answer Relevancy | Source Recall@4 | Explicit Citation Recall | Precisão Citação de Fontes | Abstenção (Sem Resposta) | Latência Média (ms) | Tokens (In/Out) | Custo Total (USD) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `v1` | `66.97%` | `62.71%` | `96.00%` | `24.00%` | `36.67%` | `80.00%` | `9820.0` | `170758 / 6863` | `$0.019822` |
| `v2` | `65.00%` | `53.65%` | `92.00%` | `76.00%` | `72.50%` | `80.00%` | `8221.8` | `176865 / 5717` | `$0.019973` |

> **Destaque**: A adoção do prompt `v2` elevou a **citação explícita de arquivos fonte** de `24.00%` para `76.00%` e praticamente dobrou a **precisão na citação de fontes** (`36.67%` → `72.50%`), mantendo `80.00%` de abstenção adequada e reduzindo a latência média em ~`1.6 s` por consulta.

---

### 9.2 Benchmark de Embeddings e Estratégias de Retrieval (`evals/benchmark_embeddings.py`)

Permite comparar estratégias (`vector_only`, `hybrid_rrf`, `hybrid_rrf_rerank`) e candidatos de embedding (`minilm`, `gemma-768`, `gemma-256` MRL) em coleções isoladas no `pgvector`:

```bash
# Benchmark com MiniLM usando evals/sample_corpus.json e recriando coleção de teste
python -m evals.benchmark_embeddings --models minilm --reindex

# Comparar MiniLM vs EmbeddingGemma 2 (requer HF_TOKEN e aceite de licença no HuggingFace)
python -m evals.benchmark_embeddings --models minilm gemma-768 gemma-256 --from-db --reindex
```

#### Resultados Registrados — Estratégias de Retrieval (`evals/results/benchmark_embeddings.md`)

| Embedding | Modo de Busca | Recall@4 | MRR@4 | Latência Média (ms) | Indexação (s) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `MiniLM-L12-v2 (384d)` | `vector_only` | `80.00%` | `0.7056` | `40.0` | `5.26` |
| `MiniLM-L12-v2 (384d)` | `hybrid_rrf` | `93.33%` | `0.8667` | `50.5` | `5.26` |
| `MiniLM-L12-v2 (384d)` | `hybrid_rrf_rerank` | `93.33%` | `0.7889` | `2510.2` | `5.26` |

> **Observação prática**: A fusão `hybrid_rrf` (busca vetorial + `BM25` com tokenização legislativa) aumentou o `Recall@4` de `80.00%` para `93.33%` e o `MRR@4` de `0.7056` para `0.8667` adicionando apenas ~`10.5 ms` à busca, enquanto o reranking via Cross-Encoder em CPU elevou a latência média para `2510.2 ms` (podendo ser alternado via `ENABLE_RERANKER=true|false`).

---

### 9.3 Testes Unitários (`tests/`)

A suíte em [`tests/test_telemetry_and_evals.py`](tests/test_telemetry_and_evals.py) cobre extração de tokens, estimativa de custos, migração de schema de `query_logs`, validação das 9 categorias `DOC_TYPES`, sanitização de `QueryRequest`, controle de `MAX_TOOL_ROUNDS`, classificação do `sapl_downloader.py`, descoberta do `batch_upload.py` e scoring de Evals (sem exigir PostgreSQL externo nem chave de API):

```bash
python -m unittest discover -s tests -v
```

---

## 📂 10. Estrutura do Repositório

```text
PublicGov-RAG/
├── app/
│   ├── api/
│   │   ├── deps.py                   # Injeção de dependência da sessão SQLAlchemy
│   │   └── v1/
│   │       ├── documents.py          # Upload de PDFs e listagem do catálogo
│   │       ├── query.py              # Consulta via agente (/ask), /history e /metrics
│   │       └── router.py             # Agregador de rotas /api/v1
│   ├── core/
│   │   ├── config.py                 # Configurações Pydantic Settings (.env)
│   │   ├── constants.py              # 9 categorias oficiais DOC_TYPES e aliases
│   │   ├── observability.py          # Cliente, CallbackHandler e flush do Langfuse
│   │   └── telemetry.py              # Contagem de tokens e estimativa de custo em USD
│   ├── db/
│   │   ├── models.py                 # DocumentModel, QueryLogModel e migração segura
│   │   ├── session.py                # Engine e SessionLocal SQLAlchemy
│   │   └── vector_store.py           # PGVector isolado por coleção + leitura para BM25
│   ├── schemas/
│   │   └── query.py                  # Schemas Pydantic V2 e sanitização de doc_type_filter
│   ├── services/
│   │   ├── agent_service.py          # Agente LangGraph (prompts v1/v2, 4 tools, telemetria)
│   │   ├── embedding_factory.py      # Singleton de embeddings (MiniLM e EmbeddingGemma 2)
│   │   ├── pdf_service.py            # Extração PyPDF + fallback Tesseract OCR + chunking
│   │   ├── rag_service.py            # Orquestração da resposta e persistência em QueryLogModel
│   │   └── retrieval_service.py      # Busca híbrida (pgvector + BM25 + RRF) + FlashRank
│   ├── static/
│   │   ├── index.html                # Workbench Web (Playground, Documentos e Telemetria)
│   │   └── app.js                    # Lógica frontend do Workbench (Markdown, filtros, KPIs)
│   ├── mcp_server.py                 # Servidor MCP (FastMCP) para HTTP /mcp e stdio
│   └── main.py                       # Ponto de entrada FastAPI, StaticFiles e mount /mcp
├── evals/
│   ├── results/
│   │   ├── latest_report.json        # Relatório detalhado mais recente da suíte de Evals
│   │   ├── prompt_comparison.md      # Tabela comparativa Prompt v1 vs Prompt v2
│   │   ├── benchmark_embeddings.json # Resultados brutos do benchmark de embeddings
│   │   └── benchmark_embeddings.md   # Tabela comparativa de retrieval/embeddings
│   ├── golden_dataset.json           # 30 perguntas reais (25 respondíveis + 5 abstenção)
│   ├── dataset.json                  # Dataset inicial (18 perguntas)
│   ├── sample_corpus.json            # Chunks extraídos para benchmark reproduzível
│   ├── benchmark_embeddings.py       # Benchmark MiniLM vs EmbeddingGemma 2 (MRL)
│   └── run_eval.py                   # Runner de Evals (RAGAS, citações, abstenção, cobertura)
├── storage/
│   └── uploads/                      # PDFs persistidos após upload na API (gitignored)
├── tests/
│   └── test_telemetry_and_evals.py   # 13 testes unitários offline (telemetria, agente, ETL, evals)
├── sapl_downloader.py                # ETL e downloader incremental da API REST do SAPL
├── batch_upload.py                   # Upload em lote com deduplicação e check de /health
├── docker-compose.yml                # Stack PostgreSQL/pgvector + API + profile Langfuse
├── .dockerfile                       # Imagem Python 3.12 com Poppler e Tesseract OCR (por)
├── .env.example                      # Modelo de variáveis de ambiente
├── requirements.txt                  # Dependências Python do projeto
└── README.md                         # Documentação do projeto
```

---

## 🔒 11. Governança, Auditoria e Melhores Práticas

1. **Rastreabilidade e Citação Obrigatória**: Toda resposta fundamentada retorna a lista `sources` com os arquivos indexados utilizados e instrui o modelo (`v2`) a citar explicitamente o `.pdf` correspondente, permitindo conferência formal por cidadãos e servidores.
2. **Abstenção Segura e Bloqueio de Alucinações**: Consultas fora do escopo legislativo ou sem lastro documental recebem negativa transparente sem fabricação de números, artigos, datas ou fontes falsas.
3. **Auditoria Completa de Uso e Custos**: Cada requisição ao `/api/v1/query/ask` grava pergunta, resposta, filtro aplicado, ferramentas acionadas, latência, tokens e custo estimado em `query_logs`, além de traces detalhados no Langfuse quando habilitado.
4. **Deduplicação e Padronização na Ingestão**: Use o `sapl_downloader.py` + `batch_upload.py` (que verifica automaticamente arquivos já cadastrados no catálogo) ou nomeie uploads manuais com prefixos claros (ex.: `PLO_12_2025.pdf`, `PAUTA_SO_08_2025.pdf`, `MOCAO_02_2025.pdf`).

---

<p align="center">
  <b>PublicGov-RAG</b> — Transparência, rastreabilidade e eficiência a serviço da democracia e do cidadão de Santana do Livramento.
</p>
