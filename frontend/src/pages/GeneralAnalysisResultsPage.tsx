import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  FileText,
  Trash2,
  Calendar,
  FolderOpen,
  ChevronRight,
  AlertCircle,
  BarChart3,
  RefreshCw,
} from 'lucide-react';
import { analysisService } from '@/services/analysisService';
import './GeneralAnalysisResultsPage.css';

interface AnalysisResultSummary {
  id: number;
  analysis_name: string;
  project_name?: string;
  timestamp: string;
  criteria_results: Record<string, { name: string; content: string }>;
  model_used?: string;
}

/**
 * Parse the status from a criterion content string using the same logic
 * as GeneralAnalysisPage.
 */
function parseStatus(content: string): 'compliant' | 'partially_compliant' | 'non_compliant' {
  const statusMatch = content.match(/\*\*Status:\*\*\s*([^*\n]+)/i);
  if (statusMatch) {
    const statusText = statusMatch[1].trim().toLowerCase();
    if (statusText === 'não conforme' || statusText === 'nao conforme' ||
      statusText.startsWith('não conforme') || statusText.startsWith('nao conforme')) {
      return 'non_compliant';
    }
    if (statusText === 'parcialmente conforme' || statusText.startsWith('parcialmente conforme')) {
      return 'partially_compliant';
    }
    if (statusText === 'conforme' || statusText.startsWith('conforme')) {
      return 'compliant';
    }
    if (statusText.includes('não conforme') || statusText.includes('nao conforme')) return 'non_compliant';
    if (statusText.includes('parcialmente conforme')) return 'partially_compliant';
    if (statusText.includes('conforme') && !statusText.includes('não') && !statusText.includes('nao')) return 'compliant';
  }
  // Fallback keyword search
  const lower = content.toLowerCase();
  if (lower.includes('não atende') || lower.includes('não cumpre') || lower.includes('viol') || lower.includes('defeito')) return 'non_compliant';
  if (lower.includes('parcialmente') || lower.includes('atende parcialmente') || lower.includes('precisa melhorar')) return 'partially_compliant';
  return 'compliant';
}

function parseConfidence(content: string): number {
  const match = content.match(/(confiança|confidence)[^\d]*(\d+(?:\.\d+)?)/i);
  if (match) {
    const v = parseFloat(match[2]);
    return v > 1.0 ? Math.min(v / 100, 1.0) : Math.min(v, 1.0);
  }
  return 0.8;
}

interface CardStats {
  total: number;
  compliant: number;
  partial: number;
  nonCompliant: number;
  avgConfidence: number;
}

function computeStats(criteriaResults: Record<string, { name: string; content: string }>): CardStats {
  const entries = Object.values(criteriaResults);
  let compliant = 0, partial = 0, nonCompliant = 0, confidenceSum = 0;
  entries.forEach(({ content }) => {
    const s = parseStatus(content);
    if (s === 'compliant') compliant++;
    else if (s === 'partially_compliant') partial++;
    else nonCompliant++;
    confidenceSum += parseConfidence(content);
  });
  return {
    total: entries.length,
    compliant,
    partial,
    nonCompliant,
    avgConfidence: entries.length > 0 ? confidenceSum / entries.length : 0,
  };
}

