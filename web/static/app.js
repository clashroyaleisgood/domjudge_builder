// DOMjudge Builder Frontend Application

const state = {
  currentPid: 'DBM',
  currentTab: 'statement', // 'concept', 'statement', 'solver'
  problemData: null,
  problemsList: [],
  settings: {
    provider: 'gemini',
    apiKey: '',
    model: '',
    baseUrl: ''
  }
};

// ----------------- 初始化 -----------------
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  loadProblems();
  selectProblem('DBM');
});

// ----------------- 設定與 LocalStorage -----------------
function loadSettings() {
  const saved = localStorage.getItem('djb_settings');
  if (saved) {
    try {
      state.settings = { ...state.settings, ...jsonParseSafe(saved) };
    } catch (e) {}
  }
  document.getElementById('cfg-provider').value = state.settings.provider || 'gemini';
  document.getElementById('cfg-api-key').value = state.settings.apiKey || '';
  document.getElementById('cfg-model').value = state.settings.model || '';
  document.getElementById('cfg-base-url').value = state.settings.baseUrl || '';
  onProviderChange();
}

function saveSettings() {
  state.settings.provider = document.getElementById('cfg-provider').value;
  state.settings.apiKey = document.getElementById('cfg-api-key').value.trim();
  state.settings.model = document.getElementById('cfg-model').value.trim();
  state.settings.baseUrl = document.getElementById('cfg-base-url').value.trim();

  localStorage.setItem('djb_settings', JSON.stringify(state.settings));
  toggleSettingsModal();
  logConsole(`[設定] 已儲存 API 設定 (Provider: ${state.settings.provider})`);
}

function toggleSettingsModal() {
  const modal = document.getElementById('modal-settings');
  modal.style.display = modal.style.display === 'none' ? 'flex' : 'none';
}

function onProviderChange() {
  const prov = document.getElementById('cfg-provider').value;
  const grpBaseUrl = document.getElementById('group-base-url');
  grpBaseUrl.style.display = prov === 'openai' ? 'block' : 'none';
}

// ----------------- 視圖切換 -----------------
function switchView(viewName) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));

  document.getElementById(`tab-${viewName}`).classList.add('active');
  document.getElementById(`view-${viewName}`).classList.add('active');

  if (viewName === 'pipeline') {
    loadProblems();
  }
}

function jumpToPipelineWithCurrentProblem() {
  const pid = document.getElementById('ideation-prob-id').value.trim().toUpperCase() || 'DCA';
  switchView('pipeline');
  selectProblem(pid);
}

// ----------------- 題庫載入與渲染 -----------------
async function loadProblems() {
  try {
    const res = await fetch('/api/problems');
    const json = await res.json();
    if (json.success) {
      state.problemsList = json.problems;
      renderPipelineTable(json.problems);
      renderReferenceList(json.problems);
    }
  } catch (err) {
    logConsole(`[錯誤] 載入題目清單失敗: ${err.message}`);
  }
}

function renderPipelineTable(problems) {
  const tbody = document.getElementById('pipeline-table-body');
  if (!problems.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">目前題目庫中無任何題目</td></tr>';
    return;
  }

  tbody.innerHTML = problems.map(p => `
    <tr class="${p.id === state.currentPid ? 'selected' : ''}" onclick="selectProblem('${p.id}')">
      <td><strong class="font-mono">${p.id}</strong></td>
      <td>${escapeHtml(p.title)}</td>
      <td class="text-center">${p.has_concept ? '<span class="badge badge-success">✓ 就緒</span>' : '<span class="text-muted">-</span>'}</td>
      <td class="text-center">${p.has_statement ? '<span class="badge badge-success">✓ 就緒</span>' : '<span class="text-muted">-</span>'}</td>
      <td class="text-center">${p.has_solver ? '<span class="badge badge-success">✓ 就緒</span>' : '<span class="text-muted">-</span>'}</td>
      <td class="text-center">${p.has_pdf ? '<span class="badge badge-info">✓ PDF</span>' : '<span class="text-muted">-</span>'}</td>
      <td class="text-center">${p.has_zip ? '<span class="badge badge-primary">✓ ZIP</span>' : '<span class="text-muted">-</span>'}</td>
      <td class="text-center">
        <button class="btn btn-secondary btn-xs" onclick="event.stopPropagation(); selectProblem('${p.id}')">進入工作台</button>
      </td>
    </tr>
  `).join('');
}

function renderReferenceList(problems) {
  const container = document.getElementById('reference-problems-list');
  if (!problems.length) {
    container.innerHTML = '<span class="text-muted text-sm">無可用參考題目</span>';
    return;
  }

  container.innerHTML = problems.map(p => `
    <label class="ref-item">
      <input type="checkbox" name="ref-prob" value="${p.id}" ${p.id === 'DBM' || p.id === 'DAL' ? 'checked' : ''}>
      <span class="font-mono"><strong>${p.id}</strong></span>
      <span class="text-muted text-sm text-truncate">${escapeHtml(p.title)}</span>
    </label>
  `).join('');
}

