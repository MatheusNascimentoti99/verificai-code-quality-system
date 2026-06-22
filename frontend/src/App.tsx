import React from 'react';
import { Routes, Route, Navigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import LoginPage from '@/pages/LoginPage';
import PromptConfigPage from '@/pages/PromptConfigPage';
import CodeUploadPage from '@/pages/CodeUploadPage';
import GeneralAnalysisPage from '@/pages/GeneralAnalysisPage';
import GeneralAnalysisResultsPage from '@/pages/GeneralAnalysisResultsPage';
import GeneralAnalysisResultDetailPage from '@/pages/GeneralAnalysisResultDetailPage';
import ArchitecturalAnalysisPage from '@/pages/ArchitecturalAnalysisPage';
import BusinessAnalysisPage from '@/pages/BusinessAnalysisPage';
import DashboardPage from './pages/DashboardPage';

// Componente de proteção de rotas
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { isAuthenticated } = useAuthStore();

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

function App() {
  // Efeito para definir o título da página
  React.useEffect(() => {
    document.title = 'AVALIA Code Quality System';
  }, []);

  // Efeito para inicialização do aplicativo
  React.useEffect(() => {
    // Criar usuário de desenvolvimento para testes
    const devUser = {
      user: {
        id: 'dev-user-1',
        username: 'dev',
        email: 'dev@verificai.com',
        full_name: 'Developer User',
      },
      token: 'dev-token-12345',
      isAuthenticated: true,
      isLoading: false,
    };

    // Verificar se já existe um usuário autenticado
    const authData = localStorage.getItem('auth-storage');
    if (!authData) {
      // Criar usuário de desenvolvimento
      localStorage.setItem('auth-storage', JSON.stringify({ state: devUser }));
    } else {
      try {
        const parsed = JSON.parse(authData);
        // Verificar se há estado inválido (sem usuário ou token)
        if (!parsed.state?.user || !parsed.state?.token) {
          localStorage.setItem(
            'auth-storage',
            JSON.stringify({ state: devUser })
          );
        }
      } catch (error) {
        // Remover dados corrompidos e criar usuário de desenvolvimento
        localStorage.setItem(
          'auth-storage',
          JSON.stringify({ state: devUser })
        );
      }
    }
  }, []);

  return (
    <Routes>
      {/* Dashboard protegido */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />

      {/* Páginas de funcionalidades protegidas */}
      <Route
        path="/prompt-config"
        element={
          <ProtectedRoute>
            <PromptConfigPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/code-upload"
        element={
          <ProtectedRoute>
            <CodeUploadPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/general-analysis"
        element={
          <ProtectedRoute>
            <GeneralAnalysisPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/architectural-analysis"
        element={
          <ProtectedRoute>
            <ArchitecturalAnalysisPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/business-analysis"
        element={
          <ProtectedRoute>
            <BusinessAnalysisPage />
          </ProtectedRoute>
        }
      />
      <Route path="/prompt-config" element={
        <ProtectedRoute>
          <PromptConfigPage />
        </ProtectedRoute>
      } />
      <Route path="/code-upload" element={
        <ProtectedRoute>
          <CodeUploadPage />
        </ProtectedRoute>
      } />
      <Route path="/general-analysis/results/:resultId" element={
        <ProtectedRoute>
          <GeneralAnalysisResultDetailPage />
        </ProtectedRoute>
      } />
      <Route path="/general-analysis/results" element={
        <ProtectedRoute>
          <GeneralAnalysisResultsPage />
        </ProtectedRoute>
      } />
      <Route path="/general-analysis" element={
        <ProtectedRoute>
          <GeneralAnalysisPage />
        </ProtectedRoute>
      } />
      <Route path="/architectural-analysis" element={
        <ProtectedRoute>
          <ArchitecturalAnalysisPage />
        </ProtectedRoute>
      } />
      <Route path="/business-analysis" element={
        <ProtectedRoute>
          <BusinessAnalysisPage />
        </ProtectedRoute>
      } />

      {/* Login - acessível apenas se não estiver autenticado */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />

      {/* Redirecionar raiz para dashboard */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

// Componente para rotas públicas (redireciona se já estiver autenticado)
const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();

  return isAuthenticated ? (
    <Navigate to="/dashboard" replace />
  ) : (
    <>{children}</>
  );
};

export default App;
