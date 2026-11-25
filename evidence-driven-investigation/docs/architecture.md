# Arquitetura e decisões

Este documento é para quem mantém a Skill. O agente que usa a Skill não precisa
lê-lo; tudo que ele precisa está em `SKILL.md` e `references/`.

## 1. Visão geral

A Skill tem duas camadas que se completam:

1. **Instruções** (`SKILL.md`, `references/`): ensinam quando investigar, como
   formular hipóteses, o que conta como evidência e quando parar. Funcionam em
   qualquer agente que leia Markdown.
2. **Mecanismo** (`schemas/`, `scripts/`, `references/authority-matrix.json`):
   um ledger JSON e scripts determinísticos que recusam registros incoerentes e
   **calculam** o estado final. Funcionam em qualquer agente que execute
   Python 3.9+, sem dependências externas.

A camada de instruções sozinha é o que as skills de método científico já fazem.
A camada de mecanismo é o que esta Skill acrescenta: o agente não consegue
declarar `COMPLETE_VERIFIED` se o ledger não sustenta isso.

```
agente ──registra──▶ record_*.py ──▶ investigation.json ◀── validate_ledger.py
                                            │
                                            ├──▶ evaluate_completion.py ──▶ estado final calculado
                                            └──▶ generate_report.py ─────▶ relatório Markdown
```

## 2. Estrutura de arquivos

| Caminho | Função |
| --- | --- |
| `SKILL.md` | Ponto de entrada: seleção de modo, regras centrais, workflow, comandos. |
| `agents/openai.yaml` | Metadados de interface (convenção do Codex). Substitui o `ui_metadata.yaml` do plano, que nenhuma ferramenta lê. |
| `references/*.md` | Detalhes carregados sob demanda, um nível abaixo do `SKILL.md`. |
| `references/authority-matrix.json` | Vocabulário de autoridades e regras por tipo de afirmação. Lido pelos scripts. |
| `schemas/*.schema.json` | JSON Schema (Draft 2020-12) da estrutura de cada registro. |
| `scripts/ledger_core.py` | Biblioteca compartilhada: leitura/escrita atômica, IDs, validação de schema, regras semânticas, avaliação. |
| `scripts/*.py` | Um script por operação; cada um é uma camada fina sobre `ledger_core.py`. |
| `templates/` | Ledger vazio de referência e os dois modelos de relatório. |
| `examples/` | Quatro investigações reais, geradas pelos scripts a partir de execuções reais. |
| `evals/` | Casos, resultados esperados e grader determinístico. Comparação com/sem Skill fica para depois. |
| `tests/` | Testes `unittest` dos scripts. |
| `docs/` | Este documento e a análise das fontes. Não é lido pelo agente. |

### Desvios do plano original, e por quê

- **`agents/ui_metadata.yaml` → `agents/openai.yaml`.** Ver acima.
- **Scripts extras: `record_hypothesis.py`, `record_probe.py`,
  `record_obligation.py`, `record_finding.py`.** O plano lista scripts só para
  evidências, desconhecidos e contradições. Sem os outros, o agente editaria o
  JSON à mão para hipóteses, sondagens, obrigações e conclusões, que são
  justamente os registros que os gates mais verificam.
- **Schemas extras: `probe.schema.json` e `finding.schema.json`.** As sondagens
  (seção 9 do plano) e a classificação epistemológica de cada afirmação
  material (seção 6) precisam de um lugar no ledger.
- **`scripts/ledger_core.py`.** Evita sete cópias da mesma lógica de leitura,
  validação e escrita.
- **`tests/` e `docs/`.** Pedidos no plano como entregáveis, mas ausentes da
  árvore.

## 3. Modelo de dados

Um arquivo por investigação, `investigation.json`, com estas coleções:

| Prefixo | Coleção | Papel |
| --- | --- | --- |
| `E-` | `evidence` | O que foi observado ou calculado. Só `OBSERVED` ou `DERIVED`. |
| `H-` | `hypotheses` | Explicações candidatas, falsificáveis, com previsões. |
| `P-` | `probes` | Sondagens/experimentos: o que diferenciam, custo, risco, resultado. |
| `U-` | `unknowns` | Perguntas abertas, com autoridade exigida para fechar. |
| `C-` | `contradictions` | Conflitos entre afirmações ou evidências. |
| `O-` | `obligations` | Requisitos verificáveis de conclusão. |
| `F-` | `findings` | Afirmações materiais da conclusão, cada uma com um dos 9 estados epistêmicos. |

IDs são sequenciais por prefixo, nunca reutilizados, nunca apagados. Evidência
invalidada continua no ledger com `status: INVALIDATED`.

