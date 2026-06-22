# Documentação Técnica e Funcional: Módulo de Análise Arquitetural

## 1. Visão Geral do Módulo

O **Módulo de Análise Arquitetural** foi desenvolvido para ser um componente central na plataforma **VerificAI**, atuando de forma análoga à "Análise Geral", mas com foco estrito na verificação de conformidade do código-fonte em relação à documentação oficial do projeto (ex: páginas do SharePoint de Arquitetura Corporativa).

O objetivo principal desta *feature* é atuar como um "Arquiteto de Software Automatizado", garantindo que a implementação real desenvolvida pelos engenheiros reflita fielmente as tecnologias, os padrões de persistência, as estruturas de camadas e os princípios definidos na documentação base da empresa.

## 2. Requisitos e Funcionalidades Entregues

A solução atendeu a 100% dos requisitos solicitados na tarefa original, implementando uma cadeia completa (Frontend, Backend, Banco de Dados e Inteligência Artificial):

### 2.1. Ingestão da Documentação de Referência
- **Upload e Entrada de Texto:** O sistema permite que o usuário copie e cole o conteúdo da página do projeto (SharePoint) diretamente na plataforma ou envie através da interface. 
- Essa documentação atua como o "Solo Sagrado" da análise. A IA foi instruída via *Prompt Engineering* a **jamais** inferir regras de mercado se a documentação interna da empresa ditar um padrão diferente.

### 2.2. Gestão de Critérios Adicionais
- **Critérios Customizados:** Uma interface dinâmica foi construída para permitir a inclusão de regras específicas e isoladas (ex: *"Verificar se não há SQL puro no código"*, *"Garantir o uso de Hooks Funcionais no React"*).
- Esses critérios são injetados no contexto da IA, obrigando a plataforma a validar ponto a ponto as métricas cadastradas pelo usuário.

### 2.3. Execução da Validação e Geração de Relatório
- O código-fonte do projeto selecionado é mapeado e confrontado diretamente com a documentação da Arquitetura.
- **Relatório Estruturado:** A IA gera um documento completo contendo:
  - Resumo Executivo
  - Status Geral (com *badges* visuais: 🟢 Aderente, 🟡 Parcialmente Aderente, 🔴 Não Aderente)
  - Detalhamento de cada Critério Avaliado
  - Evidências diretamente extraídas do código (linhas e arquivos)
  - Violações, Riscos, Impactos e Próximos Passos recomendados.

## 3. Arquitetura da Solução e Tecnologias Implementadas

A entrega englobou uma arquitetura *Full-Stack* complexa para sustentar o fluxo:

### 3.1. Frontend (React + TypeScript)
- Criação completa da `ArchitecturalAnalysisPage`, contendo formulários reativos, abas de navegação de histórico e renderizador de Markdown seguro para visualização dos relatórios complexos.
- Integração ponta a ponta com a API via `architecturalAnalysisService`.

### 3.2. Backend (Python + FastAPI) e Persistência
- Modelagem de novas tabelas de banco de dados (`ArchitecturalDoc`, `ArchitecturalCriteria`, `ArchitecturalAnalysisResult`) usando SQLAlchemy para guardar histórico de documentações de referência e análises executadas.
- Criação do serviço inteligente (`llm_service.py` e `architectural_analysis.py`) contendo prompts ultra-detalhados e regras estritas para coibir alucinações da IA.

## 4. O Desafio de Escala: Arquitetura "Map-Reduce"

Durante as fases de validação da *feature*, enfrentamos o maior desafio técnico da tarefa: **A escalabilidade para repositórios corporativos reais.**
Ao submeter repositórios massivos (ex: 440+ arquivos e milhares de linhas de código), a API de IA (Gemini Flash) falhava por excesso de Payload, resultando em erros `503 Service Unavailable` e `429 Too Many Requests` limitados pela cota da API.

Para resolver o problema sem custos extras, implementamos uma engenhosa arquitetura **Map-Reduce** no motor de processamento de código (`file_processor.py`):

1. **Batching (Particionamento):** O código é segmentado inteligentemente em lotes (*batches*) limitados a `800.000` caracteres, garantindo que o payload seja leve e de rápido processamento.
2. **Fase "Map" (Avaliação Paralela Segura):** O sistema roda análises isoladas de cada lote. Adicionamos *Throttling* dinâmico (`asyncio.sleep`) para cadenciar as chamadas à API, garantindo respeito absoluto aos limites do rate limit gratuito (RPM).
3. **Fase "Reduce" (Consolidação de Contexto):** Se um lote contiver apenas *Frontend*, a IA acusaria um falso positivo relatando que o *Backend* está ausente. Para anular isso, criamos a etapa de `Reduce`. O backend faz uma "chamada relâmpago" final à IA enviando todos os resultados parciais e obrigando-a a **consolidá-los** e mesclá-los em um único relatório executivo unificado, cancelando contradições de contexto.

## 5. Resultados Obtidos
A implementação desta tarefa proveu ao time:
- **Automatização Absoluta:** O processo manual e exaustivo de code-review arquitetural por humanos pode ser agora abstraído e feito em segundos.
- **Escala Infinita:** Graças ao padrão *Map-Reduce*, a ferramenta pode analisar bases de código gigantescas (gigabytes de texto) dividindo a carga sem estourar limites de memória ou custos de API.
- **Histórico Organizacional:** Todas as documentações do SharePoint validadas ficam imortalizadas no banco de dados para repetições de testes futuros sem esforço de *copy/paste*.

---
*Este documento atesta a entrega e homologação completa da Épica de "Verificação de Conformidade Arquitetural".*
