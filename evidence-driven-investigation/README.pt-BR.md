# evidence-driven-investigation (resumo em português)

Uma Skill no formato aberto [Agent Skills](https://agentskills.io/specification)
que faz um agente de IA investigar com disciplina: separar o que observou do
que inferiu, testar hipóteses concorrentes, manter desconhecidos e contradições
visíveis e **calcular** se o trabalho está concluído, em vez de declarar.

Funciona com qualquer modelo. As instruções são Markdown; o mecanismo é um
ledger JSON e scripts Python que usam só a biblioteca padrão (Python 3.9+).

O README completo, em inglês, está em [README.md](README.md). A análise das
fontes (REA, POPPER, skills de método científico, boas práticas de Skills,
avaliação de agentes) e as decisões de arquitetura estão em português em
[docs/research-analysis.md](docs/research-analysis.md) e
[docs/architecture.md](docs/architecture.md).

## Em uma frase

O agente registra evidências, hipóteses, sondagens, desconhecidos,
contradições, obrigações e conclusões com IDs estáveis; os scripts recusam
registros incoerentes (por exemplo, fechar uma obrigação com evidência de
autoridade insuficiente) e o `evaluate_completion.py` calcula o estado final,
de `COMPLETE_VERIFIED` a `FAILED`.

## Modos

- **Leve**: tarefa simples; fazer, verificar, responder. Sem ledger.
- **Investigativo**: causa desconhecida, explicações concorrentes, engenharia
  reversa, depuração, análise exploratória.
- **Rigoroso**: afirmação extraordinária, matemática ou ciência, segurança,
  impacto alto, reprodutibilidade, pedido de prova ou auditoria.

## Instalação rápida

```
python tools/package_skill.py evidence-driven-investigation
```

Descompacte `dist/evidence-driven-investigation-1.0.0.zip` em
`~/.claude/skills/` (Claude Code) ou na pasta de skills do seu agente.

## Testes

```
cd evidence-driven-investigation
python -m unittest discover -s tests
```

## O que este projeto não afirma

Não torna modelos infalíveis, não garante descoberta científica, não substitui
especialistas, não transforma evidência fraca em prova, não elimina
alucinações, não fornece ferramentas de domínio e não substitui validação
experimental, formal ou humana. Os scripts verificam coerência, não verdade.
