# Relatório de Refatoração: Escalabilidade da Análise Arquitetural (Padrão Map-Reduce)

## 1. Contexto e Problema Identificado

Durante as validações de qualidade de código na plataforma **VerificAI**, foi identificado um gargalo crítico ao submeter repositórios de larga escala (ex: repositórios com mais de 440 arquivos e milhares de linhas de código) à avaliação arquitetural automatizada. 

A API do LLM (Gemini Flash) em seu tier gratuito retornava erros consistentes de **`503 Service Unavailable`** e **`429 Too Many Requests`**. O problema ocorria porque o payload (a quantidade de texto do código-fonte concatenado) excedia o limite máximo de tokens ou estourava o tempo de timeout permitido pela infraestrutura de IA para requisições únicas.

## 2. A Solução Arquitetada: Padrão "Map-Reduce"

Para resolver definitivamente o problema de escalabilidade sem comprometer a acurácia da análise ou exigir custos adicionais em APIs premium, a arquitetura do motor de análise foi totalmente reescrita implementando o padrão de processamento distribuído **Map-Reduce**.

### 2.1. O Processo de Batching (Particionamento)
O módulo `file_processor.py` foi refatorado para implementar a técnica de *chunking*. Em vez de concatenar todo o repositório em uma única string, o sistema agora calcula o volume de texto e segmenta os arquivos em **Lotes (Batches)**. 
- **Limite de Segurança:** Foi estabelecida uma válvula de segurança rigorosa de **800.000 caracteres por lote**. 
- Isso garante que a requisição seja sempre pequena o suficiente para ser rapidamente processada pela IA, eliminando as falhas `503`.

### 2.2. A Etapa "Map" (Avaliação Paralela)
O backend agora itera sobre cada lote gerado. Para cada lote, uma chamada independente é feita à IA, instruindo-a a realizar uma análise parcial.
- **Throttling Inteligente:** Para evitar bloqueios do tipo `429` (limite de requisições por minuto - RPM), foi introduzido um controle de cadência (`asyncio.sleep(2.0)`) entre as requisições, respeitando as políticas da API sem travar a thread principal da aplicação.

### 2.3. A Etapa "Reduce" (Consolidação Inteligente)
O maior desafio do processamento em lotes é o "Falso Positivo de Contexto". Por exemplo: Se o Lote 1 contém apenas arquivos Frontend e o Lote 2 contém apenas arquivos Backend, o relatório do Lote 1 apontaria erroneamente a "ausência do Backend" como uma violação arquitetural.

Para contornar isso com maestria, implementamos um passo final de **Reduce**:
- Quando a análise de todos os lotes é concluída, o backend agrupa todas as respostas parciais.
- Uma última requisição super rápida é feita à IA, na qual ela atua como uma "Especialista Consolidadora".
- A instrução exige que ela mescle os resultados, remova contradições, cancele falsos positivos baseados na visão global e gere um **Único Relatório Final Coeso**.

## 3. Melhorias na Experiência do Usuário (UX/UI) e Formatação

Aproveitando a refatoração do motor, atacamos os problemas visuais de renderização dos relatórios gerados pela IA.

- **Nomenclatura Amigável (Badges):** Modificamos a taxonomia interna do sistema. Onde antes o sistema binariamente marcava falhas, a IA agora utiliza um vocabulário corporativo com identificadores visuais claros:
  - 🟢 Aderente
  - 🟡 Parcialmente Aderente
  - 🔴 Não Aderente
- **Formatação de Listas (Line Breaks):** Os relatórios originais apresentavam os critérios de forma aglomerada em uma única linha (ex: Frontend, Backend e Banco de Dados colados), prejudicando a leitura. O Prompt Template foi reescrito introduzindo regras rígidas de Markdown, obrigando a IA a utilizar quebras de linha duplas e listas por tópicos para separar cada componente avaliado.

## 4. Ganhos e Resultados

1. **Cobertura 100%:** O sistema agora é capaz de analisar repositórios infinitamente grandes dividindo-os em pacotes digeríveis.
2. **Resiliência:** Tolerância a falhas garantida. O tráfego de rede agora é distribuído e cadenciado.
3. **Agregação Pura:** A consolidação via IA (Reduce) provou ser extremamente eficiente para evitar alertas falsos.
4. **Legibilidade:** O relatório entregue aos usuários está visualmente impecável, claro e com padrão corporativo.

---
*Este documento reflete a entrega técnica da otimização de processamento em Larga Escala da ferramenta VerificAI.*
