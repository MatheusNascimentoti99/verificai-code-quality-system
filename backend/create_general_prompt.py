#!/usr/bin/env python3
"""
Script to create the correct general analysis prompt for criteria analysis
"""

import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent / "backend"))

from sqlalchemy.orm import sessionmaker
from app.core.database import engine
from app.models.prompt import PromptConfiguration
from datetime import datetime

def create_general_analysis_prompt():
    """Create the general analysis prompt for criteria evaluation"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if prompt already exists
        existing_prompt = db.query(PromptConfiguration).filter(
            PromptConfiguration.name == "General Analysis with Criteria"
        ).first()

        if existing_prompt:
            print("Prompt already exists, updating...")
            existing_prompt.content = get_prompt_content()
            existing_prompt.updated_at = datetime.utcnow()
            db.commit()
            print("Prompt updated successfully")
        else:
            # Create new prompt
            new_prompt = PromptConfiguration(
                name="General Analysis with Criteria",
                prompt_type="GENERAL",
                user_id=1,  # Assuming admin user with ID 1 exists
                content=get_prompt_content(),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_prompt)
            db.commit()
            print(f"Prompt created successfully with ID: {new_prompt.id}")

        # List all prompts
        print("\nCurrent prompts:")
        prompts = db.query(PromptConfiguration).all()
        for prompt in prompts:
            print(f"ID: {prompt.id}, Name: {prompt.name}, Type: {prompt.prompt_type}")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

def get_prompt_content():
    """Get the correct prompt content for criteria analysis"""
    return """Você é um especialista em análise de código com vasta experiência em revisão de qualidade, boas práticas e padrões de codificação.

Sua tarefa é analisar o código fonte fornecido e avaliá-lo com base nos critérios específicos elencados abaixo.

### CÓDIGO FONTE PARA ANÁLISE:
```typescript
[INSERIR CÓDIGO AQUI]
```

Analise o código acima com base nos seguintes critérios:

#

Para cada critério, forneça:
1. Uma avaliação clara sobre se o código atende ao critério
2. Nível de confiança (0.0-1.0)
3. Evidências específicas do código, incluindo linhas relevantes
4. Recomendações para melhoria, se aplicável

Forneça sua análise em um formato estruturado que inclua:
- Avaliação geral do código
- Avaliações individuais dos critérios
- Exemplos de código que apoiam suas conclusões
- Recomendações acionáveis

Formate sua resposta em markdown com a seguinte estrutura exata:

## Avaliação Geral
[Resumo geral da análise com pontos fortes e fracos do código]

## Critério 1: [Nome do critério]
**Status:** [Conforme/Parcialmente Conforme/Não Conforme]
**Confiança:** [X.X]%

[Avaliação detalhada com evidências específicas do código]
- **Evidências:** [Listar evidências com referência a linhas ou trechos específicos]
- **Justificativa:** [Explicação detalhada da avaliação]

**Recomendações:**
- [Lista de recomendações específicas e acionáveis]

## Critério 2: [Nome do critério]
**Status:** [Conforme/Parcialmente Conforme/Não Conforme]
**Confiança:** [X.X]%

[Avaliação detalhada com evidências específicas do código]
- **Evidências:** [Listar evidências com referência a linhas ou trechos específicos]
- **Justificativa:** [Explicação detalhada da avaliação]

**Recomendações:**
- [Lista de recomendações específicas e acionáveis]

## Recomendações Gerais
[Lista de recomendações gerais para melhoria do código]

IMPORTANTE:
1. Seja específico e forneça exemplos concretos do código analisado
2. Inclua números de linhas ou trechos específicos como evidências
3. Para cada critério, avalie de forma independente e justificada
4. Ao finalizar sua análise, inclua exatamente a tag #FIM# para indicar que a resposta está completa.

#FIM#"""

if __name__ == "__main__":
    create_general_analysis_prompt()