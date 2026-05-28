import React, { useState, useEffect } from 'react';
import { RefreshCw, Download, FileText, AlertCircle, Clock, Bot } from 'lucide-react';
import { analysisService } from '@/services/analysisService';

interface LatestLLMResponseData {
  success: boolean;
  message: string;
  response_content?: string;
  file_exists: boolean;
  file_size?: number;
  modified_time?: number;
  file_path?: string;
  model_used?: string;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
  };
}

const LatestLLMResponse: React.FC = () => {
  const [responseData, setResponseData] = useState<LatestLLMResponseData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadLatestResponse = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await analysisService.getLatestResponse();
      setResponseData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar resposta da LLM');
      console.error('Error loading latest LLM response:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLatestResponse();
  }, []);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString('pt-BR');
  };

  const downloadResponse = () => {
    if (!responseData?.response_content) return;

    const blob = new Blob([responseData.response_content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `llm_response_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="br-card">
        <div className="card-content">
          <div className="d-flex align-items-center justify-content-center" style={{ minHeight: '200px' }}>
            <RefreshCw className="animate-spin mr-2" />
            <span>Carregando resposta da LLM...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="br-card">
        <div className="card-content">
          <div className="d-flex align-items-center text-danger">
            <AlertCircle className="mr-2" />
            <span>Erro: {error}</span>
          </div>
        </div>
      </div>
    );
  }

  if (!responseData || !responseData.file_exists) {
    return (
      <div className="br-card">
        <div className="card-content">
          <div className="text-center py-5">
            <Bot className="mb-3" style={{ width: '48px', height: '48px', opacity: 0.5 }} />
            <h3 className="text-h3 mb-2">Nenhuma resposta encontrada</h3>
            <p className="text-regular text-muted mb-4">
              Execute uma análise primeiro para gerar uma resposta da LLM.
            </p>
            <button
              className="br-button primary"
              onClick={loadLatestResponse}
              type="button"
            >
              <RefreshCw className="mr-1" />
              Atualizar
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="br-card">
      <div className="card-header">
        <div className="d-flex justify-content-between align-items-center">
          <div>
            <h2 className="text-h2 mb-1">Última Resposta Recebida da LLM</h2>
            <div className="d-flex align-items-center text-muted text-small">
              <Clock className="mr-1" style={{ width: '14px', height: '14px' }} />
              <span>
                {responseData.modified_time ? formatDate(responseData.modified_time) : 'Data não disponível'}
              </span>
              {responseData.file_size && (
                <span className="ml-3">
                  Tamanho: {formatFileSize(responseData.file_size)}
                </span>
              )}
              {responseData.model_used && (
                <span className="ml-3">
                  Modelo: {responseData.model_used}
                </span>
              )}
            </div>
            {responseData.usage && (
              <div className="d-flex align-items-center text-muted text-small mt-1">
                {responseData.usage.input_tokens && (
                  <span className="mr-3">
                    Tokens de entrada: {responseData.usage.input_tokens.toLocaleString('pt-BR')}
                  </span>
                )}
                {responseData.usage.output_tokens && (
                  <span className="mr-3">
                    Tokens de saída: {responseData.usage.output_tokens.toLocaleString('pt-BR')}
                  </span>
                )}
                {responseData.usage.total_tokens && (
                  <span>
                    Total: {responseData.usage.total_tokens.toLocaleString('pt-BR')}
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="d-flex gap-2">
            <button
              className="br-button circle"
              onClick={loadLatestResponse}
              title="Atualizar"
              type="button"
            >
              <RefreshCw />
            </button>
            <button
              className="br-button circle"
              onClick={downloadResponse}
              title="Baixar resposta"
              type="button"
            >
              <Download />
            </button>
          </div>
        </div>
      </div>

      <div className="card-content">
        <div className="br-scrollbar" style={{ maxHeight: '600px', overflow: 'auto' }}>
          <div className="response-content" style={{
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            fontSize: '14px',
            lineHeight: '1.6',
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word',
            margin: 0,
            padding: '1rem',
            backgroundColor: '#f8f9fa',
            border: '1px solid #e9ecef',
            borderRadius: '4px'
          }}>
            {responseData.response_content}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LatestLLMResponse;