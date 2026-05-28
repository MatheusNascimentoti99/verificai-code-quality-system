import React, { useState, useCallback, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';

// @ts-ignore
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

interface FilePath {
  id: string;
  fullPath: string;
  fileName: string;
  fileExtension: string;
  folderPath: string;
  fileSize?: number;
  lastModified?: Date;
}

interface FolderSelectorProps {
  onFolderSelect: (paths: FilePath[]) => void;
  onError: (error: string) => void;
  onSelectionComplete?: () => void;
  disabled?: boolean;
}

const FolderSelector: React.FC<FolderSelectorProps> = ({
  onFolderSelect,
  onError,
  onSelectionComplete,
  disabled = false
}) => {
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanningPath, setScanningPath] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileExtension = (fileName: string): string => {
    const parts = fileName.split('.');
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
  };

  const scanFolderRecursively = async (folderPath: string): Promise<FilePath[]> => {
    const filePaths: FilePath[] = [];

    try {
      // Create a virtual folder structure for demo purposes
      // In a real implementation, this would use the File System Access API
      const demoFiles = [
        `${folderPath}/src/index.js`,
        `${folderPath}/src/components/App.js`,
        `${folderPath}/src/utils/helpers.js`,
        `${folderPath}/package.json`,
        `${folderPath}/README.md`,
        `${folderPath}/src/styles/main.css`,
        `${folderPath}/src/components/Header.js`,
        `${folderPath}/src/components/Footer.js`,
        `${folderPath}/src/hooks/useApi.js`,
        `${folderPath}/src/services/api.js`
      ];

      for (let i = 0; i < demoFiles.length; i++) {
        const fullPath = demoFiles[i];
        const pathParts = fullPath.split('/');
        const fileName = pathParts[pathParts.length - 1];
        const folderPath = pathParts.slice(0, -1).join('/');

        const filePath: FilePath = {
          id: uuidv4(),
          fullPath,
          fileName,
          fileExtension: getFileExtension(fileName),
          folderPath,
          fileSize: Math.floor(Math.random() * 50000) + 1000, // Random size for demo
          lastModified: new Date()
        };

        filePaths.push(filePath);

        // Update progress
        setScanProgress(((i + 1) / demoFiles.length) * 100);

        // Small delay to show progress
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      return filePaths;
    } catch (error) {
      console.error('Error scanning folder:', error);
      throw new Error('Failed to scan folder');
    }
  };

  const handleFolderSelect = useCallback(async (files: FileList) => {
    console.log('handleFolderSelect called with:', {
      fileCount: files.length,
      firstFileName: files[0]?.name,
      firstFilePath: files[0]?.webkitRelativePath
    });

    if (disabled) return;

    try {
      setIsScanning(true);
      setScanProgress(0);

      // Extract folder path from the first file
      const firstFile = files[0];
      if (!firstFile) {
        onError('No files selected');
        return;
      }

      const relativePath = firstFile.webkitRelativePath || '';
      const folderPath = relativePath.split('/')[0] || 'selected_folder';
      console.log('Processing folder:', { folderPath, relativePath });
      setScanningPath(folderPath);

      // Process files to extract path information
      const filePaths: FilePath[] = [];

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const relativePath = file.webkitRelativePath || '';
        const pathParts = relativePath.split('/');
        const fileName = pathParts[pathParts.length - 1];
        const folderPath = pathParts.slice(0, -1).join('/');

        const filePath: FilePath = {
          id: uuidv4(),
          fullPath: relativePath,
          fileName,
          fileExtension: getFileExtension(fileName),
          folderPath,
          fileSize: file.size,
          lastModified: new Date(file.lastModified)
        };

        filePaths.push(filePath);

        // Update progress
        setScanProgress(((i + 1) / files.length) * 100);

        // Small delay to show progress
        await new Promise(resolve => setTimeout(resolve, 50));
      }

      // Try to persist paths to database, but continue even if it fails
      try {
        console.log('Attempting to save paths to database...');
        const { getAuthHeaders } = await import('@/utils/auth');
        const authHeaders = getAuthHeaders();

        console.log('Auth headers:', { hasAuth: !!authHeaders.Authorization });

        if (authHeaders.Authorization) {
          const transformedFilePaths = filePaths.map(path => ({
            full_path: path.fullPath,
            file_name: path.fileName,
            file_extension: path.fileExtension,
            folder_path: path.folderPath,
            file_size: path.fileSize,
            last_modified: path.lastModified?.toISOString()
          }));

          const response = await fetch(`${API_BASE_URL}/file-paths/bulk`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...authHeaders
            },
            body: JSON.stringify({
              file_paths: transformedFilePaths
            })
          });

          console.log('Database response:', {
            status: response.status,
            statusText: response.statusText
          });

          if (!response.ok) {
            if (response.status === 401) {
              console.warn('Authentication failed - continuing without database save');
            } else {
              const errorText = await response.text();
              console.error('Server error response:', errorText);
            }
          } else {
            const result = await response.json();
            console.log('Save result:', result);

            if (result.errors && result.errors.length > 0) {
              console.warn('Some paths could not be saved:', result.errors);
            }
          }
        } else {
          console.warn('No authentication token - skipping database save');
        }
      } catch (error) {
        console.warn('Error saving file paths (continuing anyway):', error);
      }

      // Always call onFolderSelect, even if database save failed
      onFolderSelect(filePaths);

      // Notify that selection is complete to trigger list refresh
      if (onSelectionComplete) {
        onSelectionComplete();
      }

    } catch (error) {
      console.error('Error scanning folder:', error);
      onError(error instanceof Error ? error.message : 'Failed to scan folder');
    } finally {
      setIsScanning(false);
      setScanProgress(0);
      setScanningPath('');
    }
  }, [disabled, onFolderSelect, onError, onSelectionComplete]);

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
      onError('Nenhum arquivo selecionado. Por favor, escolha uma pasta com arquivos.');
    }
  };

  return (
    <div className="space-y-4">
      {/* Folder Selection Interface */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-gray-400 transition-colors">
        <input
          ref={fileInputRef}
          id="folder-input"
          type="file"
          // @ts-ignore
          webkitdirectory="true"
          // @ts-ignore
          directory="true"
          multiple
          className="hidden"
          onChange={handleFileInputChange}
          disabled={disabled || isScanning}
        />

        <div className="text-center">
          <button
            type="button"
            disabled={disabled || isScanning}
            onClick={() => document.getElementById('folder-input')?.click()}
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isScanning ? (
              <div className="flex items-center space-x-2">
                <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Escaneando...</span>
              </div>
            ) : (
              'Selecionar Pasta'
            )}
          </button>
        </div>
      </div>

      {/* Scanning Progress */}
      {isScanning && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-blue-800">
              Escaneando pasta: {scanningPath}
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

    </div>
  );
};

export default FolderSelector;