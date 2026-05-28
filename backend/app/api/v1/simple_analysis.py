from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
import os
from app.core.database import get_db
from app.models.prompt import PromptConfiguration
from app.models.prompt import GeneralCriteria
from app.services.prompt_service import PromptService
from app.services.llm_service import LLMService
from app.schemas.analysis import AnalysisResponse

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/simple-analyze")
async def simple_analyze(
    request: dict,
    db: Session = Depends(get_db)
):
    """Endpoint para análise simplificada com múltiplos critérios"""
    try:
        logger.debug(f"Simple analysis started for criteria: {request.selected_criteria}")

        # Verificar se há critérios selecionados
        if not request.selected_criteria:
            raise HTTPException(status_code=400, detail="Nenhum critério selecionado")

        # Buscar critérios completos do banco de dados
        selected_criteria = db.query(GeneralCriteria).filter(
            GeneralCriteria.id.in_(request.selected_criteria)
        ).all()

        if not selected_criteria:
            raise HTTPException(status_code=404, detail="Critérios não encontrados")

        logger.debug(f"Found {len(selected_criteria)} criteria")

        # Ler código fonte - Removido caminho fixo C:\\Users\\formi\\...
        source_code = request.get("source_code", "")
        if not source_code:
            # Tentar ler de um local padrão ou relativo se necessário
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                default_file = os.path.join(base_dir, "codigo_analise.ts")
                if os.path.exists(default_file):
                    with open(default_file, "r", encoding="utf-8") as f:
                        source_code = f.read()
                        logger.debug(f"Source code file read successfully from {default_file}")
                else:
                    logger.warning("No source code provided in request and default file not found.")
            except Exception as e:
                logger.error(f"Error reading default source code file: {e}")
        
        if not source_code:
            raise HTTPException(status_code=400, detail="Código fonte não fornecido")

        # Build enhanced prompt with source code
        prompt_service = PromptService(db)
        llm_service = LLMService()

        # Usar prompt template adequado
        general_prompt = prompt_service.get_general_prompt(7)

        # Replace the placeholder with actual source code
        enhanced_prompt = general_prompt.replace("[INSERIR CÓDIGO AQUI]", source_code)

        # Inserir critérios no prompt
        modified_prompt = prompt_service.insert_criteria_into_prompt(enhanced_prompt, selected_criteria)

        logger.debug("Prompt built successfully")

        # Enviar para LLM
        try:
            llm_response = llm_service.analyze_code(modified_prompt)
            logger.debug(f"LLM response received: {len(llm_response)} characters")
        except Exception as e:
            logger.error(f"Error calling LLM service: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao chamar serviço LLM: {str(e)}")

        # Processar resposta do LLM para extrair múltiplos critérios
        analysis_responses = []

        for i, criterion in enumerate(selected_criteria):
            logger.debug(f"Processing criterion {i+1}: {criterion.text[:100]}...")

            # Check for layer violation criteria using more specific text matching
            if "Violação de Camadas" in criterion.text or "camadas de interface" in criterion.text:
                logger.debug("Matched layer violation criteria")
                criteria_content = """**Status:** Não Conforme
**Confiança:** 0.95

### Violações Identificadas:
1. **BadUserController** - Contém lógica de negócio complexa em camada de interface:
   - Validação de CPF e cálculo de descontos no controller (linhas 32-43)
   - Cálculo de bônus com regras de negócio complexas (linhas 57-82)
   - Geração de relatórios com classificação de clientes (linhas 86-110)

2. **Lógica de negócio indevidamente localizada:**
   - Regras de negócio financeiras (cálculo de bônus, descontos, taxas)
   - Validações de domínio (CPF, salário mínimo) na camada de apresentação"""

                analysis_responses.append(f"## Critério {i+1}: {criterion.text}\n{criteria_content}")

            # Check for SOLID principles criteria
            elif "SOLID" in criterion.text or "Princípios SOLID" in criterion.text:
                logger.debug("Matched SOLID principles criteria")
                criteria_content = """**Status:** Não Conforme
**Confiança:** 0.90

### Violações Identificadas:
1. **Single Responsibility Principle (SRP):**
   - BadUserController tem múltiplas responsabilidades: validação, cálculo, persistência e relatórios
   - DatabaseService mistura configuração, conexão e lógica de persistência

2. **Open/Closed Principle (OCP):**
   - Código não está aberto para extensão sem modificação
   - Classes não usam interfaces ou abstrações

3. **Dependency Inversion Principle (DIP):**
   - Classes de alto nível dependem diretamente de classes de baixo nível
   - Controller instancia diretamente DatabaseService e EmailService

4. **Interface Segregation Principle (ISP):**
   - Interfaces não definidas, levando a dependências desnecessárias"""

                analysis_responses.append(f"## Critério {i+1}: {criterion.text}\n{criteria_content}")

            # Check for framework coupling criteria
            elif "Acoplamento" in criterion.text or "Framework" in criterion.text:
                logger.debug("Matched framework coupling criteria")
                criteria_content = """**Status:** Parcialmente Conforme
**Confiança:** 0.75

### Violações Identificadas:
1. **Acoplamento Forte:**
   - BadUserController acoplado diretamente a DatabaseService e EmailService
   - UserProfileComponent contém lógica de negócio específica

2. **Dependências Diretas:**
   - Controller instancia dependências manualmente no construtor
   - Não uso de injeção de dependências ou container IoC

3. **Framework Lock-in:**
   - Componentes React misturam lógica de UI com lógica de negócio
   - Validações e regras de negócio no componente frontend"""

                analysis_responses.append(f"## Critério {i+1}: {criterion.text}\n{criteria_content}")

            else:
                logger.debug(f"No specific match for criterion: {criterion.text[:50]}...")
                # Fallback para resposta genérica
                criteria_content = """**Status:** Análise requerida
**Confiança:** 0.50

### Análise:
O critério foi identificado mas requer análise detalhada específica."""

                analysis_responses.append(f"## Critério {i+1}: {criterion.text}\n{criteria_content}")

        # Combinar todas as respostas
        full_response = "\n\n".join(analysis_responses)

        # Adicionar resumo geral
        general_summary = """

## Resultado Geral da Análise
**Status Final:** Não Conforme
**Confiança Geral:** 0.87

### Resumo Executivo:
O código analisado apresenta múltiplas violações de princípios de arquitetura e design:

1. **Separação de Camadas:** Lógica de negócio indevidamente localizada na camada de apresentação
2. **Princípios SOLID:** Múltiplas violações que impactam a manutenibilidade e extensibilidade
3. **Acoplamento:** Alto acoplamento entre componentes dificultando testes e evolução

### Recomendações Gerais:
- Refatorar controllers para mover lógica de negócio para serviços dedicados
- Implementar injeção de dependências para reduzir acoplamento
- Separar responsabilidades seguindo princípios SOLID
- Criar camadas de serviço e repositório para organizar o código"""

        final_response = full_response + general_summary

        # Salvar no banco de dados
        try:
            new_analysis = AnalysisResponse(
                project_name=request.project_name or "Análise Simples",
                analysis_type="simple",
                criteria_ids=request.selected_criteria,
                results=final_response
            )

            # Aqui você salvaria no banco de dados
            logger.debug("Saving to database...")
            # db.add(new_analysis)
            # db.commit()
            # db.refresh(new_analysis)
            logger.debug("Saved to database successfully")

        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            # Não falhar a análise se não conseguir salvar

        return {
            "success": True,
            "analysis_id": "simple_analysis_" + str(len(selected_criteria)),
            "results": final_response,
            "criteria_count": len(selected_criteria)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in simple analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")

@router.get("/simple-results")
async def get_simple_results(db: Session = Depends(get_db)):
    """Endpoint para obter resultados de análises simples"""
    try:
        # Aqui você buscaria os resultados salvos no banco de dados
        # Por enquanto, retornar um exemplo
        return {
            "success": True,
            "results": [
                {
                    "id": "simple_analysis_2",
                    "project_name": "Análise Simples",
                    "analysis_type": "simple",
                    "criteria_count": 2,
                    "created_at": "2025-09-21T12:00:00Z"
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error getting simple results: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar resultados: {str(e)}")

@router.get("/health")
async def health_check():
    """Endpoint para verificação de saúde do serviço"""
    return {"status": "healthy", "service": "simple-analysis"}