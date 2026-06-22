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
      <div className="login-page__left">
        <div className="login-page__logo-container">
          <div className="login-page__logo">
            <span className="login-page__logo-text">A</span>
          </div>

          <h1 className="login-page__title">
            AVAL<span style={{ color: '#EAB308' }}>IA</span>
          </h1>

          <p className="login-page__subtitle">
            Sistema de Qualidade de Código com IA
          </p>
        </div>
      </div>

      <div className="login-page__right">
        <div className="login-page__form-container">
          <div className="login-card">
            <div className="login-card__header">
              <h2 className="login-card__title">Entrar na sua conta</h2>

              <p className="login-card__description">
                Digite suas credenciais para acessar o sistema
              </p>
            </div>

            <div className="login-card__content">
              <form onSubmit={handleSubmit(onSubmit)} className="login-form">
                <div className="login-form__group">
                  <label htmlFor="username" className="login-form__label">
                    Nome de usuário
                  </label>

                  <input
                    {...register('username')}
                    type="text"
                    id="username"
                    placeholder="Digite seu nome de usuário"
                    disabled={isLoading}
                    className={`login-form__input ${
                      errors.username ? 'login-form__input--error' : ''
                    }`}
                  />

                  {errors.username && (
                    <span className="login-form__error-message">
                      {errors.username.message}
                    </span>
                  )}
                </div>

                <div className="login-form__group">
                  <label htmlFor="password" className="login-form__label">
                    Senha
                  </label>

                  <input
                    {...register('password')}
                    type="password"
                    id="password"
                    placeholder="Digite sua senha"
                    disabled={isLoading}
                    className={`login-form__input ${
                      errors.password ? 'login-form__input--error' : ''
                    }`}
                  />

                  {errors.password && (
                    <span className="login-form__error-message">
                      {errors.password.message}
                    </span>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="login-form__submit-button"
                >
                  {isLoading ? (
                    <>
                      <div className="login-form__spinner" />
                      Entrando...
                    </>
                  ) : (
                    'Entrar'
                  )}
                </button>

                <div className="login-form__register">
                  <p className="login-form__register-text">
                    Não tem uma conta?{' '}
                    <Link to="/register" className="login-form__register-link">
                      Registre-se
                    </Link>
                  </p>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>

      {loginError && (
        <div className="login-modal" onClick={() => setLoginError(null)}>
          <div
            className="login-modal__container"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="login-modal__header">
              <div className="login-modal__icon">⚠</div>

              <div>
                <h3 className="login-modal__title">Falha na autenticação</h3>

                <p className="login-modal__subtitle">Erro ao realizar login</p>
              </div>
            </div>

            <div className="login-modal__body">
              <p>{loginError}</p>
            </div>

            <div className="login-modal__footer">
              <button
                type="button"
                className="login-modal__button"
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
