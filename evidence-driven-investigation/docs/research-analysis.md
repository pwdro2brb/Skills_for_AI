# Análise das fontes pesquisadas

Pesquisa feita em 2026-11-24, antes de implementar a Skill. Para cada fonte há
as mesmas sete perguntas pedidas no plano do projeto. "Adotado", "adaptado" e
"rejeitado" se referem a esta Skill, não a uma avaliação geral da fonte.

Fontes lidas diretamente (código ou documento completo) estão marcadas com
**[lido]**. Fontes conhecidas apenas por resumo, página de registro ou abstract
estão marcadas com **[resumo]**, e as conclusões sobre elas são mais fracas.

---

## 1. REA — Reverse Engineer Anything **[lido]**

Repositório `github.com/morluto/rea`, commit `ef4945cd` (2026-11-25), licença MIT.
Arquivos lidos: `.agents/skills/reverse-engineer-anything/SKILL.md`,
`references/evidence-workflows.md`, `docs/reference/reconstruction-obligation-ledgers.md`,
trechos de `docs/reference/mcp-contracts.md`, `docs/getting-started/mcp-prompts.md`,
`docs/development/tool-design.md`, `docs/development/reconstruction-readiness.md`,
`src/domain/evidence.ts`, `src/domain/residualUnknown.ts`,
`src/domain/evidenceCompletionLedger.ts`, `AGENTS.md`.

### 1.1 Evidence ledger

- **Conceito útil:** toda ferramenta devolve um registro de Evidence com
  identidade estável; conclusões citam IDs em vez de repetir dados.
- **Como funciona:** o registro tem `confidence` (`observed | derived | inferred`),
  `authority` (`shipped-artifact | controlled-replay | historical-reference |
  external-service | analyst-inference`), `limitations`, `locations`,
  `evidence_links`, `environment` e `relationship_coverage`. O ID é um digest
  SHA-256 do conteúdo canônico, então qualquer alteração muda o ID
  (`computeEvidenceId`). Um bundle autenticado é validado inteiro.
- **Generalizável:** separação entre *o que foi observado* e *com que
  autoridade*; limitações obrigatórias dentro do próprio registro; links de
  derivação; detecção de adulteração por digest.
- **Específico do domínio:** subjects de binário (endereços, offsets), perfis de
  análise de Ghidra/IDA, cobertura de relações de grafo.
- **Limitações:** a autoridade é um enum fechado pensado para engenharia
  reversa; não cobre "prova formal", "teste estatístico" ou "fonte primária".
- **Decisão de adoção:** **adaptado.** Mantive `epistemic_status` separado de
  `authority`, limitações por evidência e `derived_from`. Troquei o ID por digest
  pelo ID sequencial `E-0001` pedido no plano (legível por humanos), e adicionei
  um `record_digest` separado para detectar edição fora dos scripts. O
  vocabulário de autoridade virou um arquivo de dados extensível
  (`references/authority-matrix.json`).

### 1.2 Residual unknowns

- **Conceito útil:** o que não se sabe é um objeto de primeira classe, com
  pergunta delimitada, severidade, autoridade exigida e sondagens recomendadas.
- **Como funciona:** `residualUnknown.ts` define status `open | investigating |
  blocked | contradicted | resolved`; `resolved` exige uma `resolution` com
  disposição `verified` (com pelo menos uma evidência), `withdrawn` ou
  `out-of-scope`. `contradicted` exige evidência contraditória. A mesma
  evidência não pode apoiar e contradizer. Cada revisão tem digest encadeado
  (`previous_revision_digest`). `evidenceBundle.ts` recusa uma resolução cuja
  evidência não tenha a `required_authority`.
- **Generalizável:** praticamente tudo. É o mecanismo que impede "não achei,
  então não existe".
- **Específico do domínio:** `comparison_conclusion_scope` (dimensões de
  comparação de funções).
