"""
Prompt service for VerificAI Backend - Handles prompt manipulation and criteria insertion
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.prompt import PromptConfiguration
from app.models.prompt import GeneralCriteria

class PromptService:
    """Service for handling prompt operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_general_prompt(self, prompt_id: int = None) -> str:
        """Get the general prompt configuration from database"""
        try:
            if prompt_id:
                # Get specific prompt by ID
                prompt_config = self.db.query(PromptConfiguration).filter(
                    PromptConfiguration.id == prompt_id,
                    PromptConfiguration.is_active == True
                ).first()
            else:
                # Get the most recent general prompt configuration
                prompt_config = self.db.query(PromptConfiguration).filter(
                    PromptConfiguration.prompt_type == "general",
                    PromptConfiguration.is_active == True
                ).order_by(PromptConfiguration.updated_at.desc()).first()

            if prompt_config:
                return prompt_config.content
            else:
                # Return default prompt if no configuration found
                return self._get_default_general_prompt()

        except Exception as e:
            print(f"Error getting general prompt: {e}")
            return self._get_default_general_prompt()

    def get_selected_criteria(self, criteria_ids: List[str]) -> List[GeneralCriteria]:
        """Get selected criteria from database"""
        try:
            # Extract actual IDs from criteria_ids (format: "criteria_123")
            actual_ids = []
            for criteria_id in criteria_ids:
                if criteria_id.startswith("criteria_"):
                    actual_ids.append(int(criteria_id.replace("criteria_", "")))
                else:
                    try:
                        actual_ids.append(int(criteria_id))
                    except ValueError:
                        continue

            # Get criteria from database
            criteria = self.db.query(GeneralCriteria).filter(
                GeneralCriteria.id.in_(actual_ids),
                GeneralCriteria.is_active == True
            ).order_by(GeneralCriteria.order).all()

            return criteria

        except Exception as e:
            print(f"Error getting selected criteria: {e}")
            return []

    def insert_criteria_into_prompt(self, prompt: str, criteria: List[GeneralCriteria]) -> str:
        """Insert criteria into prompt at the # delimiter and update the structure example"""
        try:
            # Format criteria for insertion with clear headers
            criteria_text = ""
            for i, criterion in enumerate(criteria, 1):
                criteria_text += f"## Critério {i}: {criterion.text}\n\n"
                criteria_text += f"Avalie este critério especificamente usando o nome exato: \"{criterion.text}\"\n\n"
                criteria_text += "---\n\n"

            # Look for [INSERIR_CRITÉRIOS_AQUI] delimiter in prompt
            if "[INSERIR_CRITÉRIOS_AQUI]" in prompt:
                # Replace the placeholder with formatted criteria
                modified_prompt = prompt.replace("[INSERIR_CRITÉRIOS_AQUI]", criteria_text.strip())
            else:
                # If no placeholder found, append criteria to the end
                modified_prompt = prompt + f"\n\nCritérios a serem avaliados:\n{criteria_text}"

            # Now update the structure example to match the actual number of criteria
            if len(criteria) == 1:
                # For single criteria, remove the duplicate "Critério 2" example
                modified_prompt = self._adjust_prompt_for_single_criteria(modified_prompt, criteria[0].text)
            elif len(criteria) > 1:
                # For multiple criteria, ensure the example shows the correct count
                modified_prompt = self._adjust_prompt_for_multiple_criteria(modified_prompt, len(criteria))

            return modified_prompt

        except Exception as e:
            print(f"Error inserting criteria into prompt: {e}")
            return prompt  # Return original prompt if error occurs

    def _adjust_prompt_for_single_criteria(self, prompt: str, criteria_text: str) -> str:
        """Adjust prompt structure to show only one criteria example with the actual criteria name"""
        import re

        print(f"=== ADJUSTING PROMPT FOR SINGLE CRITERIA ===")
        print(f"Original prompt contains 'Critério 2': {'Critério 2' in prompt}")
        print(f"Number of '## Critério' in original: {prompt.count('## Critério')}")
        print(f"Criteria text: {criteria_text}")

        # Remove completely the multi-criteria example structure and replace with single-criteria structure
        # Find the format section and replace it entirely
        format_section_pattern = r'Formate sua resposta em markdown com a seguinte estrutura exata:.*?(?=#FIM#|$)'

        single_criteria_format = f"""Formate sua resposta em markdown com a seguinte estrutura exata:

## Avaliação Geral
[Resumo geral da análise]

## Critério: {criteria_text}
**Status:** [Conforme/Parcialmente Conforme/Não Conforme]
**Confiança:** [X.X]%

[Avaliação detalhada com evidências do código]

**Recomendações:**
- [Lista de recomendações específicas]

**IMPORTANTE: Ao finalizar a análise deste critério, inclua EXATAMENTE a tag: #FIM_ANALISE_CRITERIO#**
Esta tag marca o fim completo da análise do critério acima.

#FIM_ANALISE_CRITERIO#

## Recomendações Gerais
[Lista de recomendações gerais]

#FIM#"""

        modified_prompt = re.sub(format_section_pattern, single_criteria_format, prompt, flags=re.DOTALL)

        print(f"After replacing format section:")
        print(f"Contains 'Critério 2': {'Critério 2' in modified_prompt}")
        print(f"Number of '## Critério' in modified: {modified_prompt.count('## Critério')}")
        print(f"Number of '## Critério:' (with colon): {modified_prompt.count('## Critério:')}")

        # Also clean up any remaining multiple criteria references that might exist
        modified_prompt = re.sub(r'## Critério \d+:', '## Critério:', modified_prompt)

        # Add explicit instruction for single criteria analysis with the exact criteria name
        instruction_text = f"""
CRÍTICO: Esta análise deve conter APENAS UM critério de avaliação.
- NÃO crie múltiplos critérios
- NÃO invente critérios adicionais
- Use OBRIGATORIAMENTE o cabeçalho exato: "## Critério 1: {criteria_text}"
- A numeração é OBRIGATÓRIA para o processamento correto da análise
- NÃO modifique o nome do critério: use exatamente "{criteria_text}"
- Avalie exclusivamente o critério fornecido acima
- O título do critério na resposta DEVE ser idêntico ao fornecido

"""

        # Insert the instruction before the code analysis section
        code_analysis_marker = "## CÓDIGO FONTE PARA ANÁLISE:"
        if code_analysis_marker in modified_prompt:
            modified_prompt = modified_prompt.replace(
                code_analysis_marker,
                instruction_text + code_analysis_marker
            )

        print(f"=== FINAL PROMPT STATS ===")
        print(f"Final prompt length: {len(modified_prompt)}")
        print(f"Final '## Critério' count: {modified_prompt.count('## Critério')}")
        print(f"Final '## Critério:' count: {modified_prompt.count('## Critério:')}")
        print(f"=== END ADJUSTMENT ===")

        return modified_prompt

    def _adjust_prompt_for_multiple_criteria(self, prompt: str, count: int) -> str:
        """Adjust prompt structure to show the correct number of criteria examples"""
        import re

        if count >= 2:
            # First, insert the instruction before the code analysis section
            instruction_text = f"""
CRÍTICO: Esta análise deve conter exatamente {count} critérios de avaliação.
- Use exatamente os nomes dos critérios fornecidos acima
- NÃO modifique os nomes dos critérios
- NÃO invente critérios adicionais
- CADA critério DEVE usar o cabeçalho com numeração: "## Critério 1: [Nome exato do critério]", "## Critério 2: [Nome exato do critério]", etc.
- A numeração é OBRIGATÓRIA para o processamento correto da análise

"""

            code_analysis_marker = "## CÓDIGO FONTE PARA ANÁLISE:"
            if code_analysis_marker in prompt:
                prompt = prompt.replace(
                    code_analysis_marker,
                    instruction_text + code_analysis_marker
                )

            # Then, generate the correct number of criteria examples in the template
            criteria_examples = ""
            for i in range(1, count + 1):
                criteria_examples += f"""
## Critério {i}: [Nome do critério]
**Status:** [Conforme/Parcialmente Conforme/Não Conforme]
**Confiança:** [X.X]%

[Avaliação detalhada com evidências do código]

**Recomendações:**
- [Lista de recomendações específicas]

**IMPORTANTE: Ao finalizar a análise deste critério, inclua EXATAMENTE a tag: #FIM_ANALISE_CRITERIO#**
Esta tag marca o fim completo da análise do critério acima.

#FIM_ANALISE_CRITERIO#

"""

            # Replace the entire format section with the correct number of examples
            format_section_pattern = r'Formate sua resposta em markdown com a seguinte estrutura exata:.*?(?=## Recomendações Gerais|#FIM#|$)'

            new_format_section = f"""Formate sua resposta em markdown com a seguinte estrutura exata:

## Avaliação Geral
[Resumo geral da análise]

{criteria_examples}## Recomendações Gerais
[Lista de recomendações gerais]"""

            modified_prompt = re.sub(format_section_pattern, new_format_section, prompt, flags=re.DOTALL)

            return modified_prompt
        else:
            # This shouldn't happen as this method is only called for count > 1
            return prompt

    def _get_default_general_prompt(self) -> str:
        """Get default general prompt"""
        return """
Você é um especialista em análise de código.

**INSTRUÇÃO CRÍTICA - OBRIGATÓRIO:**
Para cada critério de avaliação, você DEVE incluir EXATAMENTE a tag #FIM_ANALISE_CRITERIO# ao final da análise completa do critério.
Esta tag é ESSENCIAL para garantir que a análise completa seja capturada pelo sistema.
NÃO trunc suas respostas - forneça análises detalhadas e completas.

### CRITÉRIOS PARA ANÁLISE:
[INSERIR_CRITÉRIOS_AQUI]

### CÓDIGO FONTE PARA ANÁLISE:
```typescript
[INSERIR CÓDIGO AQUI]
```

**IMPORTANTE:** O código acima pode conter múltiplos arquivos. Cada arquivo está claramente identificado com cabeçalhos no formato:
```
============================================================
ARQUIVO: [nome_do_arquivo]
TAMANHO: [X] caracteres
TIPO: [EXTENSÃO]
============================================================
```

Analise TODOS os arquivos de código acima como um conjunto integrado, considerando as interações entre eles, com base nos seguintes critérios:

#

Para cada critério, forneça:
1. Uma avaliação clara sobre se o código atende ao critério
2. Nível de confiança (0.0-1.0)
3. Evidências específicas do código
4. Recomendações para melhoria, se aplicável

Forneça sua análise em um formato estruturado que inclua:
- Avaliação geral
- Avaliações individuais dos critérios
- Exemplos de código que apoiam suas conclusões
- Recomendações acionáveis

Formate sua resposta em markdown com a seguinte estrutura exata:

## Avaliação Geral
[Resumo geral da análise]

## Critério 1: [Nome do critério]
**Status:** [Conforme/Parcialmente Conforme/Não Conforme]
**Confiança:** [X.X]%

[Avaliação detalhada com evidências do código]

**Recomendações:**
- [Lista de recomendações específicas]

## Critério 2: [Nome do critério]
**Status:** [Conforme/Parcialmente Conforme/Não Conforme]
**Confiança:** [X.X]%

[Avaliação detalhada com evidências do código]

**Recomendações:**
- [Lista de recomendações específicas]

**IMPORTANTE: Ao finalizar a análise deste critério, inclua EXATAMENTE a tag: #FIM_ANALISE_CRITERIO#**
Esta tag marca o fim completo da análise do critério acima.

#FIM_ANALISE_CRITERIO#

## Recomendações Gerais
[Lista de recomendações gerais]

IMPORTANTE: Ao finalizar sua análise, inclua exatamente a tag #FIM# para indicar que a resposta está completa.

#FIM#
"""

# Global instance function
def get_prompt_service(db: Session) -> PromptService:
    """Get prompt service instance"""
    return PromptService(db)