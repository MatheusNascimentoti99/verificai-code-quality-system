import React, { useState, useEffect, useRef, useCallback } from 'react';
// Função alternativa para gerar UUID sem dependência externa
const generateUUID = (): string => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};
import './PathList.css';

// @ts-ignore - Ignore TS error for env variable, Vite will replace this statically
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

interface FilePath {
  id: string;
  fullPath: string;
  fileName: string;
  fileExtension: string;
  folderPath: string;
  fileSize?: number;
  lastModified?: Date;
  created_at?: string;
  file?: File;
}

interface PathListProps {
  paths?: FilePath[];
  onLoadPaths?: (paths: FilePath[]) => void;
  autoRefresh?: boolean;
  onFolderSelect?: (paths: FilePath[]) => void;
  onError?: (error: string) => void;
  onSelectionComplete?: () => void;
}

const PathList: React.FC<PathListProps> = ({
  paths: initialPaths = [],
  onLoadPaths,
  autoRefresh = true,
  onFolderSelect,
  onError,
  onSelectionComplete
}) => {
  const [paths, setPaths] = useState<FilePath[]>(initialPaths);

  // Debug: Verificar estado inicial
  console.log('🔍 PathList montado com initialPaths:', initialPaths);
  console.log('🔍 initialPaths.length:', initialPaths.length);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [selectedFolderPath, setSelectedFolderPath] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [sortBy, setSortBy] = useState<'fileName' | 'fullPath' | 'fileSize' | 'lastModified'>('fileName');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Função para sincronizar file paths com o upload store
  const syncPathsToUploadStore = useCallback((filePaths: FilePath[]) => {
    try {
      // Limpar arquivos existentes no upload store
      // clearFiles(); // Removido temporariamente

      // Criar objetos File simulados para o upload store
      const mockFiles = filePaths.map(path => ({
        id: path.id,
        name: path.fileName,
        size: path.fileSize || 0,
        type: `application/${path.fileExtension}`,
        path: path.fullPath,
        status: 'completed' as const,
        progress: 100,
        uploadedAt: new Date()
      }));

      // Adicionar arquivos ao upload store simulando o uploadFiles
      mockFiles.forEach(mockFile => {
        // Usar o estado interno diretamente já que uploadFiles é assíncrono
        setPaths(prevPaths => [...prevPaths]);
      });

      console.log(`Sincronizados ${mockFiles.length} arquivos para o upload store`);
    } catch (error) {
      console.error('Erro ao sincronizar paths com upload store:', error);
    }
  }, []);

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getFileExtension = (fileName: string): string => {
    const parts = fileName.split('.');
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
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
        if (onError) onError('No files selected');
        return;
      }

      const relativePath = firstFile.webkitRelativePath || '';
      const folderPath = relativePath.split('/')[0] || 'selected_folder';
      console.log('Processing folder:', { folderPath, relativePath });

      // Store the complete folder path for display
      setSelectedFolderPath(folderPath);

      const IGNORED_DIRECTORIES = ['node_modules', 'venv', '.venv', '.git', '.idea', '.vscode', '__pycache__', '.pytest_cache', 'dist', 'build', '.next', 'bin', 'obj'];
      const ALLOWED_EXTENSIONS = ['js', 'jsx', 'ts', 'tsx', 'py', 'java', 'c', 'cpp', 'cxx', 'cc', 'h', 'hpp', 'cs', 'go', 'rs', 'rb', 'php', 'swift', 'kt', 'scala', 'm', 'sh', 'bash', 'zsh', 'sql', 'html', 'css', 'scss', 'sass', 'less', 'json', 'xml', 'yaml', 'yml', 'toml', 'ini', 'conf', 'config', 'md', 'txt'];

      console.log('Filtros ativos:', { ignored: IGNORED_DIRECTORIES, allowedExts: ALLOWED_EXTENSIONS.length });

      let skippedCount = 0;
      const filePaths: FilePath[] = [];
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const relativePath = file.webkitRelativePath || '';
        const pathParts = relativePath.split('/');
        const fileName = pathParts[pathParts.length - 1];
        const folderPath = pathParts.slice(0, -1).join('/');

        // Verificar se algum diretório no path deve ser ignorado
        const shouldIgnore = pathParts.some(part => IGNORED_DIRECTORIES.includes(part));
        const extension = getFileExtension(fileName);
        const isAllowedExtension = ALLOWED_EXTENSIONS.includes(extension);

        if (shouldIgnore || !isAllowedExtension) {
          skippedCount++;
          continue;
        }

        const relativePathForStorage = relativePath.startsWith(folderPath + '/')
          ? relativePath
          : `${folderPath}/${relativePath}`;

        const filePath: FilePath = {
          id: generateUUID(),
          fullPath: relativePathForStorage,
          fileName,
          fileExtension: extension,
          folderPath,
          fileSize: file.size,
          lastModified: new Date(file.lastModified),
          file: file
        };

        filePaths.push(filePath);

        // Atualizar progresso a cada 10 arquivos para performance
        if (i % 10 === 0 || i === files.length - 1) {
          setScanProgress(((i + 1) / files.length) * 100);
        }
      }

      console.log(`Scan concluído: ${filePaths.length} arquivos aceitos, ${skippedCount} ignorados.`);

      // Try to upload files and persist paths to database, but continue even if it fails
      try {
        console.log('Attempting to upload files and save paths to database...');
        const { getAuthHeaders } = await import('@/utils/auth');
        const authHeaders = getAuthHeaders();

        console.log('Auth headers:', { hasAuth: !!authHeaders.Authorization });

        if (authHeaders.Authorization) {
          // Upload files using the existing folder endpoint
          const formData = new FormData();

          // Add all files to FormData - the backend endpoint expects List[UploadFile]
          filePaths.forEach((filePath) => {
            if (filePath.file) {
              formData.append('files', filePath.file);
            }
          });

          const response = await fetch(`${API_BASE_URL}/upload/folder`, {
            method: 'POST',
            headers: {
              ...authHeaders
              // Don't set Content-Type header for FormData, let browser set it with boundary
            },
            body: formData
          });

          console.log('Database response:', {
            status: response.status,
            statusText: response.statusText
          });

          if (!response.ok) {
            if (response.status === 401) {
              console.warn('Authentication failed - continuing without upload');
            } else {
              const errorText = await response.text();
              console.error('Server error response:', errorText);
            }
          } else {
            const result = await response.json();
            console.log('Upload result:', result);

            if (result.failed_files && result.failed_files.length > 0) {
              console.warn('Some files could not be uploaded:', result.failed_files);
            }

            console.log(`Successfully uploaded ${result.total_uploaded} files`);

            // Call onFolderSelect with the uploaded files info
            if (onFolderSelect) {
              // Convert uploaded files to FilePath format for display
              const uploadedFilePaths: FilePath[] = result.uploaded_files.map((file: any) => ({
                id: file.id,
                fullPath: file.path, // Use the path from server
                fileName: file.name,
                fileExtension: file.name.split('.').pop() || '',
                folderPath: file.path.split('/').slice(0, -1).join('/'),
                fileSize: file.size,
                lastModified: new Date(file.upload_date),
                is_processed: true,
                processing_status: 'completed'
              }));
              onFolderSelect(uploadedFilePaths);
            }
          }
        } else {
          console.warn('No authentication token - skipping upload');
          // If no auth, still call onFolderSelect with local file info
          if (onFolderSelect) {
            onFolderSelect(filePaths);
          }
        }
      } catch (error) {
        console.warn('Error uploading files (continuing anyway):', error);
        // If upload fails, still call onFolderSelect with local file info
        if (onFolderSelect) {
          onFolderSelect(filePaths);
        }
      }

      // Refresh the file list to show uploaded files
      console.log('Refreshing file list after upload...');
      await loadPaths();

      // Notify that selection is complete to trigger list refresh
      if (onSelectionComplete) {
        onSelectionComplete();
      }

    } catch (error) {
      console.error('Error scanning folder:', error);
      if (onError) onError(error instanceof Error ? error.message : 'Failed to scan folder');
    } finally {
      setIsScanning(false);
      setScanProgress(0);
    }
  }, [onFolderSelect, onError, onSelectionComplete]);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('File input changed:', {
      files: e.target.files,
      fileCount: e.target.files?.length,
      firstFile: e.target.files?.[0]?.name
    });

    if (e.target.files && e.target.files.length > 0) {
      handleFolderSelect(e.target.files);
    } else {
      console.warn('No files selected');
      if (onError) onError('Nenhum arquivo selecionado. Por favor, escolha uma pasta com arquivos.');
    }
  };

  const loadPaths = async () => {
    try {
      console.log('🔍 PathList.loadPaths() - Iniciando carregamento...');
      setLoading(true);
      setError(null);

      const { getAuthHeaders, isAuthenticated } = await import('@/utils/auth');

      // Check if user is authenticated first
      if (!isAuthenticated()) {
        console.log('❌ Usuário não autenticado');
        setError('Por favor, faça login para ver os caminhos de arquivos.');
        return;
      }

      console.log('✅ Usuário autenticado, fazendo requisição para /api/v1/file-paths/');

      // Sync uploaded files to file_paths table first
      // REMOVIDO: Sync automático desativado para evitar duplicações
      // O backend já deve criar os registros necessários durante o upload

      const authHeaders = getAuthHeaders();
      console.log('🔑 Auth headers:', Object.keys(authHeaders));

      const requestUrl = `${API_BASE_URL}/file-paths/public`;
      console.log('🌐 Fazendo requisição para endpoint público (todos os arquivos):', requestUrl);
      console.log('📍 URL completa:', requestUrl);

      const response = await fetch(requestUrl);

      console.log('📡 Resposta da API:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Sessão expirada. Por favor, faça login novamente.');
        }
        throw new Error('Failed to load file paths');
      }

      const result = await response.json();
      console.log('📦 Dados recebidos da API:', result);

      // Transform backend response to frontend format
      // Public endpoint returns just strings (paths), so we need to create objects
      const transformedPaths = (result.file_paths || []).map((path: any, index: number) => {
        // If path is already an object (from our new public endpoint or other endpoints), keep structure
        if (typeof path === 'object' && path !== null) {
          const fullPath = path.full_path || path.fullPath || '';
          const fileName = path.file_name || path.fileName || fullPath.split(/[\\/]/).pop() || '';
          const fileExtension = path.file_extension || path.fileExtension || (fileName.includes('.') ? fileName.split('.').pop() : '');
          const folderPath = path.folder_path || path.folderPath || (fullPath.includes('/') ? fullPath.split('/')[0] : '');

          return {
            id: path.file_id || path.id || `path_${index}`,
            fullPath: fullPath,
            fileName: fileName,
            fileExtension: fileExtension || '',
            folderPath: folderPath,
            fileSize: path.file_size || path.fileSize,
            lastModified: path.last_modified || path.lastModified ? new Date(path.last_modified || path.lastModified) : undefined,
            created_at: path.created_at
          };
        }

        // If path is a string (from public endpoint), create object from string
        const pathStr = path as string;
        const fileName = pathStr.split('/').pop() || pathStr;
        const fileExtension = fileName.includes('.') ? fileName.split('.').pop() : '';

        return {
          id: `path_${index}`, // Generate unique ID
          fullPath: pathStr,
          fileName: fileName,
          fileExtension: fileExtension,
          folderPath: pathStr.includes('/') ? pathStr.split('/')[0] : '',
          fileSize: undefined, // Not available from public endpoint
          lastModified: undefined,
          created_at: undefined
        };
      });

      console.log('🔄 Paths transformados (TODOS OS ARQUIVOS):', transformedPaths.slice(0, 3)); // Show first 3 for debug
      console.log('📊 Total de paths:', transformedPaths.length);
      console.log('🔥🔥🔥 CARREGADOS TODOS OS ARQUIVOS - SEM LIMITE 🔥🔥🔥');
      console.log('🎯 Primeiro arquivo transformado:', transformedPaths[0]);

      setPaths(transformedPaths);

      if (onLoadPaths) {
        onLoadPaths(transformedPaths);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load paths';
      setError(errorMessage);
      console.error('❌ Error loading paths:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (autoRefresh) {
      loadPaths();
    }
  }, [autoRefresh]);

  const filteredAndSortedPaths = React.useMemo(() => {
    let filtered = paths;

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(path =>
        path.fileName.toLowerCase().includes(term) ||
        path.fullPath.toLowerCase().includes(term) ||
        path.fileExtension.toLowerCase().includes(term) ||
        path.folderPath.toLowerCase().includes(term)
      );
    }

    // Sort paths
    return filtered.sort((a, b) => {
      let aValue: any = a[sortBy];
      let bValue: any = b[sortBy];

      if (sortBy === 'fileSize') {
        aValue = aValue || 0;
        bValue = bValue || 0;
      }

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [paths, searchTerm, sortBy, sortOrder]);

  const handleSort = (column: typeof sortBy) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const handleFileSelect = (fileId: string) => {
    setSelectedFiles(prev => {
      const newSet = new Set(prev);
      if (newSet.has(fileId)) {
        newSet.delete(fileId);
      } else {
        newSet.add(fileId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedFiles.size === filteredAndSortedPaths.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(filteredAndSortedPaths.map(path => path.id)));
    }
  };

  const handleRemoveSelected = async () => {
    if (selectedFiles.size === 0) return;

    // Confirm before deletion
    const confirmMessage = `Tem certeza que deseja remover ${selectedFiles.size} arquivo(s) selecionados? Esta ação irá remover os arquivos do banco de dados e também deletar os arquivos físicos da pasta de uploads.`;
    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      const { getAuthHeaders } = await import('@/utils/auth');
      const authHeaders = getAuthHeaders();

      const response = await fetch(`${API_BASE_URL}/file-paths/`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders
        },
        body: JSON.stringify(Array.from(selectedFiles))
      });

      if (response.ok) {
        const result = await response.json();

        // Remove selected files from the local state
        setPaths(prev => prev.filter(path => !selectedFiles.has(path.id)));
        setSelectedFiles(new Set());

        // Show success message with details
        const message = result.errors && result.errors.length > 0
          ? `Removidos ${result.deleted_db_records} registros do banco de dados e ${result.deleted_physical_files} arquivos físicos. Alguns erros ocorreram: ${result.errors.join(', ')}`
          : `Removidos ${result.deleted_db_records} registros do banco de dados e ${result.deleted_physical_files} arquivos físicos com sucesso!`;

        alert(message);
        console.log('Remoção concluída:', result);
      } else {
        const errorText = await response.text();
        console.error('Erro ao remover arquivos selecionados:', errorText);
        alert('Erro ao remover arquivos selecionados. Por favor, tente novamente.');
      }
    } catch (error) {
      console.error('Erro ao remover arquivos selecionados:', error);
      alert('Erro ao remover arquivos selecionados. Por favor, tente novamente.');
    }
  };

  const handleRemoveFile = async (fileId: string) => {
    // Confirm before deletion
    if (!confirm('Tem certeza que deseja remover este arquivo? Esta ação irá remover o arquivo do banco de dados e também deletar o arquivo físico da pasta de uploads.')) {
      return;
    }

    try {
      const { getAuthHeaders } = await import('@/utils/auth');
      const authHeaders = getAuthHeaders();

      const response = await fetch(`${API_BASE_URL}/file-paths/`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders
        },
        body: JSON.stringify([fileId])
      });

      if (response.ok) {
        const result = await response.json();

        // Remove file from the local state
        setPaths(prev => prev.filter(path => path.id !== fileId));
        // Also remove from selected files if it was selected
        setSelectedFiles(prev => {
          const newSet = new Set(prev);
          newSet.delete(fileId);
          return newSet;
        });

        // Show success message with details
        const message = result.errors && result.errors.length > 0
          ? `Removido 1 registro do banco de dados e ${result.deleted_physical_files} arquivo(s) físico(s). Alguns erros ocorreram: ${result.errors.join(', ')}`
          : `Removido 1 registro do banco de dados e ${result.deleted_physical_files} arquivo(s) físico(s) com sucesso!`;

        alert(message);
        console.log('Remoção individual concluída:', result);
      } else {
        const errorText = await response.text();
        console.error('Erro ao remover arquivo:', errorText);
        alert('Erro ao remover arquivo. Por favor, tente novamente.');
      }
    } catch (error) {
      console.error('Erro ao remover arquivo:', error);
      alert('Erro ao remover arquivo. Por favor, tente novamente.');
    }
  };

  const handleHardReset = async () => {
    if (confirm('Tem certeza que deseja fazer um reset completo? Isso vai limpar todo o cache e recarregar a página.')) {
      console.log('🔄 Iniciando reset completo...');

      try {
        // Limpar localStorage
        console.log('🗑️ Limpando localStorage...');
        Object.keys(localStorage).forEach(key => {
          if (key.includes('auth') || key.includes('upload') || key.includes('file') || key.includes('path')) {
            console.log(`  Removendo: ${key}`);
            localStorage.removeItem(key);
          }
        });

        // Limpar sessionStorage
        console.log('🗑️ Limpando sessionStorage...');
        Object.keys(sessionStorage).forEach(key => {
          if (key.includes('auth') || key.includes('upload') || key.includes('file') || key.includes('path')) {
            console.log(`  Removendo: ${key}`);
            sessionStorage.removeItem(key);
          }
        });

        // Forçar reload da página
        console.log('🔄 Recarregando página...');
        window.location.reload();

      } catch (error) {
        console.error('❌ Erro durante reset:', error);
        alert('Erro durante o reset. Por favor, recarregue a página manualmente (F5).');
      }
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      // Optionally show a success message
    }).catch(err => {
      console.error('Failed to copy text:', err);
    });
  };

  const handleCleanupInvalid = async () => {
    if (!confirm('Tem certeza que deseja limpar os caminhos órfãos? Isso vai remover do banco de dados todos os arquivos que não existem mais no disco do servidor (útil se o servidor reiniciou).')) {
      return;
    }

    try {
      console.log('🧹 Limpando caminhos órfãos...');
      const { getAuthHeaders } = await import('@/utils/auth');
      const authHeaders = getAuthHeaders();

      const response = await fetch(`${API_BASE_URL}/file-paths/cleanup-invalid`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders
        }
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Limpeza concluída! Removidos: ${result.removed_count} arquivos órfãos. Mantidos: ${result.kept_count} arquivos válidos.`);
        // Recarregar a lista
        loadPaths();
      } else {
        const errorText = await response.text();
        console.error('Erro na limpeza:', errorText);
        alert('Erro ao limpar arquivos órfãos. Por favor, tente novamente.');
      }
    } catch (error) {
      console.error('Erro na limpeza:', error);
      alert('Erro ao limpar arquivos órfãos. Por favor, verifique a conexão.');
    }
  };

  const exportToCSV = () => {
    const csvContent = [
      ['File Path', 'File Name', 'Extension', 'Folder Path', 'Size', 'Modified'],
      ...filteredAndSortedPaths.map(path => [
        path.fullPath,
        path.fileName,
        path.fileExtension,
        path.folderPath,
        path.fileSize ? formatFileSize(path.fileSize) : '',
        path.lastModified ? formatDate(path.lastModified.toString()) : ''
      ])
    ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `file_paths_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Carregando caminhos de arquivos...</span>
        </div>
      </div>
    );
  }

  if (error) {
    const isAuthError = error.includes('login') || error.includes('Sessão expirada');
    return (
      <div className={`${isAuthError ? 'bg-blue-50 border-blue-200' : 'bg-red-50 border-red-200'} rounded-lg p-6`}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className={`text-sm font-medium ${isAuthError ? 'text-blue-800' : 'text-red-800'}`}>
              {isAuthError ? 'Autenticação necessária' : 'Erro ao carregar caminhos'}
            </h3>
            <p className={`text-sm ${isAuthError ? 'text-blue-600' : 'text-red-600'} mt-1`}>{error}</p>
          </div>
          {!isAuthError && (
            <button
              onClick={loadPaths}
              className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              Tentar novamente
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="path-list">
      {/* Hidden file input for folder selection */}
      <input
        // @ts-ignore - React typing doesn't officially support these standard HTML attributes for directory selection
        webkitdirectory="true"
        // @ts-ignore
        directory="true"
        ref={fileInputRef}
        id="folder-input"
        type="file"
        multiple
        className="hidden"
        onChange={handleFileInputChange}
        disabled={isScanning}
      />

      {/* Header */}
      <div className="path-list-header">
        <div className="br-card">
          <div className="card-header">
            <h2 className="text-h2">Caminhos de Arquivos</h2>
            <p className="text-regular">
              {filteredAndSortedPaths.length} arquivo(s) encontrado(s)
            </p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="path-list-controls">
        <div className="search-box">
          <input
            type="text"
            placeholder="Buscar arquivos..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="br-input"
          />
        </div>

        <div className="action-buttons">
          {/* Refresh button */}
          <button
            onClick={loadPaths}
            className="br-button secondary small"
            type="button"
            title="Atualizar lista de arquivos"
          >
            🔄 Atualizar
          </button>

          {/* Selection controls */}
          {filteredAndSortedPaths.length > 0 && (
            <div className="selection-controls">
              <button
                onClick={handleSelectAll}
                className="br-button secondary small"
                type="button"
              >
                {selectedFiles.size === filteredAndSortedPaths.length ? 'Desmarcar Todos' : 'Selecionar Todos'}
              </button>

              {selectedFiles.size > 0 && (
                <button
                  onClick={handleRemoveSelected}
                  className="br-button danger small"
                  type="button"
                >
                  Remover Selecionados ({selectedFiles.size})
                </button>
              )}
            </div>
          )}

          <button
            onClick={() => document.getElementById('folder-input')?.click()}
            disabled={isScanning}
            className="br-button"
            type="button"
          >
            {isScanning ? (
              <div className="flex items-center space-x-2">
                <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Selecionando...</span>
              </div>
            ) : (
              'Selecionar Pasta'
            )}
          </button>

          <button
            onClick={exportToCSV}
            disabled={filteredAndSortedPaths.length === 0}
            className="br-button secondary"
            type="button"
          >
            Exportar CSV
          </button>

          <button
            onClick={handleCleanupInvalid}
            className="br-button secondary"
            type="button"
            title="Remove registros de arquivos que não existem mais no servidor"
          >
            🧹 Limpar Órfãos
          </button>

          <button
            onClick={handleHardReset}
            className="br-button danger"
            type="button"
            title="Limpar completamente cache e recarregar"
          >
            🔄 Reset Completo
          </button>
        </div>
      </div>

      {/* Scanning Progress */}
      {isScanning && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-blue-800">
              Selecionando pasta...
            </h4>
            <span className="text-sm text-blue-600">
              {Math.round(scanProgress)}%
            </span>
          </div>

          <div className="w-full bg-blue-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${scanProgress}%` }}
            />
          </div>

          <p className="text-xs text-blue-600 mt-2">
            Extraindo caminhos dos arquivos e salvando no banco de dados...
          </p>
        </div>
      )}

      {/* Path List */}
      <div className="br-card">
        {filteredAndSortedPaths.length === 0 ? (
          <div className="empty-state">
            <p className="text-center">
              {searchTerm ? 'Nenhum arquivo encontrado para os termos de busca.' : 'Selecione uma pasta para começar.'}
            </p>
          </div>
        ) : (
          <div className="path-items">
            {filteredAndSortedPaths.map((path) => (
              <div key={path.id} className={`path-item ${selectedFiles.has(path.id) ? 'selected' : ''}`}>
                <div className="path-item-header">
                  <div className="path-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedFiles.has(path.id)}
                      onChange={() => handleFileSelect(path.id)}
                      className="br-checkbox"
                    />
                  </div>
                  <div className="path-content">
                    <code className="path-text">{path.fullPath}</code>
                    <div className="path-meta">
                      <span className="path-filename">{path.fileName}</span>
                      <span className="path-size">{path.fileSize ? formatFileSize(path.fileSize) : ''}</span>
                      <span className="path-extension">.{path.fileExtension}</span>
                    </div>
                  </div>
                </div>
                <div className="path-actions">
                  <button
                    onClick={() => copyToClipboard(path.fullPath)}
                    className="br-button circle small"
                    type="button"
                    title="Copiar caminho"
                  >
                    <svg className="br-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleRemoveFile(path.id)}
                    className="br-button circle small danger"
                    type="button"
                    title="Remover arquivo"
                  >
                    <svg className="br-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      {paths.length > 0 && (
        <div className="path-list-footer">
          <p className="text-center text-regular">
            Mostrando {filteredAndSortedPaths.length} de {paths.length} arquivos
          </p>
        </div>
      )}
    </div>
  );
};

export default PathList;