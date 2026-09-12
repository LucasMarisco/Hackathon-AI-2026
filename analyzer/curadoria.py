

from __future__ import annotations


# ---------------------------------------------------------------------------
AUDITORIA_DA_IA: tuple[dict[str, str], ...] = (
    {
        "afirmacao": "O banco database.sqlite está commitado no repositório.",
        "origem": "IA (repetindo o business-context.md)",
        "porque_errado": (
            "Falso para o repositório Python. O .gitignore ignora *.sqlite e "
            "não há nenhum arquivo .sqlite rastreado. A IA repetiu o "
            "documento de contexto em vez de olhar o repositório."
        ),
        "como_verificamos": "git ls-files | grep -i sqlite — nenhum resultado",
    },
    {
        "afirmacao": "Há um arquivo .env com credenciais reais commitado.",
        "origem": "IA (repetindo o business-context.md)",
        "porque_errado": (
            "Falso. Só existe .env.example, sem valores. É a única das 7 "
            "perguntas do questionário cuja resposta honesta hoje é 'Sim'."
        ),
        "como_verificamos": "git ls-files | grep env — apenas .env.example",
    },
    {
        "afirmacao": "SQL Injection crítica e explorável em /api/reports/monthly.",
        "origem": "bandit B608 + IA",
        "porque_errado": (
            "O código É vulnerável, mas o blueprint report_bp nunca é "
            "registrado na aplicação: a rota retorna 404 hoje. É risco "
            "LATENTE, não exposição ativa. A ferramenta analisa arquivo por "
            "arquivo e não enxerga o grafo de chamadas."
        ),
        "como_verificamos": (
            "grep -rn 'register_blueprint' — nenhum resultado; confirmado pelo "
            "módulo reachability.py deste pipeline"
        ),
    },
    {
        "afirmacao": "SQL Injection na rota /delete (app/everything.py:205).",
        "origem": "bandit B608",
        "porque_errado": (
            "A f-string interpola TABLE_MAP[thing], um dicionário fechado de 4 "
            "itens definido na própria função. O usuário controla a chave, mas "
            "o valor só pode ser um dos 4 nomes de tabela — ou KeyError. Não há "
            "vetor de injeção. Descartado do relatório."
        ),
        "como_verificamos": "leitura manual de app/everything.py:196-207",
    },
    {
        "afirmacao": "O SELECT * do dashboard expõe a senha na resposta HTTP.",
        "origem": "comentário no próprio código-fonte + IA",
        "porque_errado": (
            "A senha é carregada em memória, mas o loop de renderização usa "
            "apenas ['name', 'email', 'address'] — ela não sai na resposta. A "
            "IA acreditou no comentário do código em vez de ler o render. É "
            "over-fetch, severidade baixa."
        ),
        "como_verificamos": "leitura manual de app/everything.py:132-145",
    },
    {
        "afirmacao": "Os testes do pipeline provam que o scoring é determinístico.",
        "origem": "código gerado por IA nesta sessão",
        "porque_errado": (
            "Um dos testes comparava listas de IDs sequenciais (DT-01, DT-02...) "
            "que são atribuídos DEPOIS da ordenação — ele passava mesmo se o "
            ".sort() fosse removido. Teste vacuamente verdadeiro. Corrigido "
            "para comparar (arquivo, linha)."
        ),
        "como_verificamos": "auditoria dirigida ao código gerado, antes do commit",
    },
)


REMEDIACAO_QUESTIONARIO: dict[int, str] = {
    1: "Trocar toda f-string em query por placeholder `?`. 0,5 SP por ocorrência.",
    2: "Escapar o output do dashboard (usar template com autoescape). 2 SP.",
    3: "Migrar para bcrypt/Argon2 com rehash no próximo login. 3 SP.",
    4: "Mover segredos para variáveis de ambiente e ROTACIONAR — já estão no histórico do Git. 2 SP.",
    5: "Nenhuma ação: já conforme. Manter a regra no .gitignore.",
    6: "Definir debug=False em produção. 0,5 SP, uma linha.",
    7: "Coberto pela migração da pergunta 3 — o mesmo commit resolve as duas.",
}

PERGUNTAS_QUESTIONARIO: dict[int, str] = {
    1: "O sistema é protegido contra SQL Injection?",
    2: "O sistema é protegido contra Cross-Site Scripting (XSS)?",
    3: "As senhas são armazenadas com hash seguro (bcrypt, PBKDF2 ou Argon2)?",
    4: "Credenciais e API keys estão fora do código-fonte e do repositório Git?",
    5: "O repositório não contém arquivos .env com valores reais commitados?",
    6: "O modo debug/desenvolvimento está desativado em produção?",
    7: "O código não utiliza algoritmos de hash inseguros (MD5, SHA-1)?",
}