const GeneralAnalysisResultsPage: React.FC = () => {
  const navigate = useNavigate();
  const [results, setResults] = useState<AnalysisResultSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    document.title = 'AVALIA Code Quality System - Resultados de Análise';
    loadResults();
  }, []);

  const loadResults = async () => {
    setLoading(true);
    try {
      const data = await analysisService.getAnalysisResults();
      if (data.success && data.results) {
        setResults(data.results);
      } else {
        setResults([]);
      }
    } catch (err) {
      console.error('Erro ao carregar resultados:', err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteResult = async (e: React.MouseEvent, resultId: number) => {
    e.stopPropagation(); // Don't navigate
    if (!confirm('Tem certeza que deseja excluir este resultado? Esta ação não pode ser desfeita.')) return;
    try {
      await analysisService.deleteAnalysisResult(resultId);
      setResults(prev => prev.filter(r => r.id !== resultId));
    } catch (err) {
      console.error('Erro ao excluir resultado:', err);
      alert('Erro ao excluir resultado.');
    }
  };

  const handleDeleteAll = async () => {
    if (!confirm('Tem certeza que deseja excluir TODOS os resultados? Esta ação não pode ser desfeita.')) return;
    try {
      await analysisService.deleteAllAnalysisResults();
      setResults([]);
    } catch (err) {
      console.error('Erro ao excluir todos:', err);
      alert('Erro ao excluir resultados.');
    }
  };

  const formatDate = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }) +
        ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return ts;
    }
  };

  // ─── Render ───
  return (
    <div className="results-list-page">
      {/* Header */}
      <div className="results-list-header">
        <div className="br-card">
          <div className="card-header">
            <h1 className="text-h1">Histórico de Análises</h1>
            <p className="text-regular">
              Visualize todos os resultados de análises realizadas, acesse detalhes e exporte relatórios
            </p>
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="results-toolbar">
        <div className="results-toolbar-left">
          <Link to="/general-analysis" className="result-detail-back">
            <ArrowLeft size={16} />
            Voltar para Análise
          </Link>
          <span style={{ color: '#ced4da' }}>|</span>
          <span>
            <BarChart3 size={16} style={{ verticalAlign: 'text-bottom', marginRight: 4 }} />
            {results.length} resultado{results.length !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="results-toolbar-right">
          <button onClick={loadResults} className="br-button secondary" title="Recarregar">
            <RefreshCw size={16} />
          </button>
          {results.length > 0 && (
            <button onClick={handleDeleteAll} className="br-button danger" title="Excluir todos">
              <Trash2 size={16} style={{ marginRight: 6 }} />
              Excluir Todos
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="results-skeleton">
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton-card">
              <div className="skeleton-line medium" />
              <div className="skeleton-line short" />
              <div className="skeleton-stats">
                <div className="skeleton-stat" />
                <div className="skeleton-stat" />
                <div className="skeleton-stat" />
              </div>
            </div>
          ))}
        </div>
      ) : results.length === 0 ? (
        <div className="results-empty">
          <AlertCircle size={56} className="results-empty-icon" />
          <h3>Nenhum resultado encontrado</h3>
          <p>Execute uma análise na página de critérios para ver os resultados aqui.</p>
          <Link to="/general-analysis" className="br-button primary">
            <FileText size={16} style={{ marginRight: 8 }} />
            Ir para Análise
          </Link>
        </div>
      ) : (
        <div className="results-grid">
          {results.map(result => {
            const stats = computeStats(result.criteria_results || {});
            return (
              <div
                key={result.id}
                className="result-card"
                onClick={() => navigate(`/general-analysis/results/${result.id}`)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && navigate(`/general-analysis/results/${result.id}`)}
              >
                {/* Card Header */}
                <div className="result-card-header">
                  <div>
                    <h3 className="result-card-title">
                      {result.analysis_name || 'Análise sem nome'}
                    </h3>
                    <div className="result-card-meta">
                      <span className="result-card-meta-item">
                        <Calendar size={13} />
                        {formatDate(result.timestamp)}
                      </span>
                      {result.model_used && (
                        <span className="result-card-meta-item">
                          🤖 {result.model_used}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="result-card-actions">
                    <button
                      className="result-card-delete-btn"
                      onClick={(e) => handleDeleteResult(e, result.id)}
                      title="Excluir resultado"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                {/* Card Body */}
                <div className="result-card-body">
                  {result.project_name && (
                    <div className="result-card-project">
                      <FolderOpen size={14} />
                      {result.project_name}
                    </div>
                  )}
                  <div className="result-card-stats">
                    <div className="result-stat compliant">
                      <div className="result-stat-value">{stats.compliant}</div>
                      <div className="result-stat-label">Conforme</div>
                    </div>
                    <div className="result-stat partial">
                      <div className="result-stat-value">{stats.partial}</div>
                      <div className="result-stat-label">Parcial</div>
                    </div>
                    <div className="result-stat non-compliant">
                      <div className="result-stat-value">{stats.nonCompliant}</div>
                      <div className="result-stat-label">Não Conf.</div>
                    </div>
                  </div>
                </div>

                {/* Card Footer */}
                <div className="result-card-footer">
                  <span className="result-card-confidence">
                    Confiança média: <strong>{Math.round(stats.avgConfidence * 100)}%</strong>
                  </span>
                  <span className="result-card-view-link">
                    Ver detalhes <ChevronRight size={14} />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default GeneralAnalysisResultsPage;