// ----------------- 題目選擇與工作台綁定 -----------------
async function selectProblem(pid) {
  state.currentPid = pid;
  document.getElementById('wb-current-id').innerText = pid;

  // 更新表格高亮
  document.querySelectorAll('#pipeline-table-body tr').forEach(tr => {
    tr.classList.remove('selected');
  });

  try {
    const res = await fetch(`/api/problem/${pid}`);
    const json = await res.json();
    if (json.success) {
      state.problemData = json.data;
      document.getElementById('wb-current-title').innerText = json.data.id;
      renderCurrentFileInEditor();
      updatePreview(json.data.has_pdf ? `/api/pdf/${pid}` : '');
      updateDownloadLink(json.data.has_zip ? `/api/download/${pid}` : '');
    }
  } catch (err) {
    logConsole(`[錯誤] 載入題目 ${pid} 失敗: ${err.message}`);
  }
}

function switchFileTab(tabName) {
  state.currentTab = tabName;
  document.querySelectorAll('.file-tab').forEach(b => b.classList.remove('active'));
  document.getElementById(`ftab-${tabName}`).classList.add('active');

  const names = { concept: 'concept.yaml', statement: 'statement.md', solver: 'solver.py' };
  document.getElementById('editor-file-indicator').innerText = names[tabName];
  renderCurrentFileInEditor();
}

function renderCurrentFileInEditor() {
  if (!state.problemData) return;
  const editor = document.getElementById('file-editor');
  editor.value = state.problemData[state.currentTab] || '';
}

// ----------------- 檔案儲存與即時修改 -----------------
async function saveCurrentFile() {
  if (!state.problemData) return;
  const content = document.getElementById('file-editor').value;
  state.problemData[state.currentTab] = content;

  const payload = { id: state.currentPid, [state.currentTab]: content };
  try {
    const res = await fetch('/api/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      logConsole(`[儲存] ${state.currentPid} / ${state.currentTab} 儲存成功！`);
      loadProblems();
    } else {
      logConsole(`[失敗] 儲存失敗: ${json.error}`);
    }
  } catch (err) {
    logConsole(`[錯誤] 請求異常: ${err.message}`);
  }
}

// ----------------- 驗證 (Check) 與編譯 (Build) -----------------
async function checkCurrentProblem() {
  await saveCurrentFile();
  logConsole(`[CHECK] 正在對 ${state.currentPid} 執行 Sanity Check 交叉檢驗...`);

  try {
    const res = await fetch('/api/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: state.currentPid })
    });
    const json = await res.json();
    if (json.success) {
      const r = json.result;
      logConsole(`[OK] 檢驗通過！\n  - 題目: ${r.id} - ${r.title}\n  - 範例數: ${r.samples_count} 筆 (吻合)\n  - 總測資: ${r.total_cases} 筆`);
    } else {
      logConsole(`[FAIL] 檢驗未通過:\n${json.error}`);
    }
  } catch (err) {
    logConsole(`[錯誤] 檢驗連線失敗: ${err.message}`);
  }
}

async function previewCurrentProblemPDF() {
  await saveCurrentFile();
  logConsole(`[PDF] 正在使用 Edge Headless 渲染 ${state.currentPid} 題本 PDF...`);

  try {
    const res = await fetch('/api/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: state.currentPid })
    });
    const json = await res.json();
    if (json.success) {
      logConsole(`[OK] 題本 PDF 渲染成功！`);
      updatePreview(json.pdf_url);
      loadProblems();
    } else {
      logConsole(`[FAIL] PDF 渲染失敗: ${json.error}`);
    }
  } catch (err) {
    logConsole(`[錯誤] PDF 連線失敗: ${err.message}`);
  }
}

async function buildCurrentProblem() {
  await saveCurrentFile();
  logConsole(`[BUILD] 開始執行 ${state.currentPid} 完整建置 (PDF + 測資 + DOMjudge ZIP)...`);

  try {
    const res = await fetch('/api/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: state.currentPid })
    });
    const json = await res.json();
    if (json.success) {
      const r = json.result;
      logConsole(`[OK] 建置完成！\n  - 題目: ${r.id} - ${r.title}\n  - 測資: ${r.testcases_count} 筆 (公開 ${r.samples_count} / 隱藏 ${r.secret_count})\n  - 壓縮包: ${r.id}.zip 就緒`);
      updatePreview(r.pdf_url);
      updateDownloadLink(r.zip_download_url);
      loadProblems();
    } else {
      logConsole(`[FAIL] 建置失敗:\n${json.error}`);
    }
  } catch (err) {
    logConsole(`[錯誤] 建置連線失敗: ${err.message}`);
  }
}

