import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  ChevronDown,
  CheckCircle,
  AlertTriangle,
  XCircle,
  HelpCircle,
  RefreshCw,
  FileText,
  Calendar,
  FolderOpen,
  Printer,
} from 'lucide-react';
import { analysisService, type AnalysisRequest, type AnalysisResponse } from '@/services/analysisService';
import { criteriaService } from '@/services/criteriaService';
import './GeneralAnalysisResultDetailPage.css';

/* ── Types ── */
interface CriterionResult {
  key: string;
  name: string;
  content: string;
  status: 'compliant' | 'partially_compliant' | 'non_compliant';
  confidence: number;
  criteriaId?: number;
}

interface AnalysisDetail {
  id: number;
  analysis_name: string;
  project_name?: string;
  timestamp: string;
  model_used?: string;
  criteria_results: Record<string, { name: string; content: string }>;
}

/* ── Helpers ── */
function parseStatus(content: string): 'compliant' | 'partially_compliant' | 'non_compliant' {
  const statusMatch = content.match(/\*\*Status:\*\*\s*([^*\n]+)/i);
  if (statusMatch) {
    const st = statusMatch[1].trim().toLowerCase();
    if (st === 'não conforme' || st === 'nao conforme' || st.startsWith('não conforme') || st.startsWith('nao conforme')) return 'non_compliant';
    if (st === 'parcialmente conforme' || st.startsWith('parcialmente conforme')) return 'partially_compliant';
    if (st === 'conforme' || st.startsWith('conforme')) return 'compliant';
    if (st.includes('não conforme') || st.includes('nao conforme')) return 'non_compliant';
    if (st.includes('parcialmente conforme')) return 'partially_compliant';
    if (st.includes('conforme') && !st.includes('não') && !st.includes('nao')) return 'compliant';
  }
  const lower = content.toLowerCase();
  if (lower.includes('não atende') || lower.includes('não cumpre') || lower.includes('viol') || lower.includes('defeito')) return 'non_compliant';
  if (lower.includes('parcialmente') || lower.includes('atende parcialmente') || lower.includes('precisa melhorar')) return 'partially_compliant';
  return 'compliant';
}

function parseConfidence(content: string): number {
  const match = content.match(/(confiança|confidence)[^\d]*(\d+(?:\.\d+)?)/i);
  if (match) { const v = parseFloat(match[2]); return v > 1 ? Math.min(v / 100, 1) : Math.min(v, 1); }
  return 0.8;
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'compliant': return <CheckCircle size={18} />;
    case 'partially_compliant': return <AlertTriangle size={18} />;
    case 'non_compliant': return <XCircle size={18} />;
    default: return <HelpCircle size={18} />;
  }
}

function getStatusText(status: string) {
  switch (status) {
    case 'compliant': return 'Conforme';
    case 'partially_compliant': return 'Parcialmente Conforme';
    case 'non_compliant': return 'Não Conforme';
    default: return 'Não Avaliado';
  }
}

function getStatusCssClass(status: string) {
  switch (status) {
    case 'compliant': return 'compliant';
    case 'partially_compliant': return 'partial';
    case 'non_compliant': return 'non-compliant';
    default: return '';
  }
}