### Por que evidência só pode ser OBSERVED ou DERIVED

O plano lista nove estados epistêmicos. Eles se aplicam a **afirmações**
(`findings`), não a evidências. Uma inferência não é evidência; é uma afirmação
que a evidência sustenta ou não. Permitir `INFERRED` numa evidência criaria
exatamente o atalho que a Skill tenta fechar: uma inferência citando a si mesma
como prova.

### Integridade

Cada registro tem `record_digest` (SHA-256 do JSON canônico do registro sem o
próprio digest). Os scripts recalculam o digest a cada escrita. O validador
acusa digest divergente como erro, o que revela edição manual. Isso não impede
fraude deliberada (quem edita pode recalcular), mas torna a edição silenciosa
visível, que é o objetivo.

Quando o agente passa `--artifact-file`, o próprio script calcula o SHA-256 do
arquivo em vez de aceitar um hash digitado.

## 4. Matriz de autoridade

`references/authority-matrix.json` tem duas partes:

- `authorities`: vocabulário de autoridades (`compiler`, `unit-test`,
  `packaged-artifact-test`, `runtime-trace`, `static-analysis`,
  `round-trip-comparison`, `independent-calculation`, `numerical-test`,
  `formal-proof`, `reviewed-proof`, `primary-source`, `secondary-source`,
  `controlled-experiment`, `observational-data`, `user-report`...), cada uma
  com os `source_type` compatíveis.
- `claim_types`: tipo de afirmação → lista de cláusulas alternativas
  (`any_of`). Cada cláusula exige N evidências ativas com autoridades de um
  conjunto. Exemplo: `historical-claim` aceita 1 `primary-source` **ou** 2
  `secondary-source`.

Um campo `required_authority` (em obrigações e desconhecidos) aceita um tipo de
afirmação ou uma autoridade isolada. Adaptadores de domínio e investigações
individuais podem estender a matriz pelo campo `authority_extensions` do ledger,
com justificativa obrigatória.

**Limitação assumida:** a matriz compara rótulos. Se o agente rotular uma leitura
estática como `runtime-trace` e `source_type: runtime`, o script aceita. O que o
script garante é coerência interna (autoridade compatível com o tipo de fonte,
comando registrado, artefato com hash). A veracidade do rótulo depende da
revisão do relatório, que mostra o comando de cada evidência.

## 5. Cálculo do estado final

`evaluate_completion.py` não lê nenhum campo de status final. Ele calcula, nesta
ordem, e para no primeiro que se aplica:

1. **Ledger inválido** → não avalia, sai com código 2 e lista os erros.
2. **FAILED** — alguma obrigação crítica com status efetivo `FAILED`.
3. **BLOCKED** — alguma obrigação crítica ou desconhecido crítico `BLOCKED`.
4. **COMPLETE_VERIFIED** — todos os gates de fechamento (G1–G6) e de completude
   (G7–G8) passam.
5. **COMPLETE_WITH_LIMITATIONS** — G1–G6 passam, G7 ou G8 falha.
6. **MITIGATED_NOT_RESOLVED** — uma obrigação `kind: mitigation` fechada e uma
   `kind: root-cause` aberta.
7. **PARTIALLY_VERIFIED** — pelo menos uma obrigação fechada ou uma conclusão
   `VERIFIED`, mas algum gate de fechamento falha.
8. **INCONCLUSIVE** — nada verificado.

Gates:

| Gate | Condição |
| --- | --- |
| G1 | Existe pelo menos uma obrigação. |
| G2 | Toda obrigação crítica está `CLOSED` (efetivamente, não só no campo). |
| G3 | Nenhum desconhecido crítico em aberto (`OPEN`, `INVESTIGATING`, `BLOCKED`, `CONTRADICTED`). |
| G4 | Nenhuma contradição crítica em aberto. |
| G5 | Toda obrigação fechada tem evidência de verificação separada da de construção (IDs disjuntos; no modo rigoroso, também ferramenta ou comando diferente). |
| G6 | O ledger registra limitações (`limitations` não vazio). |
| G7 | Nada pendente fora do crítico: todas as obrigações fechadas (nenhuma `WAIVED`), nenhum desconhecido de severidade alta ou crítica em aberto ou fora de escopo, nenhuma contradição alta em aberto. |
| G8 | Requisitos do modo (seção 6). |

"Status efetivo" significa: uma obrigação marcada `CLOSED` cujo fechamento não se
sustenta (evidência invalidada, caso sem evidência, bloqueador aberto) já é
recusada pelo validador, então a avaliação nunca parte de um fechamento falso.

