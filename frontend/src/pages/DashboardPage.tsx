import React from 'react';
import { Link } from 'react-router-dom';
import './DashboardPage.css';
import { useAuth } from '@/hooks/useAuth';
import {
  Briefcase,
  Building2,
  ChartColumn,
  FolderUp,
  Settings,
} from 'lucide-react';

const DashboardPage: React.FC = () => {
  const { logout } = useAuth();

  return (
    <div className="dashboard-page">
      <div className="dashboard-page__header">
        <div className="dashboard-card">
          <div className="dashboard-card__header">
            <h1 className="dashboard-card__title">
              Bem-vindo ao AVAL<span style={{ color: '#EAB308' }}>IA</span>!
            </h1>

            <p className="dashboard-card__description">
              Sistema de Qualidade de Código com IA
            </p>
          </div>
        </div>
      </div>

      <div className="dashboard-page__content">
        <div className="dashboard-card">
          <div className="dashboard-card__content">
            <div className="dashboard-features">
              <Link to="/prompt-config" className="dashboard-feature-card">
                <span className="dashboard-feature-card__icon">
                  <Settings />
                </span>

                <h3 className="dashboard-feature-card__title">
                  Configuração de Prompts
                </h3>

                <p className="dashboard-feature-card__description">
                  Configure e gerencie os prompts de análise de código
                </p>
              </Link>

              <Link to="/code-upload" className="dashboard-feature-card">
                <span className="dashboard-feature-card__icon">
                  <FolderUp />
                </span>

                <h3 className="dashboard-feature-card__title">
                  Upload de Código
                </h3>

                <p className="dashboard-feature-card__description">
                  Faça upload dos arquivos de código para análise
                </p>
              </Link>

              <Link to="/general-analysis" className="dashboard-feature-card">
                <span className="dashboard-feature-card__icon">
                  <ChartColumn />
                </span>

                <h3 className="dashboard-feature-card__title">Análise Geral</h3>

                <p className="dashboard-feature-card__description">
                  Análise de código baseada em critérios gerais de qualidade
                </p>
              </Link>

              <Link
                to="/architectural-analysis"
                className="dashboard-feature-card"
              >
                <span className="dashboard-feature-card__icon">
                  <Building2 />
                </span>

                <h3 className="dashboard-feature-card__title">
                  Análise Arquitetural
                </h3>

                <p className="dashboard-feature-card__description">
                  Avaliação da arquitetura e estrutura do projeto
                </p>
              </Link>

              <Link to="/business-analysis" className="dashboard-feature-card">
                <span className="dashboard-feature-card__icon">
                  <Briefcase />
                </span>

                <h3 className="dashboard-feature-card__title">
                  Análise de Negócio
                </h3>

                <p className="dashboard-feature-card__description">
                  Análise de impacto e valor de negócio do código
                </p>
              </Link>
            </div>

            <div className="dashboard-feature-list">
              <div className="dashboard-feature-list__container">
                <Link
                  to="/prompt-config"
                  className="dashboard-feature-list__item"
                >
                  <span className="dashboard-feature-list__icon">⚙️</span>

                  <span className="dashboard-feature-list__text">
                    Configuração de Prompts
                  </span>
                </Link>

                <Link
                  to="/code-upload"
                  className="dashboard-feature-list__item"
                >
                  <span className="dashboard-feature-list__icon">📁</span>

                  <span className="dashboard-feature-list__text">
                    Upload de Código
                  </span>
                </Link>

                <Link
                  to="/general-analysis"
                  className="dashboard-feature-list__item"
                >
                  <span className="dashboard-feature-list__icon">📊</span>

                  <span className="dashboard-feature-list__text">
                    Análise Geral
                  </span>
                </Link>

                <Link
                  to="/architectural-analysis"
                  className="dashboard-feature-list__item"
                >
                  <span className="dashboard-feature-list__icon">🏗️</span>

                  <span className="dashboard-feature-list__text">
                    Análise Arquitetural
                  </span>
                </Link>

                <Link
                  to="/business-analysis"
                  className="dashboard-feature-list__item"
                >
                  <span className="dashboard-feature-list__icon">💼</span>

                  <span className="dashboard-feature-list__text">
                    Análise de Negócio
                  </span>
                </Link>
              </div>
            </div>

            <div className="dashboard-logout">
              <button className="dashboard-logout__button" onClick={logout}>
                Sair do Sistema
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
