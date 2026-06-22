#!/usr/bin/env python3
"""
Script para popular critérios padrão para análise de código
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine
from app.models.user import User
from app.models.prompt import GeneralCriteria
from sqlalchemy.orm import Session

# Critérios padrão para análise de código
DEFAULT_CRITERIA = [
    "Princípios SOLID: Analisar a aplicação de princípios de design consolidados, como a Responsabilidade Única - SRP (evitando componentes que acumulam funções díspares) como controllers com múltiplos endpoints e a Inversão de Dependência (favorecendo o uso de mecanismos de injeção de dependência em vez da instanciação manual de componentes) como a instanciação manual de dependências em vez de usar a injeção padrão do NestJS",
    "Acoplamento a Frameworks: Detectar o uso de funcionalidades que acoplam o código a implementações específicas do framework (ex: uso de @Res() do Express no NestJS), o que dificulta a manutenção e a aplicação de interceptors e pipes globais.",
    "Violação de Camadas: Identificar se a lógica de negócio está incorretamente localizada em camadas de interface (como controladores de API), em vez de residir em camadas de serviço ou domínio dedicadas.",
    "Pressão sobre a Memória: Analisar rotinas e laços que criam um volume excessivo de objetos de curta duração, pressionando o coletor de lixo (Garbage Collector) e causando pausas desnecessárias na aplicação. Avaliar se objetos poderiam ser reutilizados para otimizar o uso da memória.",
    "Ciclo de Vida de Recursos Externos: Verificar se recursos externos, como arquivos temporários ou conexões de rede, são liberados de forma determinística em todos os fluxos de execução (sucesso, erro e finalização), evitando vazamentos de recursos.",
    "Operações de I/O Bloqueantes ou Inseguras: Inspecionar chamadas de rede e outras operações de entrada/saída para garantir a configuração de tempos limite (timeouts) e limites de tamanho de payload, prevenindo que a aplicação fique bloqueada ou vulnerável a sobrecargas.",
    "Manuseio de Dados em Larga Escala: Detectar o carregamento de grandes volumes de dados (como arquivos ou resultados de consultas) diretamente para a memória. Recomendar a utilização de padrões como streaming para processamento de dados em partes (chunks).",
    "Condições de Corrida em Persistência: Identificar padrões de \"leitura-seguida-de-escrita\" em operações de banco de dados que podem introduzir inconsistências de dados devido à concorrência, sugerindo o uso de transações ou operações atômicas.",
    "Validação de Entradas: Verificar se os pontos de entrada da aplicação que recebem dados, especialmente arquivos, possuem validações, filtros de tipo e limites de tamanho para mitigar riscos de segurança. Analisar se objetos de transferência de dados (DTOs) são utilizados com bibliotecas de validação para garantir a integridade e o formato dos dados.",
    "Acesso a Recursos do Sistema: Inspecionar o código que interage com o sistema de arquivos para identificar o uso de entradas do usuário na construção de caminhos, o que pode levar a vulnerabilidades de acesso indevido a arquivos (Path Traversal).",
    "Tratamento de Erros: Sinalizar blocos de captura de exceção vazios ou que apenas registram o erro sem um tratamento adequado, pois eles podem ocultar falhas críticas de segurança ou de lógica de negócio.",
    "Consistência de Contratos de API: Analisar as saídas da aplicação para detectar rotas que retornam tipos de dados inconsistentes dependendo do fluxo de execução, o que viola o contrato da API e pode causar falhas em sistemas clientes.",
    "Potenciais Vulnerabilidades de Segurança: Identificar implementações, fluxos ou configurações que possam introduzir brechas de segurança, permitindo acesso não autorizado, exposição de informações, manipulação indevida de dados, execução de operações não previstas ou comprometimento da integridade, confidencialidade e disponibilidade da aplicação. Avaliar se os controles de segurança são adequados aos riscos envolvidos e aplicados de forma consistente."
]

def seed_criteria():
    """Popula critérios padrão para todos os usuários"""
    db = SessionLocal()

    try:
        # Buscar todos os usuários
        users = db.query(User).all()

        if not users:
            print("Nenhum usuário encontrado no banco de dados")
            return

        print(f"Encontrados {len(users)} usuários")

        total_criteria_added = 0

        for user in users:
            # Verificar se usuário já tem critérios
            existing_criteria = db.query(GeneralCriteria).filter(
                GeneralCriteria.user_id == user.id
            ).count()

            if existing_criteria > 0:
                print(f"Usuario {user.username} já tem {existing_criteria} critérios, pulando...")
                continue

            print(f"Adicionando critérios para usuário: {user.username}")

            # Adicionar critérios padrão
            for i, criteria_text in enumerate(DEFAULT_CRITERIA):
                criteria = GeneralCriteria(
                    user_id=user.id,
                    text=criteria_text,
                    is_active=True,
                    order=i
                )
                db.add(criteria)
                total_criteria_added += 1

            db.commit()
            print(f"{len(DEFAULT_CRITERIA)} critérios adicionados para {user.username}")

        print(f"\nTotal de {total_criteria_added} critérios adicionados com sucesso!")

    except Exception as e:
        print(f"Erro ao popular critérios: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Iniciando seed de critérios padrão...")
    seed_criteria()
    print("Seed de critérios concluído!")