## 6. Modos

| Modo | Ledger | Requisitos extras (G8) |
| --- | --- | --- |
| `light` | Não recomendado. Se existir, só G1–G7. | Nenhum. |
| `investigative` | Sim. | Pelo menos 2 hipóteses, sendo uma não primária (`alternative`, `null` ou `measurement-error`). |
| `rigorous` | Sim. | Hipóteses `primary`, `null` e `alternative`; uma sondagem `counterexample-search` concluída; evidência `role: review` de coletor diferente dos de construção; toda evidência de verificação `reproducible: true`. |

O modo leve é o padrão para tarefas simples, e a regra principal do `SKILL.md`
para ele é **não criar ledger**. O caso de avaliação 5 mede isso.

## 7. Invalidação e reabertura

`record_evidence.py --invalidate E-0003 --reason "..."` marca a evidência e
reabre o que dependia dela:

- desconhecido `RESOLVED` que a cita na resolução → `OPEN`;
- contradição `RESOLVED` que a cita na resolução → `OPEN`;
- obrigação `CLOSED` que a cita como verificação ou caso → `OPEN`;
- conclusão `VERIFIED` que a cita como verificação → `UNKNOWN`;
- hipótese `VERIFIED` ou `REJECTED` que dependia dela → `TESTING`.

Cada reabertura entra no `history` do registro com o motivo.

## 8. Riscos e trade-offs

| Risco | Mitigação | O que sobra |
| --- | --- | --- |
| **Teatro de conformidade**: o agente preenche o ledger sem investigar de verdade. | Comando e artefato obrigatórios em evidência de runtime/teste; hash calculado pelo script; relatório mostra comandos para revisão. | Os scripts verificam coerência, não verdade. Declarado no README. |
| **Burocracia em tarefas simples.** | Modo leve sem ledger; tabela de seleção de modo no topo do `SKILL.md`; eval específico. | Depende do julgamento do agente na seleção de modo. |
| **Custo de tokens.** | `SKILL.md` curto; referências sob demanda; scripts imprimem saídas curtas. | O modo rigoroso é caro por natureza. |
| **Rigidez da matriz de autoridade.** | Extensões por adaptador e por investigação, com justificativa. | Extensões mal justificadas enfraquecem a garantia; aparecem no relatório. |
| **Agentes sem execução de código.** | As instruções funcionam sozinhas; schemas e templates permitem preencher o ledger à mão. | Sem scripts, o estado final volta a ser declarado pelo modelo. |
| **Falsa sensação de rigor.** | Seção "What this project does not claim"; estado final mais fraco que `COMPLETE_VERIFIED` é o caso comum e é apresentado como tal. | — |

## 9. Decisões menores

- **Python só com biblioteca padrão.** Roda em Windows, Linux e macOS sem
  `pip install`. Por isso há um validador de JSON Schema próprio que cobre o
  subconjunto usado (`type`, `properties`, `required`, `additionalProperties`,
  `enum`, `const`, `pattern`, `minLength`, `minItems`, `uniqueItems`, `items`,
  `$ref`, `$defs`, `format: date-time`). Um teste garante que os schemas não usam
  palavras-chave fora desse subconjunto e, se o pacote `jsonschema` estiver
  instalado, compara os dois validadores.
- **Regras condicionais ficam no código, não no schema.** Ex.: "evidência de
  runtime exige `command_or_method`". Schemas com `if/then` aninhados ficam
  ilegíveis, e as mensagens de erro do código são mais úteis para o agente.
- **Determinismo.** JSON com chaves ordenadas, indentação 2, `\n`, UTF-8. O
  horário vem de `--timestamp` ou da variável `EDI_FIXED_TIME`; sem eles, do
  relógio. Com horário fixo, a mesma sequência de comandos gera bytes idênticos.
- **Sem sobrescrita implícita.** `init` recusa arquivo existente; `record_*`
  recusa alterar um ID existente sem `--update`; `generate_report` recusa
  sobrescrever sem `--force`. Toda escrita é atômica (arquivo temporário +
  `os.replace`).
- **Idioma.** Instruções para o agente, código e README em inglês (padrão de
  publicação de skills e melhor para seguir instruções em qualquer modelo);
  `README.pt-BR.md` e estes documentos de manutenção em português.
- **Nome.** Mantido `evidence-driven-investigation`. Considerei
  `evidence-gated-investigation`, que destaca o diferencial (gates calculados),
  mas o nome original já descreve investigação, evidência e verificação, e é mais
  fácil de encontrar.