- **Limitações:** o histórico encadeado por digest é pesado para um agente
  editar; faz sentido num servidor, menos num arquivo JSON.
- **Decisão de adoção:** **adotado quase integralmente.** Mesmos status (mais
  `OUT_OF_SCOPE` explícito, pedido no plano), mesma regra de resolução por
  autoridade, mesma proibição de apoiar e contradizer ao mesmo tempo. Acrescentei
  `requires_observation` (inferência e derivação não fecham). Troquei o
  encadeamento por digest por um `history` simples por registro.

### 1.3 Reconstruction obligation ledgers

- **Conceito útil:** requisitos viram obrigações verificáveis, e uma obrigação só
  fecha com dono único, todos os casos exigidos e um verificador com autoridade
  comparável à da observação original.
- **Como funciona:** cada obrigação tem `required_case_kinds` (positive,
  negative, malformed, cancellation, teardown), autoridade exigida para original,
  fixture e verificador, dependências, unknowns residuais e `disposition`. O
  documento separa três verificações: **autenticidade** (a evidência não foi
  adulterada), **autoridade** (é do tipo certo) e **aplicabilidade** (descreve a
  versão atual do código e da obrigação). Prova antiga fica válida como
  proveniência, mas não fecha a obrigação depois de uma mudança. "Um teste
  unitário verde não fecha uma obrigação `packaged-process`." "Marcar como
  `blocked` ou `out-of-scope` registra a disposição, mas não conta como
  verificado."
- **Generalizável:** casos exigidos por obrigação; autoridade comparável; a
  tríade autenticidade/autoridade/aplicabilidade; bloqueio por unknowns e
  contradições; uma falha não pode ser escondida por um resultado duplicado que
  passou.
- **Específico do domínio:** camadas (`cli`, `protocol`, `electron`,
  `native-abi`), `owner_sha256` de implementação, captura de processo.
- **Limitações:** o próprio REA admite que o avaliador "não observa
  independentemente os eventos descritos" pelas observações fornecidas. O
  ledger garante coerência, não verdade. Isso vale igualmente para esta Skill.
- **Decisão de adoção:** **adaptado.** Obrigações com `required_cases` e
  `case_evidence`, `required_authority`, bloqueadores e dependências. A
  aplicabilidade virou o campo opcional `applies_to` (identidade do artefato
  verificado), comparado com a identidade das evidências. A limitação foi
  copiada explicitamente para o README ("What this project does not claim").

### 1.4 Authority matching

- **Conceito útil:** cada tipo de afirmação tem um tipo mínimo de evidência.
- **Como funciona:** no REA é implícito em várias regras: estático não fecha
  runtime; `controlled-replay` exige captura real; teste unitário não fecha
  `packaged-process`; correlação estático/runtime "são hipóteses, não
  causalidade".
- **Generalizável:** a ideia é independente de domínio. O que muda é a tabela.
- **Específico do domínio:** a tabela concreta.
- **Limitações:** no REA a tabela está espalhada pelo código; não existe um
  artefato único que um agente de outro domínio possa ler.
- **Decisão de adoção:** **generalizado.** Criei uma matriz explícita em JSON
  (tipo de afirmação → autoridades aceitas, quantidade mínima), legível pelo
  agente e aplicada pelos scripts, que adaptadores de domínio podem estender.

### 1.5 Ferramentas primitivas versus workflows

- **Conceito útil:** `tool-design.md` — "prefira primitivas; componha workflows".
  Uma primitiva reporta um fato reutilizável; workflows só existem quando o uso
  repetido mostra a necessidade. "Um plano sem execução não estabelece
  comportamento de runtime." "Uma sequência de ferramentas roteirizada não
  estabelece seleção pelo agente; isso exige uma avaliação real com agente."
- **Generalizável:** scripts pequenos, cada um com uma responsabilidade, em vez
  de um orquestrador que tenta conduzir a investigação.