PERGUNTAS_NAO_COBERTAS: dict[int, str] = {
    2: (
        "Nenhuma ferramenta do pipeline detecta XSS em HTML montado por "
        "f-string. Verificação manual encontrou o problema em "
        "app/everything.py:87-148 — o dashboard concatena nome de cliente sem "
        "escape, e o seed do banco já inclui um cliente chamado "
        "<script>alert(1)</script>."
    ),
    6: (
        "bandit possui a regra B201 para debug=True, mas ela não dispara aqui: "
        "`app` é importado de outro módulo e a ferramenta não consegue provar "
        "que é um objeto Flask. Verificação manual confirma debug=True em "
        "run.py:4."
    ),
}

# ---------------------------------------------------------------------------
# Achados de LEITURA MANUAL — o que nenhuma ferramenta detecta.
#
# Análise estática enxerga padrões sintáticos. Estes são defeitos de REGRA DE
# NEGÓCIO: o código roda, não gera exceção, e produz o número errado. Só
# aparecem quando alguém lê o fluxo e pergunta "isto faz sentido?".
#
# É a contraprova de que o pipeline não substitui leitura — ele prioriza o que
# a leitura e as ferramentas encontram.
# ---------------------------------------------------------------------------
ACHADOS_DE_LEITURA: tuple[dict[str, str], ...] = (
    {
        "titulo": "Fatura é calculada e nunca persistida",
        "local": "app/services/billing_service.py:70-78",
        "o_que": (
            "O INSERT grava numa tabela `invoices` que não existe no schema, "
            "dentro de um `try/except: pass`. A fatura é calculada, o e-mail é "
            "enviado ao cliente, e nada fica registrado."
        ),
        "impacto": (
            "Cliente contesta a cobrança e não há registro para provar. Com 3 "
            "dos 47 clientes respondendo por 60% da receita, uma contestação "
            "mal resolvida é perda material."
        ),
        "porque_ferramenta_nao_acha": (
            "Sintaticamente o INSERT é válido; a tabela só falta em tempo de "
            "execução, e a exceção é engolida."
        ),
    },
    {
        "titulo": "Exportação contábil usa R$ 150/h fixo",
        "local": "app/routes/report_routes.py:121",
        "o_que": (
            "O valor enviado à API da contabilidade é `hours * 150`, ignorando "
            "o `hourly_rate` da categoria."
        ),
        "impacto": (
            "Consultoria custa R$ 200/h e suporte R$ 100/h — ambos vão errados "
            "para a contabilidade. Não é bug de software, é erro fiscal."
        ),
        "porque_ferramenta_nao_acha": (
            "`150` é um número literal válido. Nenhum linter sabe que existe "
            "uma tabela de preços que deveria ter sido consultada."
        ),
    },
    {
        "titulo": "Desconto do cliente nomeado é inalcançável",
        "local": "app/services/billing_service.py:52-59",
        "o_que": (
            "A cadeia de `elif` testa `subtotal > 10000`, depois `> 5000`, e só "
            "então o nome do cliente. O desconto de 15% do Cogna só se aplica "
            "se ele faturar menos de R$ 5.000 no mês."
        ),
        "impacto": (
            "A regra comercial existe no código e nunca se aplica ao cliente "
            "grande para quem foi criada. Ninguém percebe porque o sistema não "
            "reclama."
        ),
        "porque_ferramenta_nao_acha": (
            "Todos os ramos são alcançáveis em tese; a inalcançabilidade vem "
            "da faixa de valores do cliente, não da estrutura do código."
        ),
    },
    {
        "titulo": "Um GET sem autenticação dispara centenas de e-mails",
        "local": "app/routes/report_routes.py:89-95",
        "o_que": (
            "`/api/reports/annual` chama `generate_monthly_report` 12 vezes; "
            "cada chamada calcula a fatura de todos os clientes, e cada cálculo "
            "envia e-mail. Com 47 clientes, são até 564 e-mails de fatura."
        ),
        "impacto": (
            "Incidente comercial, não técnico: clientes recebem faturas falsas "
            "em massa. Hoje contido apenas porque a rota não está registrada."
        ),
        "porque_ferramenta_nao_acha": (
            "Exige seguir três níveis de chamada — rota, serviço, notificação — "
            "e entender que o efeito colateral é envio real de e-mail."
        ),
    },
    {
        "titulo": "Sistema sem autenticação e sem isolamento entre clientes",
        "local": "app/everything.py:152, :195",
        "o_que": (
            "As rotas `/save/<thing>` e `/delete/<thing>/<id>` não verificam "
            "identidade nem autorização. Todos os clientes compartilham o mesmo "
            "banco sem coluna de tenant."
        ),
        "impacto": (
            "Qualquer pessoa com um navegador cria e apaga horas faturáveis de "
            "qualquer um dos 47 clientes. É o débito que transforma todos os "
            "outros em incidente: uma falha atrás de login exige credencial "
            "roubada, a mesma em rota pública é um comando curl."
        ),
        "porque_ferramenta_nao_acha": (
            "Ausência de código não é padrão detectável. Nenhum scanner reporta "
            "a verificação que ninguém escreveu."
        ),
    },
)
