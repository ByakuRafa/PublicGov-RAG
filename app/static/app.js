'use strict';

// Categorias oficiais sincronizadas com app/core/constants.py (DOC_TYPES)
const DOC_TYPES = [
  'Pauta_Sessao',
  'Ata_Sessao',
  'Projeto_de_Lei',
  'Lei_Municipal',
  'Mocao',
  'Parecer_Comissao',
  'Requerimento_Legislativo',
  'Materia_Legislativa',
  'Regimento_e_LOM',
];

const state = {
  sessionQueries: [],
  activeSessionIndex: -1,
  documents: [],
  history: [],
  expandedHistoryIds: new Set(),
};

// ============================================================================
// Utilitários
// ============================================================================

function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderMarkdownSafe(markdownText) {
  const raw = markdownText || '';
  if (typeof window.marked !== 'undefined') {
    const parsed = window.marked.parse(raw, { breaks: true, gfm: true });
    if (typeof window.DOMPurify !== 'undefined') {
      return window.DOMPurify.sanitize(parsed);
    }
    return parsed;
  }
  return `<pre class="whitespace-pre-wrap">${escapeHtml(raw)}</pre>`;
}

function formatDateTime(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return String(isoString);
  return d.toLocaleString('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'medium',
  });
}

function formatLatency(ms) {
  if (ms === null || ms === undefined || Number.isNaN(Number(ms))) return '—';
  const num = Number(ms);
  if (num >= 1000) {
    return `${(num / 1000).toFixed(2)} s (${Math.round(num)} ms)`;
  }
  return `${Math.round(num)} ms`;
}

function formatUsd(val) {
  if (val === null || val === undefined || Number.isNaN(Number(val))) return '—';
  return `$${Number(val).toFixed(6)}`;
}

function parseToolsUsed(tools) {
  if (!tools) return [];
  if (Array.isArray(tools)) return tools.filter(Boolean);
  if (typeof tools === 'string') {
    return tools
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return [];
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  let data = null;
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    data = await response.json();
  } else {
    const text = await response.text();
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text || response.statusText };
    }
  }

  if (!response.ok) {
    const detail =
      data && typeof data === 'object' && 'detail' in data
        ? typeof data.detail === 'string'
          ? data.detail
          : JSON.stringify(data.detail, null, 2)
        : `HTTP ${response.status} ${response.statusText}`;
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }

  return data;
}

function showError(elId, message) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (!message) {
    el.textContent = '';
    el.classList.add('hidden');
  } else {
    el.textContent = message;
    el.classList.remove('hidden');
  }
}

function populateDocTypeSelects() {
  const selectIds = ['ask-doc-type', 'upload-doc-type', 'docs-filter-type'];
  selectIds.forEach((id) => {
    const select = document.getElementById(id);
    if (!select) return;
    const keepFirst = id !== 'upload-doc-type';
    const firstOption = keepFirst ? select.querySelector('option') : null;
    select.innerHTML = '';
    if (firstOption) select.appendChild(firstOption);

    DOC_TYPES.forEach((docType) => {
      const opt = document.createElement('option');
      opt.value = docType;
      opt.textContent = docType;
      select.appendChild(opt);
    });
  });
}

// ============================================================================
// Barra de Status Persistente (/health)
// ============================================================================

async function loadHealth() {
  const dot = document.getElementById('health-dot');
  const statusText = document.getElementById('health-status-text');
  const versionEl = document.getElementById('health-version');
  const llmEl = document.getElementById('health-llm');
  const embedEl = document.getElementById('health-embedding');
  const vectorEl = document.getElementById('health-vector');
  const langfuseEl = document.getElementById('health-langfuse');

  try {
    const data = await fetchJson('/health');
    const isHealthy = data.status === 'healthy';

    dot.className = `inline-block w-2.5 h-2.5 rounded-full ring-2 ${
      isHealthy ? 'bg-emerald-400 ring-emerald-950' : 'bg-amber-400 ring-amber-950'
    }`;
    statusText.textContent = isHealthy ? 'API Online' : `Status: ${data.status || 'desconhecido'}`;
    statusText.className = `font-mono text-xs ${isHealthy ? 'text-emerald-400' : 'text-amber-400'}`;

    versionEl.textContent = data.version ? `v${data.version}` : 'v—';
    llmEl.textContent = data.llm_model || '—';

    const dimText = data.embedding_dim ? ` (${data.embedding_dim}d)` : '';
    embedEl.textContent = data.embedding_model ? `${data.embedding_model}${dimText}` : '—';

    vectorEl.textContent = data.vector_backend || '—';
    langfuseEl.textContent = data.langfuse_enabled ? 'ativo' : 'inativo';
    langfuseEl.className = data.langfuse_enabled ? 'text-emerald-400' : 'text-zinc-500';
  } catch (err) {
    dot.className = 'inline-block w-2.5 h-2.5 rounded-full bg-red-500 ring-2 ring-red-950';
    statusText.textContent = `Offline (${err.message})`;
    statusText.className = 'font-mono text-xs text-red-400';
  }
}