async function batchBuildAll() {
  logConsole(`[BATCH] 開始批次建置所有題目...`);
  for (const p of state.problemsList) {
    logConsole(`>> 建置 ${p.id} 中...`);
    try {
      const res = await fetch('/api/build', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: p.id })
      });
      const json = await res.json();
      if (json.success) {
        logConsole(`  [✓] ${p.id} 建置成功`);
      } else {
        logConsole(`  [✗] ${p.id} 建置失敗: ${json.error}`);
      }
    } catch (e) {
      logConsole(`  [✗] ${p.id} 連線失敗: ${e.message}`);
    }
  }
  logConsole(`[DONE] 批次建置完畢！`);
  loadProblems();
}

// ----------------- AI 協同生成 -----------------
async function generateConcept() {
  const pid = document.getElementById('ideation-prob-id').value.trim().toUpperCase() || 'DCA';
  const prompt = document.getElementById('ideation-prompt').value.trim();
  if (!prompt) {
    alert('請輸入題目發想描述！');
    return;
  }

  const refs = Array.from(document.querySelectorAll('input[name="ref-prob"]:checked')).map(cb => cb.value);

  logConsole(`[AI] 正在為 ${pid} 收斂核心概念規格 (concept.yaml)...`);

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: pid,
        step: 'concept',
        prompt: prompt,
        refs: refs,
        api_key: state.settings.apiKey,
        provider: state.settings.provider,
        model: state.settings.model,
        base_url: state.settings.baseUrl
      })
    });
    const json = await res.json();
    if (json.success) {
      document.getElementById('ideation-concept-output').value = json.content;
      logConsole(`[OK] concept.yaml 收斂成功！`);
      loadProblems();
    } else {
      logConsole(`[FAIL] AI 生成失敗: ${json.error}`);
    }
  } catch (err) {
    logConsole(`[錯誤] AI 連線失敗: ${err.message}`);
  }
}

async function saveConcept() {
  const pid = document.getElementById('ideation-prob-id').value.trim().toUpperCase() || 'DCA';
  const content = document.getElementById('ideation-concept-output').value;
  if (!content.trim()) {
    alert('概念內容為空，無法儲存！');
    return;
  }

  const res = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: pid, concept: content })
  });
  const json = await res.json();
  if (json.success) {
    logConsole(`[儲存] ${pid}/concept.yaml 儲存成功！`);
    loadProblems();
  } else {
    logConsole(`[失敗] ${json.error}`);
  }
}

async function aiGenerateCurrentFile() {
  if (state.currentTab === 'concept') {
    alert('concept.yaml 請至「題目發想」分頁進行發想收斂！');
    return;
  }

  logConsole(`[AI] 正在為 ${state.currentPid} 推導生成 ${state.currentTab}...`);

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: state.currentPid,
        step: state.currentTab,
        api_key: state.settings.apiKey,
        provider: state.settings.provider,
        model: state.settings.model,
        base_url: state.settings.baseUrl
      })
    });
    const json = await res.json();
    if (json.success) {
      document.getElementById('file-editor').value = json.content;
      state.problemData[state.currentTab] = json.content;
      logConsole(`[OK] ${state.currentTab} 生成成功並已填入編輯器！`);
      loadProblems();
    } else {
      logConsole(`[FAIL] AI 生成失敗: ${json.error}`);
    }
  } catch (err) {
    logConsole(`[錯誤] AI 連線失敗: ${err.message}`);
  }
}

// ----------------- UI 輔助函式 -----------------
function updatePreview(url) {
  const frame = document.getElementById('pdf-preview-frame');
  const placeholder = document.getElementById('pdf-placeholder');
  const btnExt = document.getElementById('btn-pdf-external');

  if (url) {
    frame.src = url;
    placeholder.style.display = 'none';
    btnExt.href = url;
    btnExt.style.display = 'inline-flex';
  } else {
    frame.src = 'about:blank';
    placeholder.style.display = 'flex';
    btnExt.style.display = 'none';
  }
}

function updateDownloadLink(url) {
  const container = document.getElementById('download-container');
  if (url) {
    container.innerHTML = `<a href="${url}" class="btn btn-success" download><span class="btn-icon">⬇️</span> 下載 DOMjudge ZIP</a>`;
  } else {
    container.innerHTML = '';
  }
}

function logConsole(msg) {
  const box = document.getElementById('console-output');
  box.textContent = msg;
}

function clearConsole() {
  document.getElementById('console-output').textContent = '系統就緒。';
}

function escapeHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function jsonParseSafe(str) {
  try { return JSON.parse(str); } catch (e) { return {}; }
}