- **Decisão de adoção:** **adotado.** Cada script faz uma coisa (registrar,
  validar, avaliar, gerar relatório). Nenhum script conduz a investigação ou
  decide hipóteses; isso fica com o agente.

### 1.6 Prompts e contratos MCP

- **Conceito útil:** seis workflows guiados (`investigate_feature`,
  `verify_reconstruction`, `audit_residual_unknowns`,
  `prepare_bounded_process_capture`...) que **não invocam ferramentas**; só
  sugerem pontos de partida e pedem para separar observação, inferência e
  desconhecido. Conteúdo vindo do alvo é marcado `untrusted_content` e tratado
  como dado, nunca como instrução.
- **Generalizável:** orientar sem prescrever chamadas; marcar conteúdo não
  confiável; "não repetir uma chamada idêntica sem mudar a entrada ou resolver o
  bloqueio".
- **Específico do domínio:** catálogo de ferramentas, paginação de evidências.
- **Decisão de adoção:** **adaptado** em `references/safety-boundaries.md`
  (conteúdo observado é dado) e em `investigation-workflow.md` (não repetir
  sondagem idêntica; checklist final de perguntas abertas).

### 1.7 Disciplina geral do SKILL.md do REA

- Trechos úteis: "Toda conclusão precisa distinguir observações, inferências e
  desconhecidos"; "nunca implicar que análise estática observou execução"; "uma
  ausência observada numa tabela não prova que o comportamento nunca existiu";
  "antes de terminar, revisite o checklist original e marque cada pergunta como
  respondida, parcialmente respondida ou não resolvida".
- **Decisão:** **adotado** como regras centrais do `SKILL.md`, reescritas para
  serem independentes de domínio.

---

## 2. POPPER — Automated Hypothesis Validation with Agentic Sequential Falsifications **[resumo]**

Huang, Jin, Li, Li, Candès, Leskovec. ICML 2025 (PMLR 267). arXiv 2502.09858.
Código: `github.com/snap-stanford/POPPER`.

- **Fonte:** abstract, página do ICML e trechos do PDF.
- **Conceito útil:** validar uma hipótese abstrata testando suas
  **implicações mensuráveis** com experimentos de falsificação desenhados por
  agentes, e agregar os resultados com controle estrito de erro tipo I.
- **Como funciona:** dois agentes (um desenha experimentos de falsificação,
  outro executa); cada teste vira um p-valor convertido em e-valor; os e-valores
  são combinados sequencialmente e o processo decide rejeitar, continuar ou parar.
- **Generalizável:** hipótese → implicações observáveis → testes desenhados para
  derrubar, não para confirmar; parar quando a evidência acumulada basta;
  separar quem desenha de quem executa.
- **Específico do domínio:** a agregação por e-valores exige testes estatísticos
  válidos sobre dados; não se aplica a depuração ou engenharia reversa.