// ============================================================================
// Navegação por Abas
// ============================================================================

function initTabs() {
  const buttons = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel');

  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;

      buttons.forEach((b) => {
        const active = b.dataset.tab === target;
        b.classList.toggle('border-sky-500', active);
        b.classList.toggle('text-zinc-100', active);
        b.classList.toggle('border-transparent', !active);
        b.classList.toggle('text-zinc-400', !active);
      });

      panels.forEach((p) => {
        p.classList.toggle('hidden', p.id !== `tab-${target}`);
      });

      if (target === 'documents') {
        loadDocuments();
      } else if (target === 'telemetry') {
        loadTelemetry();
      }
    });
  });
}

// ============================================================================
// Aba 1: Playground RAG
// ============================================================================

function renderAskResult(entry) {
  const emptyState = document.getElementById('ask-empty-state');
  const panel = document.getElementById('ask-result-panel');
  emptyState.classList.add('hidden');
  panel.classList.remove('hidden');

  const data = entry.response;
  document.getElementById('res-question-preview').textContent = data.question || entry.request.question;

  const latencyVal = data.latency_ms !== null && data.latency_ms !== undefined
    ? data.latency_ms
    : entry.clientLatencyMs;
  document.getElementById('res-latency').textContent = formatLatency(latencyVal);
  document.getElementById('res-client-latency').textContent = `${Math.round(entry.clientLatencyMs)} ms no cliente`;

  const pTok = data.prompt_tokens ?? '—';
  const cTok = data.completion_tokens ?? '—';
  document.getElementById('res-tokens').textContent = `${pTok} in / ${cTok} out`;
  document.getElementById('res-cost').textContent = formatUsd(data.estimated_cost_usd);

  // Tools used
  const toolsEl = document.getElementById('res-tools');
  const tools = parseToolsUsed(data.tools_used);
  if (tools.length === 0) {
    toolsEl.innerHTML =
      '<span class="font-mono text-xs px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-500">nenhuma ferramenta invocada</span>';
  } else {
    toolsEl.innerHTML = tools
      .map(
        (t) =>
          `<span class="font-mono text-xs px-2 py-0.5 rounded bg-indigo-950/60 border border-indigo-800/70 text-indigo-300">${escapeHtml(
            t
          )}</span>`
      )
      .join('');
  }

  // Answer Markdown
  const answerEl = document.getElementById('res-answer');
  answerEl.innerHTML = renderMarkdownSafe(data.answer);

  // Sources
  const sourcesEl = document.getElementById('res-sources');
  const sources = Array.isArray(data.sources) ? data.sources : [];
  if (sources.length === 0) {
    sourcesEl.innerHTML =
      '<span class="font-mono text-xs px-2.5 py-1 rounded bg-amber-950/50 border border-amber-800/80 text-amber-300">Sem fontes recuperadas (abstenção ou resposta direta)</span>';
  } else {
    sourcesEl.innerHTML = sources
      .map(
        (src) =>
          `<span class="font-mono text-xs px-2.5 py-1 rounded bg-emerald-950/40 border border-emerald-800/70 text-emerald-300">${escapeHtml(
            src
          )}</span>`
      )
      .join('');
  }

  // Raw JSON
  document.getElementById('res-raw-json').textContent = JSON.stringify(
    {
      client_latency_ms: Math.round(entry.clientLatencyMs),
      doc_type_filter_sent: entry.request.doc_type_filter,
      response: data,
    },
    null,
    2
  );
}

