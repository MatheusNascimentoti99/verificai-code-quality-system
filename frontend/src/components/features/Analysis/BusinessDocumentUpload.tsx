import React, { useState, useCallback, useRef } from 'react';
import { Upload, FileText, AlertCircle, CheckCircle, Trash2, RefreshCw, FolderOpen } from 'lucide-react';
import { useBusinessAnalysisStore } from '@/stores/businessAnalysisStore';
import './BusinessDocumentUpload.css';

interface DocumentInfo {
  id: string;
  name: string;
  type: 'user-story' | 'epic' | 'business-rule' | 'requirement';
  content: string;
  uploadDate: Date;
  metadata?: {
    fileSize: number;
    lastModified: Date;
    [key: string]: any;
  };
}

interface BusinessDocumentUploadProps {
  onDocumentsUploaded?: (documents: DocumentInfo[]) => void;
  onStartAnalysis?: () => void;
}

const BusinessDocumentUpload: React.FC<BusinessDocumentUploadProps> = ({
  onDocumentsUploaded,
  onStartAnalysis
}) => {
  const {
    businessDocuments,
    isUploading,
    uploadDocuments,
    deleteDocument,
    error
  } = useBusinessAnalysisStore();

  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [selectedFolderPath, setSelectedFolderPath] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (date: Date): string => {
    return new Date(date).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const determineDocumentType = (fileName: string, content: string): DocumentInfo['type'] => {
    const lowerFileName = fileName.toLowerCase();
    const lowerContent = content.toLowerCase();

    // Check filename patterns first
    if (lowerFileName.includes('user') && lowerFileName.includes('story')) return 'user-story';
    if (lowerFileName.includes('epic')) return 'epic';
    if (lowerFileName.includes('business') && (lowerFileName.includes('rule') || lowerFileName.includes('requirement'))) {
      return 'business-rule';
    }
    if (lowerFileName.includes('requirement')) return 'requirement';

    // Check content patterns
    if (lowerContent.includes('user story') || lowerContent.includes('como um')) return 'user-story';
    if (lowerContent.includes('epic') || lowerContent.includes('épico')) return 'epic';
    if (lowerContent.includes('business rule') || lowerContent.includes('regra de negócio')) return 'business-rule';
    if (lowerContent.includes('requirement') || lowerContent.includes('requisito')) return 'requirement';

    // Default to requirement if unsure
    return 'requirement';
  };

  const getDocumentTypeLabel = (type: DocumentInfo['type']): string => {
    switch (type) {
      case 'user-story': return 'User Story';
      case 'epic': return 'Épico';
      case 'business-rule': return 'Regra de Negócio';
      case 'requirement': return 'Requisito';
      default: return 'Documento';
    }
  };

  const getDocumentTypeIcon = (type: DocumentInfo['type']) => {
    return <FileText className="w-4 h-4" />;
  };

  const readFileContent = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        resolve(content);
      };
      reader.onerror = (e) => {
        reject(new Error('Failed to read file'));
      };
      reader.readAsText(file);
    });
  };

  const generateUUID = (): string => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  };

  const handleFolderSelect = useCallback(async (files: FileList) => {
    console.log('handleFolderSelect called with:', {
      fileCount: files.length,
      firstFileName: files[0]?.name,
      firstFilePath: files[0]?.webkitRelativePath
    });

    try {
      setIsScanning(true);
      setScanProgress(0);

      // Extract folder path from the first file
      const firstFile = files[0];
      if (!firstFile) {
        console.error('No files selected');
        return;
      }

      const relativePath = firstFile.webkitRelativePath || '';
      const folderPath = relativePath.split('/')[0] || 'selected_folder';
      console.log('Processing folder:', { folderPath, relativePath });
      setSelectedFolderPath(folderPath);

      // Process files to extract business document information
      const documents: DocumentInfo[] = [];

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const relativePath = file.webkitRelativePath || '';

        // Only process supported file types
        const fileName = file.name.toLowerCase();
        const supportedExtensions = ['.md', '.txt', '.pdf', '.docx', '.doc'];
        const isSupported = supportedExtensions.some(ext => fileName.endsWith(ext));

        if (!isSupported) {
          console.log(`Skipping unsupported file: ${file.name}`);
          setScanProgress(((i + 1) / files.length) * 100);
          continue;
        }

        try {
          const content = await readFileContent(file);

          // Determine document type based on filename or content
          const documentType = determineDocumentType(file.name, content);

          const document: DocumentInfo = {
            id: `doc_${generateUUID()}`,
            name: relativePath, // Use relative path to show folder structure
            type: documentType,
            content: content,
            uploadDate: new Date(),
            metadata: {
              fileSize: file.size,
              lastModified: new Date(file.lastModified),
              originalName: file.name,
              relativePath: relativePath,
              folderPath: folderPath
            }
          };

          documents.push(document);
          console.log(`Processed document: ${file.name} -> ${documentType}`);

        } catch (error) {
          console.error(`Error processing file ${file.name}:`, error);
        }

        // Update progress
        setScanProgress(((i + 1) / files.length) * 100);

        // Small delay to show progress
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      console.log(`Successfully processed ${documents.length} business documents from folder: ${folderPath}`);

      uploadDocuments(documents);
      onDocumentsUploaded?.(documents);

      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

    } catch (error) {
      console.error('Error processing folder:', error);
    } finally {
      setIsScanning(false);
      setScanProgress(0);
    }
  }, [uploadDocuments, onDocumentsUploaded]);

  const handleFileInputChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('File input changed:', {
      files: e.target.files,
      fileCount: e.target.files?.length,
      firstFile: e.target.files?.[0]?.name
    });

    if (e.target.files && e.target.files.length > 0) {
      await handleFolderSelect(e.target.files);
    }
  }, [handleFolderSelect]);

  
  const handleDeleteDocument = (documentId: string) => {
    deleteDocument(documentId);
  };

  const handleStartAnalysis = () => {
    if (businessDocuments.length === 0) {
      alert('Por favor, selecione uma pasta com documentos de negócio para análise.');
      return;
    }
    onStartAnalysis?.();
  };

  return (
    <div className="business-document-upload">
      {/* Header */}
      <div className="upload-header">
        <div className="br-card">
          <div className="card-header text-center">
            <h2 className="text-h2">Upload de Documentação Negocial</h2>
            <p className="text-regular">
              Selecione uma pasta contendo documentos de negócio para análise de alinhamento com o código-fonte
            </p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="upload-controls">
        <div className="action-buttons">
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isScanning}
            className="br-button primary"
            type="button"
          >
            {isScanning ? (
              <div className="flex items-center space-x-2">
                <div className="br-loading-small"></div>
                <span>Selecionando...</span>
              </div>
            ) : (
              <>
                <FolderOpen className="w-4 h-4 mr-2" />
                Selecionar Pasta
              </>
            )}
          </button>

          {/* Hidden file input for folder selection */}
          <input
            ref={fileInputRef}
            id="business-folder-input"
            type="file"
            // @ts-ignore
            webkitdirectory="true"
            // @ts-ignore
            directory="true"
            multiple
            className="hidden"
            onChange={handleFileInputChange}
            disabled={isScanning}
          />
        </div>
      </div>

      {/* Folder Path Display */}
      {selectedFolderPath && (
        <div className="folder-path-display">
          <div className="br-message info">
            <FolderOpen className="w-4 h-4" />
            <div>
              <strong>Pasta selecionada:</strong> {selectedFolderPath}
              <p className="text-small mt-1">
                {businessDocuments.length} documento(s) de negócio encontrados
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Upload Area or Documents List */}
      {businessDocuments.length === 0 && (
        <div className="upload-area">
          <div className="br-card">
            <div className="card-content">
              {isScanning ? (
                <div className="scanning-state">
                  <div className="br-loading"></div>
                  <h4>Processando documentos da pasta...</h4>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${scanProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-small">{Math.round(scanProgress)}% concluído</p>
                  {selectedFolderPath && (
                    <p className="text-small text-muted mt-2">
                      Pasta: {selectedFolderPath}
                    </p>
                  )}
                </div>
              ) : (
                <div className="upload-prompt">
                  <FolderOpen className="upload-icon" />
                  <h4>Selecione uma pasta de documentos de negócio</h4>
                  <p>Clique no botão "Selecionar Pasta" para continuar</p>
                  <p className="text-small">
                    Serão processados arquivos: .md, .txt, .pdf, .docx, .doc
                  </p>
                  <p className="text-small">
                    Formatos detectados: User Stories, Épicos, Regras de Negócio, Requisitos
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      {businessDocuments.length > 0 && (
        <div className="documents-list">
          <div className="br-card">
            <div className="card-header">
              <h3 className="text-h3">
                Documentos de Negócio ({businessDocuments.length})
              </h3>
              <p className="text-regular">
                Documentos encontrados na pasta selecionada
              </p>
            </div>

            <div className="card-content">
              {error && (
                <div className="br-message danger mb-3">
                  <AlertCircle className="w-4 h-4" />
                  <span>{error}</span>
                </div>
              )}

              <div className="document-items">
                {businessDocuments.map((doc) => (
                  <div key={doc.id} className="document-item">
                    <div className="document-info">
                      <div className="document-details">
                        <div className="document-header">
                          {getDocumentTypeIcon(doc.type)}
                          <div className="document-name-container">
                            <span className="document-name">{doc.name}</span>
                            {doc.metadata?.originalName && doc.metadata.originalName !== doc.name && (
                              <span className="original-name">
                                ({doc.metadata.originalName})
                              </span>
                            )}
                          </div>
                          <span className={`document-type-badge type-${doc.type}`}>
                            {getDocumentTypeLabel(doc.type)}
                          </span>
                        </div>

                        <div className="document-meta">
                          <span className="text-small text-muted">
                            {formatFileSize(doc.metadata?.fileSize || 0)}
                          </span>
                          <span className="text-small text-muted">
                            {formatDate(doc.uploadDate)}
                          </span>
                          {doc.metadata?.folderPath && (
                            <span className="text-small text-muted">
                              Pasta: {doc.metadata.folderPath}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Analysis Actions */}
              <div className="analysis-actions">
                <div className="action-buttons">
                  <button
                    className="br-button secondary"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isScanning}
                  >
                    <FolderOpen className="w-4 h-4 mr-2" />
                    Selecionar Outra Pasta
                  </button>

                  <button
                    className="br-button primary"
                    onClick={handleStartAnalysis}
                    disabled={businessDocuments.length === 0 || isUploading}
                  >
                    {isUploading ? 'Analisando...' : 'Iniciar Análise de Negócio'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BusinessDocumentUpload;