- **Limitações:** um artigo posterior (arXiv 2604.22080, "Sound Agentic Science
  Requires Adversarial Experiments") observa que a instância atual do POPPER
  opera apenas sobre bases estáticas e que nenhuma implantação com experimentos
  físicos existe ainda.
- **Decisão de adoção:** **adaptado sem a estatística.** Previsões por hipótese,
  sondagens com resultado esperado por hipótese e prioridade para sondagens que
  discriminam. A agregação por e-valores fica como orientação no adaptador de
  análise de dados, não como mecanismo geral. A confiança continua sendo rótulo
  (`low | moderate | high`) com justificativa, não probabilidade, como o plano
  exige.

## 3. "Sound Agentic Science Requires Adversarial Experiments" **[resumo]**

arXiv 2604.22080.

- **Conceito útil:** padrão "falsification-first": todo resultado produzido com
  ajuda de agentes deve vir acompanhado de evidência de que passou por um teste
  adversarial.
- **Generalizável:** sim, é exatamente a regra "procure ativamente
  contradições e contraexemplos".
- **Decisão de adoção:** **adotado** como gate do modo rigoroso: pelo menos uma
  sondagem com `purpose: counterexample-search` executada e registrada.

## 4. Skills públicas de método científico **[resumo]**

### 4.1 `scientific-thinking` e `evidence-first-debugging` (Jamie-BitFlight, plugin `scientific-method`)

- **Fonte:** páginas em skills.sh, tessl.io, claudepluginhub e uma cópia do
  `SKILL.md` publicada no pacote npm `aiden-runtime`. O repositório original
  pediu autenticação no clone, então não li os arquivos de referência completos.
- **Conceito útil:** IDs de evidência citados em cada afirmação (`[E3]`);
  afirmação sem ID vira `UNKNOWN`; cada hipótese com previsão e teste de
  falsificação; "causality gate" que só permite linguagem causal com
  classificação `causal-supported`; status final `resolved-verified` reservado a
  verificação com evidência; **divulgação obrigatória de saída truncada**
  (linhas totais, linhas mostradas, método, fingerprint, comando).
- **Como funciona:** template de 15 seções em Markdown e um checklist que o
  modelo deve conferir antes de responder.
- **Generalizável:** quase tudo; são boas regras de redação.
- **Limitações:** tudo é instrução em texto. Nada verifica mecanicamente se o
  checklist foi cumprido. O status final é escrito pelo próprio modelo.
- **Decisão de adoção:** **adotado em parte.** Citação obrigatória de IDs,
  previsão e falsificação por hipótese e divulgação de truncamento (campo
  `output_capture` na evidência). **Diferença central desta Skill:** o estado
  final é calculado por script a partir do ledger, não escrito pelo modelo.

### 4.2 `hypothesis-generation` (K-Dense-AI/claude-scientific-skills) e `hypothesis-formulation` (AutoResearchClaw)

- **Conceito útil:** hipótese nula e alternativa explícitas; definir de antemão o
  resultado que refutaria a hipótese.
- **Limitações:** focadas em pesquisa biomédica; uma delas exige figuras geradas
  por IA em todo relatório, o que é burocracia fora desse contexto.
- **Decisão:** **adotado** só o requisito de hipótese nula/conservadora e
  alternativa.

### 4.3 Skills de depuração "evidence-first" de outros autores

- Regras úteis vistas em resumos: "evidência de runtime vence inferência
  estática"; "não encadear especulações (talvez A, então talvez B, então causa
  C)"; "não usar 'confirmado' ou 'definitivo' sem a evidência de runtime
  principal"; "trate resumos de agentes como evidência interpretada, não bruta".
- **Decisão:** **adotado** em `evidence-model.md` e `multi-agent-patterns.md`.

## 5. Sistemas multiagentes para pesquisa científica **[resumo]**

### 5.1 Google AI co-scientist (arXiv 2502.18864; Nature, 2026)

- **Conceito útil:** agentes especializados — geração, reflexão (revisor),
  ranking por torneio Elo, evolução, proximidade (deduplicação) e meta-revisão —
  coordenados por uma fila assíncrona de tarefas.
- **Generalizável:** separar quem propõe de quem critica; deduplicar hipóteses;
  um sintetizador final.
- **Específico do domínio / limitações:** o torneio mede preferência entre
  hipóteses, não verdade; o sistema escala computação de teste para gerar
  ideias novas, o que é um objetivo diferente de verificar uma conclusão.
- **Decisão:** **adaptado.** Papéis opcionais (coordenador, crítico, buscador de
  contraexemplos, verificador...) e a regra explícita de que **consenso ou
  ranking entre agentes não é evidência**. Torneio rejeitado.

## 6. Boas práticas oficiais de Skills **[lido]**

`platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices` e a
especificação aberta `agentskills.io/specification`.

- **Conceitos úteis:** `name` com até 64 caracteres, minúsculas, números e
  hífens, igual ao nome da pasta; `description` até 1024 caracteres, em terceira
  pessoa, dizendo o que faz e quando usar; corpo do `SKILL.md` abaixo de 500
  linhas; referências a um nível de profundidade; índice em referências com mais
  de 100 linhas; scripts que tratam erros em vez de delegar; dizer se o script
  deve ser **executado** ou **lido**; padrão "planejar → validar → executar →
  verificar"; laço "rodar validador → corrigir → repetir"; caminhos com barra
  normal; dependências explícitas; testar com mais de um modelo; pelo menos três
  avaliações antes de publicar.
- **Generalizável:** a especificação é aberta e lida por vários agentes (Claude
  Code, Codex, Cursor, Gemini CLI, Copilot e outros).
- **Decisão:** **adotado.** Uma consequência: o arquivo `agents/ui_metadata.yaml`
  do plano não existe em nenhum padrão que encontrei. O REA usa
  `agents/openai.yaml` (convenção do Codex, com `interface.display_name`,
  `short_description` e `default_prompt`). Usei esse nome, que tem efeito real
  num agente, em vez de um arquivo que nenhuma ferramenta lê.

## 7. Avaliação de agentes e testes determinísticos **[lido em parte]**

"Demystifying evals for AI agents", Anthropic Engineering, 2026-01-09.

- **Conceito útil:** eval = tarefa + graders + resultado; distinguir
  **transcrição** (o que o agente disse e fez) de **resultado** (estado final do
  ambiente); combinar graders determinísticos (código, regras) com graders por
  modelo calibrados por humanos; deixar o grader responder "Unknown" quando a
  evidência não basta; avaliar o resultado em vez de exigir uma sequência rígida
  de chamadas; distinguir evals de capacidade e de regressão; medir pass@k e
  pass^k.
- **Testes determinísticos de workflows:** o próprio REA faz isso
  (`verify:readiness`): fixtures redistribuíveis, avaliador sintético,
  verificação de determinismo, rejeição de evidência adulterada e de fonte
  desatualizada — e declara que isso não estabelece comportamento real.
- **Decisão:** **adotado.** Os scripts têm testes determinísticos
  (`tests/`, com horário fixo e saída comparada byte a byte). Os evals
  (`evals/`) avaliam o **ledger e o relatório produzidos** (resultado), com
  grader determinístico; a comparação com e sem a Skill fica para uma etapa
  posterior, como combinado.

---

## 8. Síntese: o que foi generalizado

| Princípio | Origem | Mecanismo nesta Skill |
| --- | --- | --- |
| Separar observação, derivação e inferência | REA | `epistemic_status`; evidência só pode ser `OBSERVED` ou `DERIVED` |
| Autoridade adequada para fechar | REA (implícito) | `authority-matrix.json` aplicada por `validate_ledger.py` |
| Desconhecidos residuais | REA | ledger `U-`, resolução exige autoridade |
| Obrigações verificáveis | REA | ledger `O-`, casos exigidos, bloqueadores |
| Ausência de evidência ≠ evidência de ausência | REA | regra central + `scope` obrigatório na evidência |
| Contradições preservadas | REA + plano | ledger `C-`, resolução exige evidência nova |
| Falsificação ativa | POPPER, 2604.22080 | sondagens com resultado esperado por hipótese; gate de contraexemplo |
| Proponente separado do crítico | co-scientist, POPPER | evidência `role: review` de outro coletor; consenso não é prova |
| Status final não é escrito pelo modelo | lacuna das skills de texto | `evaluate_completion.py` calcula |
| Divulgar truncamento | evidence-first-debugging | `output_capture` |

## 9. O que esta Skill não copia

- Nenhum código, schema ou texto do REA foi copiado. Os nomes de conceitos
  (evidence, residual unknown, obligation, authority) foram mantidos para que
  quem conhece o REA reconheça a origem.
- Nenhuma ferramenta de engenharia reversa: a Skill não analisa binários. O
  adaptador de engenharia reversa só orienta o que conta como evidência.
- Nenhum arquivo de Burnout 3 ou de qualquer software proprietário.