function formatAssessmentHTML(text: string): string {
  let out = text;
  out = out.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre style="background:#f0f0f0;padding:12px;border-radius:6px;overflow-x:auto;font-size:13px;"><code>$2</code></pre>');
  out = out.replace(/`([^`]+)`/g, '<code style="background:#e9ecef;padding:2px 5px;border-radius:3px;font-family:monospace;font-size:13px;">$1</code>');
  out = out.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/^### (.+)$/gm, '<h5 style="color:#1351b4;margin:14px 0 6px;">$1</h5>');
  out = out.replace(/^## (.+)$/gm, '<h4 style="color:#1351b4;margin:16px 0 8px;">$1</h4>');
  out = out.replace(/^# (.+)$/gm, '<h3 style="color:#1351b4;margin:18px 0 8px;">$1</h3>');
  out = out.replace(/^[-*] (.+)$/gm, '<li style="margin-bottom:4px;">$1</li>');
  out = out.replace(/(<li[^>]*>.*<\/li>\n?)+/g, (m) => `<ul style="padding-left:20px;margin:8px 0;">${m}</ul>`);
  out = out.replace(/\n/g, '<br/>');
  return out;
}

/* ── Component ── */
const GeneralAnalysisResultDetailPage: React.FC = () => {
  const { resultId } = useParams<{ resultId: string }>();
  const navigate = useNavigate();

  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [criteria, setCriteria] = useState<CriterionResult[]>([]);
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reanalyzingKey, setReanalyzingKey] = useState<string | null>(null);

  useEffect(() => {
    document.title = 'AVALIA Code Quality System - Detalhe da Análise';
    loadDetail();
  }, [resultId]);

  const loadDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await analysisService.getAnalysisResults();
      if (!data.success || !data.results) throw new Error('Falha ao carregar resultados');

      const match = data.results.find((r: any) => String(r.id) === resultId);
      if (!match) { setError('Resultado não encontrado.'); setLoading(false); return; }

      setAnalysis(match);

      // Build criteria list
      const allCriteriaData = await criteriaService.getCriteria();
      const criteriaTextToIdMap = new Map<string, number>();
      allCriteriaData.forEach(c => {
        const numId = typeof c.id === 'string' ? parseInt(c.id.replace('criteria_', '')) : c.id;
        criteriaTextToIdMap.set(c.text, numId);
        const short = c.text.split(':')[0].trim();
        if (short !== c.text) criteriaTextToIdMap.set(short, numId);
      });

      const parsed: CriterionResult[] = Object.entries(match.criteria_results || {}).map(([key, val]: [string, any]) => {
        const name = val.name || `Critério ${key}`;
        const cid = criteriaTextToIdMap.get(name) || criteriaTextToIdMap.get(name.split(':')[0].trim());
        // Try matching the criterion to get original text
        const matchingCrit = allCriteriaData.find(c => {
          const numId = typeof c.id === 'string' ? parseInt(c.id.replace('criteria_', '')) : c.id;
          return numId === cid;
        });
        return {
          key,
          name: matchingCrit ? matchingCrit.text : name,
          content: val.content,
          status: parseStatus(val.content),
          confidence: parseConfidence(val.content),
          criteriaId: cid,
        };
      });

      setCriteria(parsed);
    } catch (err: any) {
      console.error('Erro ao carregar detalhe:', err);
      setError(err.message || 'Erro desconhecido');
    } finally {
      setLoading(false);
    }
  };

  const toggleRow = (key: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  const expandAll = () => {
    if (expandedRows.size === criteria.length) {
      setExpandedRows(new Set());
    } else {
      setExpandedRows(new Set(criteria.map(c => c.key)));
    }
  };

  /* ── Re-analyze a single criterion ── */
  const handleReanalyze = async (cr: CriterionResult) => {
    if (!cr.criteriaId || !analysis) return;
    const criteriaKey = `criteria_${cr.criteriaId}`;
    setReanalyzingKey(cr.key);
    try {
      // Get file paths
      const API_BASE_URL = (import.meta as any).env.VITE_API_BASE_URL || '/api/v1';
      let filePaths: string[] = [];
      try {
        const resp = await fetch(`${API_BASE_URL}/file-paths/dev-paths`);
        if (resp.ok) {
          const d = await resp.json();
          filePaths = d.file_paths?.map((fp: any) => typeof fp === 'string' ? fp : fp.full_path) || [];
        }
      } catch { /* fallback empty */ }

      if (filePaths.length === 0) {
        alert('Nenhum arquivo encontrado para reanálise.');
        return;
      }

      const request: AnalysisRequest = {
        criteria_ids: [criteriaKey],
        file_paths: filePaths,
        analysis_name: `Reanálise: ${cr.name}`,
        temperature: 0.7,
        max_tokens: 4000,
      };

      const response: AnalysisResponse = await analysisService.analyzeSelectedCriteria(request);
      const entry = Object.entries(response.criteria_results)[0];
      if (!entry) throw new Error('Sem resultado');

      const [, newVal] = entry;
      setCriteria(prev => prev.map(c => c.key === cr.key ? {
        ...c,
        content: newVal.content,
        status: parseStatus(newVal.content),
        confidence: parseConfidence(newVal.content),
      } : c));
    } catch (err) {
      console.error('Erro na reanálise:', err);
      alert('Erro ao reanalisar o critério.');
    } finally {
      setReanalyzingKey(null);
    }
  };

  /* ── DOCX export — same logic as existing GeneralAnalysisPage ── */
  const handleDownloadDocx = useCallback(() => {
    if (!analysis || criteria.length === 0) { alert('Nenhum resultado para exportar.'); return; }

    const currentDate = new Date().toLocaleDateString('pt-BR');
    const currentTime = new Date().toLocaleTimeString('pt-BR');
    const projectName = analysis.project_name || '';

    let content = `
      <html xmlns:o='urn:schemas-microsoft-com:office:office'
            xmlns:w='urn:schemas-microsoft-com:office:word'
            xmlns='http://www.w3.org/TR/REC-html40'>
      <head>
        <meta charset='utf-8'>
        <title>Relatório de Análise de Código</title>
        <style>
          @page Section1 { size:21cm 29.7cm; margin:1.2cm 1.5cm; mso-header-margin:1cm; mso-footer-margin:1cm; }
          div.Section1 { page:Section1; }
          body { font-family:'Calibri','Arial',sans-serif; font-size:11pt; line-height:1.4; margin:0; padding:0; }
          h1 { font-size:16pt; color:#2C5282; text-align:center; border-bottom:2pt solid #2C5282; padding-bottom:8pt; margin:0 0 15pt 0; }
          h2 { font-size:14pt; color:#2C5282; margin:15pt 0 8pt 0; }
          h3 { font-size:12pt; color:#2C5282; border-left:3pt solid #2C5282; padding-left:6pt; margin:12pt 0 6pt 0; }
          h4 { font-size:11pt; color:#2C5282; margin:8pt 0 4pt 0; }
          .header { text-align:center; margin-bottom:20pt; }
          .summary { background-color:#F7FAFC; padding:10pt; border:1pt solid #E2E8F0; margin-bottom:15pt; }
          .result-item { margin-bottom:15pt; page-break-inside:avoid; }
          .status-conforme { color:#38A169; font-weight:bold; }
          .status-parcial { color:#D69E2E; font-weight:bold; }
          .status-nao-conforme { color:#E53E3E; font-weight:bold; }
          .confidence { font-style:italic; color:#718096; }
          .footer { text-align:center; margin-top:20pt; font-size:10pt; color:#718096; border-top:1pt solid #E2E8F0; padding-top:8pt; }
          p { margin:4pt 0; }
        </style>
      </head>
      <body>
        <div class="Section1">
          <div class="header">
            <h1>Relatório de Análise de Código</h1>
            <h2>AVALIA Code Quality System</h2>
            ${projectName ? `<h3>Projeto: ${projectName}</h3>` : ''}
            <p>Gerado em: ${currentDate} às ${currentTime}</p>
          </div>
          <div class="summary">
            <h3>Resumo da Análise</h3>
            <p><strong>Análise:</strong> ${analysis.analysis_name}</p>
            <p><strong>Total de critérios analisados:</strong> ${criteria.length}</p>
            <p><strong>Critérios conformes:</strong> ${criteria.filter(r => r.status === 'compliant').length}</p>
            <p><strong>Critérios parcialmente conformes:</strong> ${criteria.filter(r => r.status === 'partially_compliant').length}</p>
            <p><strong>Critérios não conformes:</strong> ${criteria.filter(r => r.status === 'non_compliant').length}</p>
            <p><strong>Confiança média:</strong> ${Math.round(criteria.reduce((a, r) => a + r.confidence, 0) / criteria.length * 100)}%</p>
          </div>`;

    criteria.forEach((result, index) => {
      const statusClass = result.status === 'compliant' ? 'status-conforme' :
        result.status === 'partially_compliant' ? 'status-parcial' : 'status-nao-conforme';
      const statusText = result.status === 'compliant' ? 'Conforme' :
        result.status === 'partially_compliant' ? 'Parcialmente Conforme' : 'Não Conforme';

      let processedText = result.content;
      processedText = processedText.replace(/`([^`]+)`/g, '<code style="background-color:#e9ecef;padding:2px 4px;border-radius:3px;font-family:monospace;">$1</code>');
      processedText = processedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      processedText = processedText.replace(/\n/g, '<br>');

      content += `
        <div class="result-item">
          <h3>${index + 1}. ${result.name}</h3>
          <p><strong>Status:</strong> <span class="${statusClass}">${statusText}</span></p>
          <p><strong>Confiança:</strong> <span class="confidence">${Math.round(result.confidence * 100)}%</span></p>
          <div><h4>Avaliação</h4><div style="margin:0;">${processedText}</div></div>
        </div>`;
    });

    content += `
          <div class="footer">
            <p>Relatório gerado automaticamente pelo AVALIA Code Quality System</p>
            <p>Este relatório é confidencial e deve ser tratado de acordo com as políticas da organização.</p>
          </div>
        </div>
      </body></html>`;

    const blob = new Blob(['\ufeff', content], { type: 'application/msword' });
    const fileName = `relatorio-analise-codigo-${currentDate.replace(/\//g, '-')}.doc`;
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = fileName;
    link.click();
    URL.revokeObjectURL(link.href);
  }, [analysis, criteria]);

  const formatDate = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
        ' às ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch { return ts; }
  };

  // Stats
  const stats = {
    total: criteria.length,
    compliant: criteria.filter(c => c.status === 'compliant').length,
    partial: criteria.filter(c => c.status === 'partially_compliant').length,
    nonCompliant: criteria.filter(c => c.status === 'non_compliant').length,
  };

  /* ── Render ── */
  if (loading) {
    return (
      <div className="result-detail-page">
        <div className="result-detail-loading">
          <div className="spinner" />
          <p style={{ color: '#6c757d' }}>Carregando análise...</p>
        </div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="result-detail-page">
        <button className="result-detail-back" onClick={() => navigate('/general-analysis/results')}>
          <ArrowLeft size={16} /> Voltar para Resultados
        </button>
        <div className="result-detail-error">
          <XCircle size={48} style={{ marginBottom: 16 }} />
          <h3>{error || 'Resultado não encontrado'}</h3>
          <p>O resultado solicitado não está disponível.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="result-detail-page">
      {/* Back nav */}
      <button className="result-detail-back" onClick={() => navigate('/general-analysis/results')}>
        <ArrowLeft size={16} /> Voltar para Resultados
      </button>

      {/* Header Card */}
      <div className="result-detail-header">
        <div className="br-card">
          <div className="card-header">
            <h1 className="result-detail-title">{analysis.analysis_name || 'Análise'}</h1>
            <p className="result-detail-subtitle">
              <span><Calendar size={14} /> {formatDate(analysis.timestamp)}</span>
              {analysis.project_name && <span><FolderOpen size={14} /> {analysis.project_name}</span>}
              {analysis.model_used && <span>🤖 {analysis.model_used}</span>}
            </p>
          </div>
          <div className="card-content" style={{ padding: 0 }}>
            {/* Action Bar */}
            <div className="result-detail-actions">
              <button onClick={handleDownloadDocx} className="br-button primary" title="Baixar relatório DOCX">
                <Download size={16} style={{ marginRight: 8 }} />
                Baixar Relatório (DOCX)
              </button>
              <button onClick={() => window.print()} className="br-button secondary" title="Imprimir">
                <Printer size={16} style={{ marginRight: 8 }} />
                Imprimir
              </button>
              <button onClick={expandAll} className="br-button secondary" title="Expandir/Recolher todos">
                <ChevronDown size={16} style={{ marginRight: 8 }} />
                {expandedRows.size === criteria.length ? 'Recolher Todos' : 'Expandir Todos'}
              </button>
            </div>

            {/* Summary Stats */}
            <div className="result-detail-summary">
              <div className="summary-stat-card total">
                <div className="summary-stat-value">{stats.total}</div>
                <div className="summary-stat-label">Total</div>
              </div>
              <div className="summary-stat-card compliant">
                <div className="summary-stat-value">{stats.compliant}</div>
                <div className="summary-stat-label">Conforme</div>
              </div>
              <div className="summary-stat-card partial">
                <div className="summary-stat-value">{stats.partial}</div>
                <div className="summary-stat-label">Parcial</div>
              </div>
              <div className="summary-stat-card non-compliant">
                <div className="summary-stat-value">{stats.nonCompliant}</div>
                <div className="summary-stat-label">Não Conforme</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Criteria Results */}
      <div className="result-detail-criteria">
        <h2 className="result-detail-criteria-title">
          <FileText size={20} />
          Critérios Avaliados ({criteria.length})
        </h2>

        {criteria.map((cr, idx) => {
          const isExpanded = expandedRows.has(cr.key);
          const cssClass = getStatusCssClass(cr.status);

          return (
            <div key={cr.key} className="criterion-card">
              {/* Clickable header */}
              <div className="criterion-card-header" onClick={() => toggleRow(cr.key)}>
                <div className={`criterion-status-indicator ${cssClass}`}>
                  {getStatusIcon(cr.status)}
                </div>

                <div className="criterion-card-info">
                  <h4 className="criterion-card-name">{idx + 1}. {cr.name}</h4>
                  <div className="criterion-card-badge-row">
                    <span className={`criterion-badge ${cssClass}`}>
                      {getStatusText(cr.status)}
                    </span>
                    <span className="criterion-confidence">
                      Confiança: {Math.round(cr.confidence * 100)}%
                    </span>
                  </div>
                </div>

                <ChevronDown
                  size={20}
                  className={`criterion-expand-icon ${isExpanded ? 'expanded' : ''}`}
                />
              </div>

              {/* Expanded body */}
              {isExpanded && (
                <div className="criterion-card-body">
                  <div
                    className="criterion-assessment"
                    dangerouslySetInnerHTML={{ __html: formatAssessmentHTML(cr.content) }}
                  />
                  {cr.criteriaId && (
                    <button
                      className="criterion-reanalyze-btn"
                      onClick={() => handleReanalyze(cr)}
                      disabled={reanalyzingKey === cr.key}
                    >
                      <RefreshCw size={14} className={reanalyzingKey === cr.key ? 'animate-spin' : ''} />
                      {reanalyzingKey === cr.key ? 'Reanalisando...' : 'Reanalisar este Critério'}
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default GeneralAnalysisResultDetailPage;