function renderSessionList() {
  const listEl = document.getElementById('session-list');
  const countEl = document.getElementById('session-count');
  countEl.textContent = `${state.sessionQueries.length} consulta${state.sessionQueries.length === 1 ? '' : 's'}`;

  if (state.sessionQueries.length === 0) {
    listEl.innerHTML =
      '<p class="text-xs text-zinc-500 italic">Nenhuma consulta executada nesta sessão ainda.</p>';
    return;
  }

  listEl.innerHTML = state.sessionQueries
    .map((entry, idx) => {
      const active = idx === state.activeSessionIndex;
      const tools = parseToolsUsed(entry.response.tools_used);
      const sources = Array.isArray(entry.response.sources) ? entry.response.sources : [];
      return `
        <button type="button" data-session-idx="${idx}"
          class="session-item w-full text-left p-2 rounded border transition cursor-pointer ${
            active
              ? 'bg-sky-950/40 border-sky-700/80'
              : 'bg-zinc-950/70 border-zinc-800 hover:border-zinc-700'
          }">
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs text-zinc-200 font-medium truncate">${escapeHtml(entry.request.question)}</span>
            <span class="font-mono text-[10px] text-sky-400 shrink-0">${Math.round(entry.clientLatencyMs)} ms</span>
          </div>
          <div class="mt-1 flex flex-wrap items-center gap-1.5 font-mono text-[10px] text-zinc-500">
            <span>${escapeHtml(entry.request.doc_type_filter || 'Todos')}</span>
            <span>•</span>
            <span>${sources.length} fonte(s)</span>
            <span>•</span>
            <span>${tools.length} tool(s)</span>
          </div>
        </button>
      `;
    })
    .join('');

  listEl.querySelectorAll('.session-item').forEach((btn) => {
    btn.addEventListener('click', () => {
      const idx = Number(btn.dataset.sessionIdx);
      state.activeSessionIndex = idx;
      const entry = state.sessionQueries[idx];
      if (entry) {
        document.getElementById('ask-question').value = entry.request.question;
        document.getElementById('ask-doc-type').value = entry.request.doc_type_filter || '';
        renderAskResult(entry);
        renderSessionList();
      }
    });
  });
}

async function submitAskForm(e) {
  if (e) e.preventDefault();
  showError('ask-error', null);

  const questionInput = document.getElementById('ask-question');
  const docTypeSelect = document.getElementById('ask-doc-type');
  const submitBtn = document.getElementById('ask-submit-btn');
  const btnLabel = document.getElementById('ask-btn-label');
  const timerEl = document.getElementById('ask-timer');

  const question = questionInput.value.trim();
  if (!question) {
    showError('ask-error', 'Informe uma pergunta antes de enviar.');
    return;
  }

  const docTypeFilter = docTypeSelect.value.trim() || null;

  submitBtn.disabled = true;
  btnLabel.textContent = 'Consultando...';
  timerEl.classList.remove('hidden');

  const start = performance.now();
  const timerHandle = setInterval(() => {
    const elapsed = performance.now() - start;
    timerEl.textContent = elapsed >= 1000 ? `${(elapsed / 1000).toFixed(1)} s` : `${Math.round(elapsed)} ms`;
  }, 60);

  try {
    const payload = {
      question,
      doc_type_filter: docTypeFilter,
    };
    const response = await fetchJson('/api/v1/query/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const clientLatencyMs = performance.now() - start;
    const entry = {
      id: Date.now(),
      request: payload,
      response,
      clientLatencyMs,
    };

    state.sessionQueries.unshift(entry);
    state.activeSessionIndex = 0;
    renderAskResult(entry);
    renderSessionList();
  } catch (err) {
    showError('ask-error', err.message);
  } finally {
    clearInterval(timerHandle);
    submitBtn.disabled = false;
    btnLabel.textContent = 'Executar Consulta';
    timerEl.classList.add('hidden');
  }
}

function initPlayground() {
  const form = document.getElementById('ask-form');
  const textarea = document.getElementById('ask-question');

  form.addEventListener('submit', submitAskForm);
  textarea.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      submitAskForm();
    }
  });

  document.querySelectorAll('.preset-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      textarea.value = btn.dataset.question || '';
      document.getElementById('ask-doc-type').value = btn.dataset.doctype || '';
      textarea.focus();
    });
  });

  document.getElementById('btn-clear-session').addEventListener('click', () => {
    state.sessionQueries = [];
    state.activeSessionIndex = -1;
    renderSessionList();
  });
}

// ============================================================================
// Aba 2: Documentos & Ingestão
// ============================================================================

function renderCategoryCoverage(docs) {
  const counts = {};
  DOC_TYPES.forEach((t) => {
    counts[t] = 0;
  });

  docs.forEach((d) => {
    if (d.doc_type in counts) {
      counts[d.doc_type] += 1;
    } else if (d.doc_type) {
      counts[d.doc_type] = (counts[d.doc_type] || 0) + 1;
    }
  });

  const grid = document.getElementById('docs-coverage-grid');
  grid.innerHTML = Object.entries(counts)
    .map(([docType, count]) => {
      const isEmpty = count === 0;
      return `
        <div class="rounded-md p-2.5 border ${
          isEmpty
            ? 'bg-amber-950/20 border-amber-800/60 border-dashed'
            : 'bg-zinc-950 border-zinc-800'
        }">
          <div class="font-mono text-[11px] truncate ${isEmpty ? 'text-amber-300' : 'text-zinc-400'}" title="${escapeHtml(
            docType
          )}">
            ${escapeHtml(docType)}
          </div>
          <div class="mt-1 flex items-baseline justify-between">
            <span class="font-mono text-lg font-semibold ${isEmpty ? 'text-amber-400' : 'text-zinc-100'}">${count}</span>
            <span class="font-mono text-[10px] ${isEmpty ? 'text-amber-500' : 'text-zinc-500'}">
              ${isEmpty ? 'vazio' : count === 1 ? 'doc' : 'docs'}
            </span>
          </div>
        </div>
      `;
    })
    .join('');
}

function renderDocumentsTable() {
  const search = document.getElementById('docs-search').value.trim().toLowerCase();
  const typeFilter = document.getElementById('docs-filter-type').value;
  const tbody = document.getElementById('docs-table-body');
  const totalCountEl = document.getElementById('docs-total-count');

  const filtered = state.documents.filter((d) => {
    if (typeFilter && d.doc_type !== typeFilter) return false;
    if (search) {
      const hay = `${d.id} ${d.filename || ''} ${d.doc_type || ''}`.toLowerCase();
      if (!hay.includes(search)) return false;
    }
    return true;
  });

  totalCountEl.textContent = String(filtered.length);

  if (filtered.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="5" class="px-3 py-6 text-center text-zinc-500">Nenhum documento encontrado.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered
    .map(
      (doc) => `
      <tr class="hover:bg-zinc-800/40 transition">
        <td class="px-3 py-2 font-mono text-zinc-400">#${escapeHtml(doc.id)}</td>
        <td class="px-3 py-2 font-mono text-zinc-200">${escapeHtml(doc.filename)}</td>
        <td class="px-3 py-2">
          <span class="font-mono text-[11px] px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-sky-300">
            ${escapeHtml(doc.doc_type)}
          </span>
        </td>
        <td class="px-3 py-2 font-mono text-right text-zinc-200">${escapeHtml(doc.chunks_count)}</td>
        <td class="px-3 py-2 font-mono text-zinc-400">${escapeHtml(formatDateTime(doc.uploaded_at))}</td>
      </tr>
    `
    )
    .join('');
}

async function loadDocuments() {
  showError('docs-error', null);
  try {
    const docs = await fetchJson('/api/v1/documents/');
    state.documents = Array.isArray(docs) ? docs : [];
    renderCategoryCoverage(state.documents);
    renderDocumentsTable();
  } catch (err) {
    showError('docs-error', `Erro ao carregar documentos: ${err.message}`);
  }
}

async function submitUploadForm(e) {
  e.preventDefault();
  showError('upload-error', null);

  const fileInput = document.getElementById('upload-file');
  const docTypeSelect = document.getElementById('upload-doc-type');
  const submitBtn = document.getElementById('upload-submit-btn');
  const btnLabel = document.getElementById('upload-btn-label');
  const timerEl = document.getElementById('upload-timer');
  const resultBox = document.getElementById('upload-result');

  const file = fileInput.files && fileInput.files[0];
  if (!file) {
    showError('upload-error', 'Selecione um arquivo PDF.');
    return;
  }

  resultBox.classList.add('hidden');
  submitBtn.disabled = true;
  btnLabel.textContent = 'Processando PDF / OCR...';
  timerEl.classList.remove('hidden');

  const start = performance.now();
  const timerHandle = setInterval(() => {
    const elapsedSec = (performance.now() - start) / 1000;
    timerEl.textContent = `${elapsedSec.toFixed(1)} s`;
  }, 100);

  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docTypeSelect.value);

    const data = await fetchJson('/api/v1/documents/upload', {
      method: 'POST',
      body: formData,
    });

    document.getElementById('upload-result-msg').textContent = data.message || 'Upload concluído.';
    document.getElementById('upload-result-id').textContent = data.document_id ?? '—';
    document.getElementById('upload-result-chunks').textContent = data.chunks_created ?? '—';
    document.getElementById('upload-raw-json').textContent = JSON.stringify(data, null, 2);
    resultBox.classList.remove('hidden');

    fileInput.value = '';
    await loadDocuments();
  } catch (err) {
    showError('upload-error', err.message);
  } finally {
    clearInterval(timerHandle);
    submitBtn.disabled = false;
    btnLabel.textContent = 'Enviar e Indexar PDF';
    timerEl.classList.add('hidden');
  }
}

function initDocuments() {
  document.getElementById('upload-form').addEventListener('submit', submitUploadForm);
  document.getElementById('btn-refresh-docs').addEventListener('click', loadDocuments);
  document.getElementById('docs-search').addEventListener('input', renderDocumentsTable);
  document.getElementById('docs-filter-type').addEventListener('change', renderDocumentsTable);
}

// ============================================================================
// Aba 3: Telemetria & Auditoria
// ============================================================================

function renderHistoryTable() {
  const search = document.getElementById('history-search').value.trim().toLowerCase();
  const tbody = document.getElementById('history-table-body');
  const countEl = document.getElementById('history-count');

  const filtered = state.history.filter((row) => {
    if (!search) return true;
    const hay = `${row.question || ''} ${row.answer || ''} ${row.tools_used || ''} ${
      row.doc_type_filter || ''
    }`.toLowerCase();
    return hay.includes(search);
  });

  countEl.textContent = String(filtered.length);

  if (filtered.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="7" class="px-3 py-6 text-center text-zinc-500">Nenhum registro encontrado.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered
    .map((row) => {
      const tools = parseToolsUsed(row.tools_used);
      const toolsHtml =
        tools.length > 0
          ? tools
              .map(
                (t) =>
                  `<span class="font-mono text-[10px] px-1.5 py-0.5 rounded bg-indigo-950/60 border border-indigo-800/70 text-indigo-300">${escapeHtml(
                    t
                  )}</span>`
              )
              .join(' ')
          : '<span class="font-mono text-zinc-600">—</span>';

      // QueryLogModel não persiste `sources`; exibe `sources` se presente ou `doc_type_filter`
      const sourcesList = Array.isArray(row.sources) ? row.sources : null;
      const sourceOrFilterHtml = sourcesList
        ? sourcesList.length > 0
          ? sourcesList.map((s) => `<span class="font-mono text-[10px] text-emerald-300">${escapeHtml(s)}</span>`).join(', ')
          : '<span class="font-mono text-amber-400">vazio</span>'
        : row.doc_type_filter
        ? `<span class="font-mono text-[10px] px-1.5 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-300">filtro: ${escapeHtml(
            row.doc_type_filter
          )}</span>`
        : '<span class="font-mono text-zinc-600" title="sources não é persistido em QueryLogModel">—</span>';

      const pTok = row.prompt_tokens ?? '—';
      const cTok = row.completion_tokens ?? '—';
      const isExpanded = state.expandedHistoryIds.has(row.id);

      const mainRow = `
        <tr data-history-id="${escapeHtml(row.id)}" class="history-row hover:bg-zinc-800/40 transition cursor-pointer">
          <td class="px-3 py-2 font-mono text-[11px] text-zinc-400 whitespace-nowrap">${escapeHtml(
            formatDateTime(row.created_at)
          )}</td>
          <td class="px-3 py-2 text-zinc-200 max-w-xs truncate" title="${escapeHtml(row.question)}">${escapeHtml(
        row.question
      )}</td>
          <td class="px-3 py-2"><div class="flex flex-wrap gap-1">${toolsHtml}</div></td>
          <td class="px-3 py-2">${sourceOrFilterHtml}</td>
          <td class="px-3 py-2 font-mono text-right text-sky-400">${
            row.latency_ms !== null && row.latency_ms !== undefined ? Math.round(row.latency_ms) : '—'
          }</td>
          <td class="px-3 py-2 font-mono text-right text-zinc-300 whitespace-nowrap">${pTok} / ${cTok}</td>
          <td class="px-3 py-2 font-mono text-right text-emerald-400">${formatUsd(row.estimated_cost_usd)}</td>
        </tr>
      `;

      if (!isExpanded) return mainRow;

      const detailRow = `
        <tr class="bg-zinc-950/90">
          <td colspan="7" class="px-4 py-3 border-t border-zinc-800 space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-2 font-mono text-[11px] text-zinc-400">
              <span>Log ID: <strong class="text-zinc-200">#${escapeHtml(row.id)}</strong></span>
              <span>Filtro: <strong class="text-zinc-200">${escapeHtml(row.doc_type_filter || 'Nenhum')}</strong></span>
              <span>Criado em: <strong class="text-zinc-200">${escapeHtml(formatDateTime(row.created_at))}</strong></span>
            </div>
            <div>
              <div class="text-[11px] font-mono text-zinc-500 uppercase mb-1">Pergunta completa</div>
              <div class="text-xs text-zinc-100 bg-zinc-900 border border-zinc-800 rounded p-2.5">${escapeHtml(
                row.question
              )}</div>
            </div>
            <div>
              <div class="text-[11px] font-mono text-zinc-500 uppercase mb-1">Resposta</div>
              <div class="markdown-body text-xs text-zinc-200 bg-zinc-900 border border-zinc-800 rounded p-3">${renderMarkdownSafe(
                row.answer
              )}</div>
            </div>
            <details class="bg-zinc-900 border border-zinc-800 rounded">
              <summary class="px-2.5 py-1.5 text-[11px] font-mono text-zinc-400 cursor-pointer">Metadados JSON</summary>
              <pre class="p-2.5 text-[11px] font-mono text-zinc-300 overflow-x-auto">${escapeHtml(
                JSON.stringify(row, null, 2)
              )}</pre>
            </details>
          </td>
        </tr>
      `;

      return mainRow + detailRow;
    })
    .join('');

  tbody.querySelectorAll('.history-row').forEach((tr) => {
    tr.addEventListener('click', () => {
      const id = Number(tr.dataset.historyId);
      if (state.expandedHistoryIds.has(id)) {
        state.expandedHistoryIds.delete(id);
      } else {
        state.expandedHistoryIds.add(id);
      }
      renderHistoryTable();
    });
  });
}

async function loadTelemetry() {
  showError('telemetry-error', null);
  const limit = document.getElementById('history-limit').value || '50';

  try {
    const [metrics, history] = await Promise.all([
      fetchJson('/api/v1/query/metrics'),
      fetchJson(`/api/v1/query/history?limit=${encodeURIComponent(limit)}`),
    ]);

    document.getElementById('kpi-total-queries').textContent = metrics.total_queries ?? 0;
    document.getElementById('kpi-avg-latency').textContent = formatLatency(metrics.avg_latency_ms);
    document.getElementById('kpi-tokens').textContent = `${metrics.total_prompt_tokens ?? 0} / ${
      metrics.total_completion_tokens ?? 0
    }`;
    document.getElementById('kpi-cost').textContent = formatUsd(metrics.total_estimated_cost_usd);

    state.history = Array.isArray(history) ? history : [];
    renderHistoryTable();
  } catch (err) {
    showError('telemetry-error', `Erro ao carregar telemetria: ${err.message}`);
  }
}

function initTelemetry() {
  document.getElementById('btn-refresh-telemetry').addEventListener('click', loadTelemetry);
  document.getElementById('history-limit').addEventListener('change', loadTelemetry);
  document.getElementById('history-search').addEventListener('input', renderHistoryTable);
}

// ============================================================================
// Inicialização
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  populateDocTypeSelects();
  initTabs();
  initPlayground();
  initDocuments();
  initTelemetry();

  document.getElementById('btn-refresh-health').addEventListener('click', loadHealth);
  loadHealth();
});
