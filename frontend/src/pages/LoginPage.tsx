import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import './LoginPage.css';

const loginSchema = z.object({
  username: z.string().min(1, 'Nome de usuário é obrigatório'),
  password: z.string().min(1, 'Senha é obrigatória'),
});

type LoginFormData = z.infer<typeof loginSchema>;

const LoginPage: React.FC = () => {
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();
  const [loginError, setLoginError] = useState<string | null>(null);

  // Definir título da página
  React.useEffect(() => {
    document.title = 'AVALIA Code Quality System - Login';
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data);

      navigate('/dashboard', { replace: true });
    } catch (error: any) {
      console.log('ERRO LOGIN:', error);

      const message =
        error?.response?.data?.message ??
        error?.message ??
        'Não foi possível realizar o login.';

      setLoginError(message);
    }
  };

  return (
    <div className="login-page">
      {/* Logo and App Title */}
      <div className="login-left">
        <div className="logo-container">
          <div className="logo">
            <span className="logo-text">A</span>
          </div>
          <h1 className="app-title">
            AVAL<span style={{ color: '#EAB308' }}>IA</span>
          </h1>
          <p className="app-subtitle">Sistema de Qualidade de Código com IA</p>
        </div>
      </div>

      {/* Login Form */}
      <div className="login-right">
        <div className="login-form-container">
          <div className="br-card">
            <div className="card-header">
              <h2 className="text-h2">Entrar na sua conta</h2>
              <p className="text-regular">
                Digite suas credenciais para acessar o sistema
              </p>
            </div>
            <div className="card-content">
              <form onSubmit={handleSubmit(onSubmit)} className="login-form">
                <div className="form-group">
                  <label htmlFor="username" className="form-label">
                    Nome de usuário
                  </label>
                  <input
                    {...register('username')}
                    type="text"
                    id="username"
                    placeholder="Digite seu nome de usuário"
                    disabled={isLoading}
                    className={`form-input ${errors.username ? 'error' : ''}`}
                  />
                  {errors.username && (
                    <span className="error-message">
                      {errors.username.message}
                    </span>
                  )}
                </div>

                <div className="form-group">
                  <label htmlFor="password" className="form-label">
                    Senha
                  </label>
                  <input
                    {...register('password')}
                    type="password"
                    id="password"
                    placeholder="Digite sua senha"
                    disabled={isLoading}
                    className={`form-input ${errors.password ? 'error' : ''}`}
                  />
                  {errors.password && (
                    <span className="error-message">
                      {errors.password.message}
                    </span>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="login-button"
                >
                  {isLoading ? (
                    <>
                      <div className="loading-spinner"></div>
                      Entrando...
                    </>
                  ) : (
                    'Entrar'
                  )}
                </button>

                <div className="register-link">
                  <p className="text-regular">
                    Não tem uma conta?{' '}
                    <Link to="/register" className="link">
                      Registre-se
                    </Link>
                  </p>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {loginError && (
        <div
          className="login-modal-overlay"
          onClick={() => setLoginError(null)}
        >
          <div className="login-modal" onClick={(e) => e.stopPropagation()}>
            <div className="login-modal-header">
              <div className="login-modal-icon">⚠</div>

              <div>
                <h3>Falha na autenticação</h3>
                <p>Erro ao realizar login</p>
              </div>
            </div>

            <div className="login-modal-body">
              <p>{loginError}</p>
            </div>

            <div className="login-modal-footer">
              <button
                type="button"
                className="login-modal-button"
                onClick={() => setLoginError(null)}
              >
                Entendi
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoginPage;
