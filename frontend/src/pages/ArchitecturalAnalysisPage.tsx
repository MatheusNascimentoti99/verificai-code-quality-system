import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Upload, FileText, Plus, Trash2, Play, AlertCircle, CheckCircle, Clock, ChevronDown, ChevronUp } from 'lucide-react';
import {
  architecturalAnalysisService,
  type ArchitecturalDoc,
  type ArchitecturalCriteria,
  type ArchitecturalAnalysisResult,
} from '@/services/architecturalAnalysisService';
import MarkdownViewer from '@/components/features/Analysis/MarkdownViewer';
import './ArchitecturalAnalysisPage.css';

// @ts-ignore
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// ─── tipos locais ────────────────────────────────────────────────────────────

type ActiveTab = 'doc' | 'criteria' | 'code' | 'results' | 'history';

// ─── helpers ─────────────────────────────────────────────────────────────────

const statusLabel: Record<string, { label: string; cls: string }> = {
  ADERENTE:              { label: '✅ Aderente',              cls: 'status-compliant' },
  PARCIALMENTE_ADERENTE: { label: '⚠️ Parcialmente Aderente', cls: 'status-partial' },
  NAO_ADERENTE:          { label: '❌ Não Aderente',          cls: 'status-noncompliant' },
};

// ─── componente principal ─────────────────────────────────────────────────────

