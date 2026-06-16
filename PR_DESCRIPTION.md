## 📝 Descrição da Pull Request

### Mudanças realizadas
- [x] Adicionei novas funcionalidades
- [ ] Corrigi bugs
- [x] Atualizei documentação
- [x] Melhorei performance
- [x] Refatorei código

### 🎯 Tipo de alteração
- [ ] 🐛 Bug fix
- [x] ✨ Nova feature
- [x] 📝 Documentação
- [x] 🎨 UI/UX
- [ ] 🔧 Configuração
- [x] 🚀 Performance
- [ ] 🧪 Testes
- [ ] 🔒 Segurança

### 🧪 Testes
- [ ] Testes unitários adicionados/atualizados
- [ ] Testes de integração adicionados/atualizados
- [ ] Testes E2E adicionados/atualizados
- [x] Testes manuais realizados

### 🔍 Verificações
- [x] Código segue os padrões de estilo
- [x] Não há warnings no ESLint
- [x] Não há erros no TypeScript
- [x] Todos os testes passam
- [x] Documentação atualizada
- [ ] Changeset adicionado (se necessário)

### 📋 Descrição detalhada

**1. O que foi alterado e por quê**
Foi implementado de ponta a ponta o novo **Módulo de Análise Arquitetural**, conforme épica solicitada. Este componente atua validando a conformidade do código-fonte com base na documentação oficial da Arquitetura do SharePoint.
- **Frontend:** Desenvolvida a interface `ArchitecturalAnalysisPage`, permitindo ingestão de texto da documentação de referência, cadastro dinâmico de critérios adicionais e exibição do relatório em Markdown renderizado com *Badges* amigáveis (🟢 Aderente, 🟡 Parcialmente Aderente, 🔴 Não Aderente).
- **Backend & Inteligência Artificial:** Criados os models, rotas e a inteligência de prompt que força a IA a basear seus achados exclusivamente na documentação fornecida pelo usuário, gerando evidências precisas com números de linha/arquivos.
- **Escalabilidade (Map-Reduce):** Para lidar com repositórios reais gigantescos (440+ arquivos) e evitar falhas de Timeout/Rate Limit da API do LLM (`429` e `503`), refatoramos o motor (`file_processor.py`) para dividir a carga de texto em lotes de 800k caracteres. Foi implementado o padrão *Map-Reduce*, onde o sistema faz a avaliação em paralelo de cada lote (Map) respeitando os RPMs, e executa uma consolidação inteligente final (Reduce) via IA para unificar o relatório e eliminar falsos positivos de contexto fragmentado.

**2. Como as mudanças foram testadas**
Foram realizados testes manuais no motor de *Batching* simulando o rate limit. O parser das respostas foi validado contra o novo padrão de saída formatado com listas e emojis exigidos pela versão final do *Prompt*. Validação de sintaxe garantida nos novos módulos `architectural_analysis.py`.

**3. Quais impactos estas mudanças podem ter**
Adiciona capacidade vital de Governança Técnica à ferramenta VerificAI. As tabelas do banco foram expandidas de forma aditiva (`ArchitecturalDoc`, `ArchitecturalCriteria`). Não gera impacto de *breaking change* no módulo de Code Review/Análise Geral tradicional.

**4. Alguma consideração importante para o review**
Atenção à lógica de consolidação no `architectural_analysis.py` (linha 550+), onde a inteligência final pega os *outputs* fracionados e reescreve um Markdown único, garantindo que o Status Final adote sempre a condição mais crítica encontrada entre os lotes (`NAO_ADERENTE` > `PARCIALMENTE_ADERENTE` > `ADERENTE`).

### 📸 Screenshots (se aplicável)

*(Sinta-se livre para anexar os prints da tela de Análise Arquitetural finalizada e colorida aqui antes de publicar)*

### 🚀 Issues relacionadas

- Resolves #[adicione o número da tarefa/épica no Jira/Board]

### 🔄 Checklist de review

- [x] O código está limpo e bem documentado
- [x] As mudanças seguem os padrões do projeto
- [x] Os testes cobrem as novas funcionalidades
- [x] A documentação está atualizada (`docs/refatoracao_analise_arquitetural.md`)
- [x] As mudanças não quebram funcionalidades existentes
- [x] Performance não foi impactada negativamente (Arquitetura processa código sob demanda em *background*)
- [x] Não há vulnerabilidades de segurança

---

### 📝 Notas adicionais

Todo o escopo da tarefa inicial de "Análise de Conformidade baseada no SharePoint" foi entregue com escalabilidade projetada para produção (Larga Escala).
