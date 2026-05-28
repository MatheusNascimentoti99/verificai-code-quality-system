import React, { useState } from 'react';

interface ManualPathInputProps {
  onPathAdded: (success: boolean) => void;
}

// @ts-ignore
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const ManualPathInput: React.FC<ManualPathInputProps> = ({ onPathAdded }) => {
  const [manualPath, setManualPath] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  const handleAddManualPath = async () => {
    if (!manualPath.trim()) {
      alert('Por favor, digite um caminho de arquivo.');
      return;
    }

    setIsAdding(true);
    try {
      // Simulate file extraction from path
      const pathParts = manualPath.replace(/\\/g, '/').split('/');
      const fileName = pathParts[pathParts.length - 1];
      const fileExtension = fileName.split('.').pop() || '';
      const folderPath = pathParts.slice(0, -1).join('/');

      const filePathData = {
        full_path: manualPath,
        file_name: fileName,
        file_extension: fileExtension,
        folder_path: folderPath,
        file_size: 0, // Will be updated by backend
        last_modified: new Date().toISOString()
      };

      const { getAuthHeaders } = await import('@/utils/auth');
      const authHeaders = getAuthHeaders();

      const response = await fetch(`${API_BASE_URL}/file-paths/bulk`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders
        },
        body: JSON.stringify({
          file_paths: [filePathData]
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Path added successfully:', result);
        setManualPath('');
        onPathAdded(true);

        if (result.errors && result.errors.length > 0) {
          console.warn('Some warnings:', result.errors);
        }
      } else {
        const errorText = await response.text();
        console.error('Error adding path:', errorText);
        alert(`Erro ao adicionar caminho: ${errorText}`);
        onPathAdded(false);
      }
    } catch (error) {
      console.error('Error adding path:', error);
      alert(`Erro ao adicionar caminho: ${error instanceof Error ? error.message : 'Unknown error'}`);
      onPathAdded(false);
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div className="manual-path-input mb-4">
      <div className="br-card">
        <div className="card-header">
          <h3 className="text-h3">Adicionar Caminho Manualmente</h3>
          <p className="text-regular text-gray-600">
            Digite o caminho completo do arquivo que deseja analisar
          </p>
        </div>
        <div className="card-body">
          <div className="flex gap-2">
            <input
              type="text"
              value={manualPath}
              onChange={(e) => setManualPath(e.target.value)}
              placeholder="Ex: C:\Users\seunome\projeto\arquivo.ts"
              className="br-input flex-1"
              disabled={isAdding}
            />
            <button
              onClick={handleAddManualPath}
              disabled={isAdding || !manualPath.trim()}
              className="br-button"
            >
              {isAdding ? (
                <div className="flex items-center space-x-2">
                  <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Adicionando...</span>
                </div>
              ) : (
                'Adicionar Caminho'
              )}
            </button>
          </div>
          <div className="mt-2 text-sm text-gray-500">
            <p><strong>Exemplos:</strong></p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li><code>C:\Users\seunome\projeto\src\arquivo.ts</code></li>
              <li><code>C:\Projects\meuprojeto\componentes\Componente.js</code></li>
              <li><code>/home/user/project/file.py</code></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ManualPathInput;