const ArchitecturalAnalysisPage: React.FC = () => {
  useEffect(() => { document.title = 'AVALIA – Análise Arquitetural'; }, []);

  // ── state: tabs
  const [activeTab, setActiveTab] = useState<ActiveTab>('doc');

  // ── state: documentação
  const [docs, setDocs] = useState<ArchitecturalDoc[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [docTitle, setDocTitle] = useState('');
  const [docUrl, setDocUrl] = useState('');
  const [docContent, setDocContent] = useState('');
  const [docContentType, setDocContentType] = useState<'text' | 'markdown' | 'html'>('text');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [docSaving, setDocSaving] = useState(false);
  const [docError, setDocError] = useState('');

  // ── state: critérios
  const [criteria, setCriteria] = useState<ArchitecturalCriteria[]>([]);
  const [selectedCriteriaIds, setSelectedCriteriaIds] = useState<string[]>([]);
  const [newCriterionText, setNewCriterionText] = useState('');
  const [criteriaLoading, setCriteriaLoading] = useState(false);

  // ── state: código (reutiliza padrão da Análise Geral – paths do banco)
  const [dbFilePaths, setDbFilePaths] = useState<string[]>([]);
  const [selectedFilePaths, setSelectedFilePaths] = useState<string[]>([]);
  const [fileFilter, setFileFilter] = useState('');
  const [useCodeEntry, setUseCodeEntry] = useState(false);

  // ── state: análise
  const [analysisName, setAnalysisName] = useState('Análise Arquitetural');
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<ArchitecturalAnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState('');

  // ── state: histórico
  const [history, setHistory] = useState<ArchitecturalAnalysisResult[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // ── state: expand per-criterion
  const [expandedCriteria, setExpandedCriteria] = useState<Set<string>>(new Set());

  // ─── efeitos ──────────────────────────────────────────────────────────────

  useEffect(() => { loadDocs(); loadCriteria(); loadFilePaths(); }, []);

  const loadDocs = async () => {
    try { setDocs(await architecturalAnalysisService.listDocs()); } catch {}
  };

  const loadCriteria = async () => {
    setCriteriaLoading(true);
    try { setCriteria(await architecturalAnalysisService.listCriteria()); } finally { setCriteriaLoading(false); }
  };

  const loadFilePaths = async () => {
    try {
      const endpoints = [
        `${API_BASE_URL}/file-paths/dev-paths`,
        `${API_BASE_URL}/file-paths/public`,
      ];
      for (const ep of endpoints) {
        const r = await fetch(ep);
        if (r.ok) {
          const data = await r.json();
          const paths: string[] = Array.isArray(data.file_paths)
            ? data.file_paths.map((p: any) => (typeof p === 'string' ? p : p.full_path))
            : [];
          if (paths.length) { 
            setDbFilePaths(paths); 
            setSelectedFilePaths(paths); 
            return; 
          }
        }
      }
    } catch {}
  };

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try { setHistory(await architecturalAnalysisService.listResults()); } finally { setHistoryLoading(false); }
  }, []);

  useEffect(() => { if (activeTab === 'history') loadHistory(); }, [activeTab, loadHistory]);

  // ─── ações: documentação ──────────────────────────────────────────────────

  const handleSaveDoc = async () => {
    if (!docTitle.trim() || (!docContent.trim() && !uploadFile)) {
      setDocError('Informe o título e o conteúdo (ou faça upload de um arquivo).');
      return;
    }
    setDocError('');
    setDocSaving(true);
    try {
      let saved: ArchitecturalDoc;
      if (uploadFile) {
        saved = await architecturalAnalysisService.uploadDoc(docTitle, uploadFile, docUrl || undefined);
      } else {
        saved = await architecturalAnalysisService.createDoc({
          title: docTitle,
          sharepoint_url: docUrl || undefined,
          content: docContent,
          content_type: docContentType,
        });
      }
      await loadDocs();
      setSelectedDocId(saved.id);
      setDocTitle(''); setDocUrl(''); setDocContent(''); setUploadFile(null);
      alert(`✅ Documentação "${saved.title}" salva com ID ${saved.id}!`);
    } catch (e: any) {
      setDocError(e?.message || e?.response?.data?.detail || 'Erro ao salvar documentação.');
    } finally { setDocSaving(false); }
  };

  const handleDeleteDoc = async (id: number) => {
    if (!confirm('Remover esta documentação?')) return;
    await architecturalAnalysisService.deleteDoc(id);
    if (selectedDocId === id) setSelectedDocId(null);
    await loadDocs();
  };

  // ─── ações: critérios ─────────────────────────────────────────────────────

  const handleAddCriterion = async () => {
    if (!newCriterionText.trim()) return;
    const c = await architecturalAnalysisService.createCriterion(newCriterionText.trim());
    setNewCriterionText('');
    await loadCriteria();
    setSelectedCriteriaIds(prev => [...prev, c.id]);
  };

  const handleDeleteCriterion = async (id: string) => {
    await architecturalAnalysisService.deleteCriterion(id);
    setSelectedCriteriaIds(prev => prev.filter(x => x !== id));
    await loadCriteria();
  };

  const toggleCriterion = (id: string) =>
    setSelectedCriteriaIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );

  // ─── ações: análise ───────────────────────────────────────────────────────

  const handleRunAnalysis = async () => {
    if (!selectedDocId) { alert('Selecione uma documentação arquitetural.'); return; }
    if (dbFilePaths.length === 0 && !useCodeEntry) { alert('Nenhum arquivo de código encontrado. Faça upload de código primeiro.'); return; }

    setRunning(true); setProgress(0); setAnalysisError(''); setResult(null);
    setActiveTab('results');

    const timer = setInterval(() =>
      setProgress(p => p < 85 ? p + Math.random() * 10 : p), 600);

    try {
      const res = await architecturalAnalysisService.runAnalysis({
        analysis_name: analysisName,
        doc_id: selectedDocId,
        criteria_ids: selectedCriteriaIds,
        file_paths: selectedFilePaths,
        use_code_entry: useCodeEntry,
      });
      setProgress(100);
      setResult(res);
    } catch (e: any) {
      setAnalysisError(e?.message || e?.response?.data?.detail || 'Erro ao executar análise.');
    } finally {
      clearInterval(timer);
      setRunning(false);
    }
  };

  const handleDeleteResult = async (id: number) => {
    if (!confirm('Remover resultado?')) return;
    await architecturalAnalysisService.deleteResult(id);
    await loadHistory();
    if (result?.id === id) setResult(null);
  };

  const toggleCriterionExpand = (key: string) =>
    setExpandedCriteria(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });

  // ─── render ───────────────────────────────────────────────────────────────

  const selectedDoc = docs.find(d => d.id === selectedDocId);
  const overallStatus = result?.overall_status ? statusLabel[result.overall_status] : null;

  return (
    <div className="arch-page">
      {/* Cabeçalho */}
      <div className="arch-header">
        <div className="arch-header-left">
          <Link to="/dashboard" className="arch-back-link">← Voltar</Link>
          <h1 className="arch-title">🏗️ Análise Arquitetural</h1>
          <p className="arch-subtitle">Verifique a conformidade do código com a documentação arquitetural</p>
        </div>
        <button
          id="btn-run-analysis"
          className="arch-btn-primary"
          onClick={handleRunAnalysis}
          disabled={running || !selectedDocId}
        >
          <Play size={16} /> {running ? 'Analisando...' : 'Executar Análise'}
        </button>
      </div>

      {/* Barra de progresso */}
      {running && (
        <div className="arch-progress-bar-wrap">
          <div className="arch-progress-bar" style={{ width: `${progress}%` }} />
          <span className="arch-progress-label">{Math.round(progress)}% — Aguarde...</span>
        </div>
      )}

      {/* Tabs */}
      <div className="arch-tabs">
        {(['doc', 'criteria', 'code', 'results', 'history'] as ActiveTab[]).map(tab => (
          <button
            key={tab}
            id={`tab-${tab}`}
            className={`arch-tab ${activeTab === tab ? 'arch-tab--active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {{ doc: '📄 Documentação', criteria: '📋 Critérios', code: '💾 Código', results: '📊 Resultado', history: '🕐 Histórico' }[tab]}
          </button>
        ))}
      </div>

      {/* ── Tab: Documentação ─────────────────────────────────────────────── */}
      {activeTab === 'doc' && (
        <div className="arch-card">
          <h2 className="arch-section-title">📄 Documentação Arquitetural</h2>

          {/* Seleção de doc existente */}
          {docs.length > 0 && (
            <div className="arch-field">
              <label className="arch-label">Documentação salva</label>
              <select
                id="select-doc"
                className="arch-select"
                value={selectedDocId ?? ''}
                onChange={e => setSelectedDocId(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">— Selecione uma documentação existente —</option>
                {docs.map(d => (
                  <option key={d.id} value={d.id}>{d.title}</option>
                ))}
              </select>
              {selectedDoc && (
                <div className="arch-doc-preview">
                  <strong>{selectedDoc.title}</strong>
                  {selectedDoc.sharepoint_url && (
                    <span className="arch-doc-url"> | <a href={selectedDoc.sharepoint_url} target="_blank" rel="noreferrer">🔗 SharePoint</a></span>
                  )}
                  <button className="arch-btn-danger-sm" onClick={() => handleDeleteDoc(selectedDoc.id)}>
                    <Trash2 size={14} />
                  </button>
                </div>
              )}
            </div>
          )}

          <hr className="arch-divider" />
          <p className="arch-hint">Ou cadastre uma nova documentação:</p>

          <div className="arch-field">
            <label className="arch-label">Título <span className="arch-required">*</span></label>
            <input id="input-doc-title" className="arch-input" value={docTitle} onChange={e => setDocTitle(e.target.value)} placeholder="Ex: Arquitetura Backend v2.1" />
          </div>

          <div className="arch-field">
            <label className="arch-label">URL SharePoint (metadado)</label>
            <input id="input-sharepoint-url" className="arch-input" value={docUrl} onChange={e => setDocUrl(e.target.value)} placeholder="https://empresa.sharepoint.com/..." />
          </div>

          <div className="arch-field">
            <label className="arch-label">Tipo de conteúdo</label>
            <select className="arch-select" value={docContentType} onChange={e => setDocContentType(e.target.value as any)}>
              <option value="text">Texto puro</option>
              <option value="markdown">Markdown</option>
              <option value="html">HTML (será convertido)</option>
            </select>
          </div>

          <div className="arch-field">
            <label className="arch-label">Conteúdo da documentação</label>
            <textarea
              id="textarea-doc-content"
              className="arch-textarea"
              rows={10}
              value={docContent}
              onChange={e => setDocContent(e.target.value)}
              placeholder="Cole aqui o conteúdo da página SharePoint ou da documentação arquitetural..."
            />
            <span className="arch-char-count">{docContent.length.toLocaleString()} / 500.000 chars</span>
          </div>

          <div className="arch-field">
            <label className="arch-label">Ou faça upload de arquivo (.txt, .md, .html)</label>
            <div className="arch-upload-zone">
              <input
                id="input-doc-upload"
                type="file"
                accept=".txt,.md,.html"
                onChange={e => setUploadFile(e.target.files?.[0] ?? null)}
              />
              {uploadFile && <span className="arch-upload-name"><FileText size={14} /> {uploadFile.name}</span>}
            </div>
          </div>

          {docError && <div className="arch-alert arch-alert--error"><AlertCircle size={16} /> {docError}</div>}

          <button
            id="btn-save-doc"
            className="arch-btn-primary"
            onClick={handleSaveDoc}
            disabled={docSaving}
          >
            {docSaving ? 'Salvando...' : '💾 Salvar Documentação'}
          </button>
        </div>
      )}

      {/* ── Tab: Critérios ────────────────────────────────────────────────── */}
      {activeTab === 'criteria' && (
        <div className="arch-card">
          <h2 className="arch-section-title">📋 Critérios Arquiteturais</h2>
          <p className="arch-hint">Cadastre critérios adicionais de conformidade arquitetural. Selecione os que deseja incluir na análise.</p>

          <div className="arch-criterion-add">
            <input
              id="input-new-criterion"
              className="arch-input"
              value={newCriterionText}
              onChange={e => setNewCriterionText(e.target.value)}
              placeholder="Ex: O sistema deve seguir a arquitetura hexagonal"
              onKeyDown={e => e.key === 'Enter' && handleAddCriterion()}
            />
            <button id="btn-add-criterion" className="arch-btn-primary" onClick={handleAddCriterion}>
              <Plus size={16} /> Adicionar
            </button>
          </div>

          {criteriaLoading && <p className="arch-hint">Carregando critérios...</p>}

          {criteria.length === 0 && !criteriaLoading && (
            <div className="arch-empty">Nenhum critério cadastrado. Adicione critérios acima.</div>
          )}

          <ul className="arch-criteria-list">
            {criteria.map(c => (
              <li key={c.id} className="arch-criterion-item">
                <input
                  type="checkbox"
                  id={`chk-${c.id}`}
                  checked={selectedCriteriaIds.includes(c.id)}
                  onChange={() => toggleCriterion(c.id)}
                />
                <label htmlFor={`chk-${c.id}`} className="arch-criterion-text">{c.text}</label>
                <button className="arch-btn-icon" onClick={() => handleDeleteCriterion(c.id)} title="Remover">
                  <Trash2 size={14} />
                </button>
              </li>
            ))}
          </ul>

          <p className="arch-hint">{selectedCriteriaIds.length} critério(s) selecionado(s) para análise.</p>
        </div>
      )}

      {/* ── Tab: Código ───────────────────────────────────────────────────── */}
      {activeTab === 'code' && (
        <div className="arch-card">
          <h2 className="arch-section-title">💾 Código para Análise</h2>

          {dbFilePaths.length > 0 ? (
            <>
              <div className="arch-alert arch-alert--success">
                <CheckCircle size={16} /> {dbFilePaths.length} arquivo(s) disponível(eis) no sistema.
              </div>
              
              <div className="arch-file-selection-controls" style={{ marginBottom: '15px' }}>
                <input 
                  type="text" 
                  className="arch-input" 
                  placeholder="Filtrar arquivos por nome (ex: backend/app, .ts)..." 
                  value={fileFilter}
                  onChange={e => setFileFilter(e.target.value)}
                  style={{ marginBottom: '10px' }}
                />
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button type="button" className="arch-btn-secondary" onClick={() => setSelectedFilePaths(dbFilePaths)}>Selecionar Todos</button>
                  <button type="button" className="arch-btn-secondary" onClick={() => setSelectedFilePaths([])}>Limpar Seleção</button>
                  <span style={{ marginLeft: 'auto', alignSelf: 'center', fontSize: '0.9rem', color: '#666' }}>
                    {selectedFilePaths.length} arquivo(s) selecionado(s)
                  </span>
                </div>
              </div>

              <ul className="arch-file-list" style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #ddd', padding: '10px', borderRadius: '4px' }}>
                {dbFilePaths.filter(p => p.toLowerCase().includes(fileFilter.toLowerCase())).map(p => (
                  <li key={p} className="arch-file-item" style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }} onClick={() => {
                    setSelectedFilePaths(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p])
                  }}>
                    <input type="checkbox" checked={selectedFilePaths.includes(p)} readOnly style={{ cursor: 'pointer' }} />
                    <FileText size={13} /> <span style={{ wordBreak: 'break-all' }}>{p}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <div className="arch-alert arch-alert--warn">
              <AlertCircle size={16} /> Nenhum arquivo encontrado.{' '}
              <Link to="/code-upload">Faça upload de código primeiro →</Link>
            </div>
          )}

          <div className="arch-field arch-field--row">
            <input type="checkbox" id="chk-use-code-entry" checked={useCodeEntry} onChange={e => setUseCodeEntry(e.target.checked)} />
            <label htmlFor="chk-use-code-entry">Usar código colado (Code Entry)</label>
          </div>

          <div className="arch-field">
            <label className="arch-label">Nome da análise</label>
            <input className="arch-input" value={analysisName} onChange={e => setAnalysisName(e.target.value)} />
          </div>
        </div>
      )}

      {/* ── Tab: Resultado ────────────────────────────────────────────────── */}
      {activeTab === 'results' && (
        <div className="arch-card">
          <h2 className="arch-section-title">📊 Resultado</h2>

          {running && (
            <div className="arch-loading">
              <Clock size={24} className="arch-spin" />
              <span>Executando análise arquitetural... {Math.round(progress)}%</span>
            </div>
          )}

          {analysisError && (
            <div className="arch-alert arch-alert--error"><AlertCircle size={16} /> {analysisError}</div>
          )}

          {!running && !analysisError && !result && (
            <div className="arch-empty">Nenhum resultado ainda. Configure e execute a análise.</div>
          )}

          {result && (
            <div className="arch-result">
              <div className="arch-result-header">
                <h3>{result.analysis_name}</h3>
                {overallStatus && (
                  <span className={`arch-status-badge ${overallStatus.cls}`}>{overallStatus.label}</span>
                )}
                <span className="arch-result-meta">
                  {result.criteria_count} critério(s) | {result.processing_time}
                  {result.model_used && ` | ${result.model_used}`}
                </span>
              </div>

              {/* Resposta bruta em markdown */}
              <div className="arch-result-raw">
                <MarkdownViewer content={result.raw_response} />
              </div>

              {/* Resultados por critério */}
              {Object.keys(result.criteria_results).length > 0 && (
                <div className="arch-criteria-results">
                  <h4>Detalhes por Critério</h4>
                  {Object.entries(result.criteria_results).map(([key, val]) => (
                    <div key={key} className="arch-criterion-result">
                      <button
                        className="arch-criterion-result-header"
                        onClick={() => toggleCriterionExpand(key)}
                      >
                        <strong>{val.name}</strong>
                        {expandedCriteria.has(key) ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                      {expandedCriteria.has(key) && (
                        <div className="arch-criterion-result-body">
                          <MarkdownViewer content={val.content} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Tab: Histórico ────────────────────────────────────────────────── */}
      {activeTab === 'history' && (
        <div className="arch-card">
          <h2 className="arch-section-title">🕐 Histórico de Análises</h2>
          {historyLoading && <p className="arch-hint">Carregando histórico...</p>}
          {!historyLoading && history.length === 0 && (
            <div className="arch-empty">Nenhuma análise realizada ainda.</div>
          )}
          <ul className="arch-history-list">
            {history.map(h => {
              const hs = h.overall_status ? statusLabel[h.overall_status] : null;
              return (
                <li key={h.id} className="arch-history-item">
                  <div className="arch-history-info">
                    <strong>{h.analysis_name}</strong>
                    {hs && <span className={`arch-status-badge arch-status-badge--sm ${hs.cls}`}>{hs.label}</span>}
                    <span className="arch-result-meta">{h.criteria_count} critério(s) · {h.processing_time} · {h.created_at?.slice(0, 16).replace('T', ' ')}</span>
                  </div>
                  <div className="arch-history-actions">
                    <button
                      className="arch-btn-secondary"
                      onClick={() => { setResult(h); setActiveTab('results'); }}
                    >
                      Ver
                    </button>
                    <button className="arch-btn-danger-sm" onClick={() => handleDeleteResult(h.id)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ArchitecturalAnalysisPage;