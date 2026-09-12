# Hackathon AI 2026 — Radar de Débitos Técnicos

Pipeline de análise estática que varre um repositório legado, normaliza os achados de
várias ferramentas em um formato único e prioriza os débitos técnicos **contra o
contexto de negócio** da empresa fictícia do desafio.

Este é o repositório de trabalho do time. O material oficial da hackathon
(briefing, código-alvo, ambiente) foi importado para cá — veja
[`docs/UPSTREAM.md`](docs/UPSTREAM.md) para procedência e como sincronizar.

---

## Leia antes de codar

Nessa ordem:

1. **[`docs/cenario-do-desafio.md`](docs/cenario-do-desafio.md)** — o briefing. Entregas
   obrigatórias, critérios de avaliação e **penalidades**.
2. **[`docs/business-context.md`](docs/business-context.md)** — a situação da HourTrack.
   Isto não é enfeite: são os pesos do `scoring.py`.
3. **[`docs/security-questionnaire.md`](docs/security-questionnaire.md)** — as 7 perguntas
   do cliente enterprise. Cada achado que responde "não" a uma delas vale dinheiro.
4. **[`docs/ferramentas.md`](docs/ferramentas.md)** — schema do JSON de saída de cada
   ferramenta, com exemplos reais. Consulta obrigatória ao escrever os `detectors/`.

---

## Ambiente

**Use o Docker.** É o caminho suportado.

```bash
cp .env.example .env                    # opcional, só para o enriquecimento via Gemini
docker compose build                    # primeira vez, ~3 min
docker compose run --rm analyzer bash   # shell com todas as ferramentas
```

Dentro do container:

| Caminho | Conteúdo |
|---|---|
| `/workspace` | este repositório (leitura/escrita, sincronizado com o host) |
| `/repos/python` | `fixtures/bad-codebase-python` — alvo principal (read-only) |
| `/repos/php` | `fixtures/bad-codebase` — alvo do bônus (read-only) |

Os alvos ficam nos mesmos paths do ambiente oficial da organização, de propósito:
todos os comandos de exemplo do `docs/ferramentas.md` funcionam colando direto.

Edite os arquivos no host com seu editor; rode dentro do container.

### ⚠️ Não rode as ferramentas em Python 3.14

O `requirements.txt` está pinado nas versões da imagem oficial, que roda **Python
3.11**. Duas coisas quebram em 3.14 — uma delas de forma **silenciosa e perigosa**:

**1. `bandit==1.7.9` reporta zero achados em 3.14, sem erro.**

Cada arquivo falha internamente com `AttributeError: 'Constant' object has no
attribute 's'` (bandit usa `ast.Constant.s`, removido no 3.12+). O bandit então:

- **sai com código 0** (parece sucesso)
- imprime `Total issues: High: 0, Medium: 0, Low: 0`
- no JSON, devolve `"results": []`
- só menciona `(exception while scanning file)` no output de texto, no fim

Ou seja: em 3.14 o alvo parece **livre de vulnerabilidades**. Segurança é a
categoria de maior peso no nosso scoring (questionário do enterprise em 30 dias) —
um falso "tudo limpo" aqui destrói o relatório inteiro e não dá nenhum sinal de erro.

> **Consequência de design:** o pipeline não pode tratar "bandit saiu 0" como
> "bandit funcionou". Vale checar `results` vazio + arquivos skipados e falhar
> alto. Isso também cobre o requisito do briefing de degradar com elegância
> quando a ferramenta não está disponível no ambiente de avaliação.

**2. `pydantic==2.8.2` não instala em 3.14.**

`pydantic-core==2.20.1` não tem wheel para cp314, cai para build do sdist via
Rust/maturin e falha. É o único pin que impede um venv local — e note que o
briefing pede `models.py` com **dataclass**, não pydantic. Se ninguém for usar
pydantic de verdade, tirar esse pin destrava o venv local.

**O que foi verificado em 3.14:** `radon==6.0.1` funciona e reproduz exatamente a
tabela de CC do `docs/ferramentas.md`. `bandit` falha como descrito acima.
`pydantic` não instala. `semgrep==1.93.0` instala (wheel tagueada até py311),
mas **não testamos se roda correto** — assuma que não até alguém confirmar.
`pylint==3.3.1` instala; execução em 3.14 também não testada.

Conclusão: use o container para qualquer número que entre no relatório. Um venv
local serve para autocomplete e `pytest` do scoring — não para rodar as ferramentas.

### Verificação do ambiente (rodar uma vez, antes de codar)

A imagem **não foi buildada ainda** — o ambiente onde o material foi importado não
tinha acesso de rede para os containers. Quem tiver rede, rode:

```bash
docker compose build                    # ~3 min: apt + composer + pip
docker compose run --rm analyzer bash
```

Já dentro do container, o smoke test que importa — as três ferramentas devem
achar coisa, e o bandit **não pode** voltar vazio:

```bash
# 1. as ferramentas existem?
bandit --version && radon --version && pylint --version && semgrep --version
phpstan --version && phpmetrics --version   # bônus

# 2. bandit acha vulnerabilidade? (DEVE ser > 0 — se vier 0, algo está errado)
bandit -r /repos/python/app -f json -q 2>/dev/null \
  | python3 -c "import json,sys; r=json.load(sys.stdin)['results']; print(f'bandit: {len(r)} achados'); assert r, 'BANDIT VAZIO - nao confie neste ambiente'"

# 3. radon reproduz a tabela do docs/ferramentas.md?
#    esperado: handle_date=29, dashboard=16, send=12, monthly=12, calculate_invoice=10
radon cc /repos/python/app -s -n B

# 4. pylint roda?
pylint /repos/python/app --output-format=json --disable=C 2>/dev/null \
  | python3 -c "import json,sys; print(f'pylint: {len(json.load(sys.stdin))} mensagens')"
```

O passo 2 é o que protege contra o modo de falha silenciosa descrito acima.
Se ele passar no container, o ambiente está confiável.

---

## Estrutura

```
.
├── docs/           material oficial importado (não editar — ver UPSTREAM.md)
├── fixtures/       os dois códigos-alvo (não editar, não consertar — ver fixtures/README.md)
├── docker/         Dockerfile do ambiente de análise
├── requirements.txt
└── (o pipeline entra aqui)
```

O pipeline ainda não existe — o repositório está com o material pronto e o
ambiente funcionando. A estrutura que o **briefing pede** (`cenario-do-desafio.md`,
seção "Estrutura esperada do gerador") é:

```
analyzer/
├── main.py              # entry point: recebe path do repo, orquestra o pipeline
├── detectors/
│   ├── python.py        # invoca bandit/radon/pylint → lista de Finding
│   └── php.py           # invoca phpstan/phploc (bônus)
├── models.py            # dataclass Finding com campos normalizados
├── scoring.py           # scoring model determinístico
├── report.py            # renderiza Markdown e JSON
└── tests/
    └── test_scoring.py  # testes unitários do scoring model
```

Fica a critério do time seguir isso à risca ou não — mas divergir do que o
briefing descreve é uma escolha que vale explicar no README final.

---

## Restrições do desafio que afetam o design

Extraídas do briefing — vale reler antes de abrir PR:

- **Scoring determinístico.** Duas execuções no mesmo alvo, mesmo resultado.
  Pipeline não determinístico é *desclassificado como entrega técnica*.
- **LLM não decide prioridade.** IA pode redigir descrição e impacto; detecção e
  priorização são computadas pelo pipeline.
- **As ferramentas podem não estar instaladas no ambiente de avaliação.** O pipeline
  precisa de um caminho que funcione sem `bandit`/`radon`/`pylint` — degradar com
  elegância, não estourar exceção.
- **Falso positivo desconta ponto.** Reportar como débito algo que não é problema
  real custa nota. Menos achados bem justificados > muitos achados.
- **As regras de priorização vão no código**, comentadas ou em arquivo de config —
  não só no relatório.

### Pegadinha: o `rank` do radon não bate com a tabela do briefing

Verificado rodando radon no fixture. A escala real do radon é `A:1-5, B:6-10,
C:11-20, D:21-30, E:31-40, F:41+` — diferente da tabela do `docs/ferramentas.md`
(`C:11-15, D:16-20, E:21-25, F:26+`). E o próprio doc é inconsistente: lista
`dashboard` (CC=16) como `C` em uma tabela e `D` em outra.

Exemplo concreto: `handle_date` tem CC=29. O radon devolve `"rank": "D"`; a tabela
do briefing diria `F`.

Se o `scoring.py` consumir o campo `rank` do JSON do radon direto, a severidade não
vai corresponder ao que o briefing descreve. Decidam qual escala usar, **derivem o
rank do `complexity` numérico** em vez de confiar no campo, e documentem a escolha —
é exatamente o tipo de decisão explícita que os 25% de "regras justificadas" premiam.

---

## Entregas

1. **Relatório** de débitos priorizados (campos obrigatórios no briefing), incluindo
   uma seção *"O que a IA sugeriu que estava errado, e por quê"*.
2. **Pipeline** que recebe o path de um repositório e gera relatório em Markdown e JSON.
3. **README do pipeline** explicando como rodar e como o scoring model funciona.

Bônus (10%): suportar também o alvo PHP com o mesmo scoring model e o mesmo formato.
