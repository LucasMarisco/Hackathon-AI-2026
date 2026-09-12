"""Julgamento humano verificado — a curadoria do time.

Este arquivo é deliberadamente separado do resto: é onde mora o que NENHUMA
ferramenta produz e nenhuma IA decide. Cada entrada foi aberta no editor,
conferida contra o código-fonte e justificada por escrito.

Fica versionado no Git para que a verificação seja auditável: quem afirmou o
quê, com qual justificativa, em qual commit.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Seção obrigatória do relatório:
# "O que a IA sugeriu que estava errado, e por quê"
#
# O enunciado avisa: "a IA erra. Ela inventa problemas que não existem e deixa
# passar problemas reais. Validar o output da IA é uma habilidade — e será
# avaliada."
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

# ---------------------------------------------------------------------------
# Planos de remediação por pergunta do questionário de segurança.
# Esforço em story points, na capacidade real de 6 SP/semana.
# ---------------------------------------------------------------------------
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

# Perguntas que as ferramentas deste pipeline não conseguem responder.
# Declarar isso é mais honesto — e mais defensável — do que responder "Sim"
# por ausência de achado.
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
