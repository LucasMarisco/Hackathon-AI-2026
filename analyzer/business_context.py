"""Contexto de negócio da HourTrack aplicado a cada débito.

É aqui que o pipeline deixa de ser repassador de ferramenta. Nenhuma
ferramenta sabe que existe um cliente de R$ 8.000/mês perguntando sobre hash
de senha em 30 dias. Esse conhecimento vem de dois documentos do repositório:

  - docs/business-context.md       (prazos, time, receita, restrições)
  - docs/security-questionnaire.md (as 7 perguntas do cliente enterprise)

Todas as regras são TABELAS, não lógica espalhada, para que o critério possa
ser lido e contestado sem interpretar código.

REGRA DO PROJETO: nenhum fator entra aqui sem a frase do business-context.md
que o justifica, escrita ao lado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. QUESTIONÁRIO DE SEGURANÇA — o prazo de 30 dias que vale R$ 8.000/mês
#
#   "cliente enterprise (200+ usuários, contrato de R$ 8.000/mês) está em
#    negociação. Ele pediu um questionário de segurança antes de assinar...
#    Se fechar, dobra o MRR"
#
# Q1 SQL Injection   Q3 hash seguro de senha   Q5 sem .env real no repo   Q7 sem MD5/SHA-1
# Q2 XSS             Q4 credenciais fora do código                        Q6 debug desligado
# ---------------------------------------------------------------------------
PERGUNTAS_POR_CONCEITO: dict[str, tuple[int, ...]] = {
    "dynamic_sql": (1,),
    "weak_password_hash": (3, 7),   # derruba DUAS respostas com um só commit
    "hardcoded_secret": (4,),
}

# ---------------------------------------------------------------------------
# 2. EXPOSIÇÃO DE DADOS DE CLIENTE
#
#   "o sistema processa dados de contratos entre agências e seus clientes —
#    vazamento poderia gerar processo"
#   "os dados de todos os clientes estão no mesmo banco sem isolamento"
#
# Não marcamos todo achado de segurança: só o que dá acesso a DADOS DE
# CLIENTE. Um segredo de SMTP é grave por outro motivo (phishing), não por
# vazamento de dados.
# ---------------------------------------------------------------------------
CONCEITOS_QUE_EXPOEM_DADOS = {"dynamic_sql", "weak_password_hash"}
SEGREDOS_COM_DADOS_DE_CLIENTE = ("CONTABILIZEI", "ERP", "CRM")

# ---------------------------------------------------------------------------
# 3. CAMINHO DA RELEASE v2.1
#
#   "release v2.1 em 14 dias — nova funcionalidade de relatório por projeto
#    (já comprometida com 3 clientes grandes)... dois clientes ameaçaram
#    cancelar se não entregar"
#
# Débito nestes arquivos deve ser corrigido JUNTO com a feature (custo ~1x)
# em vez de depois dela (custo ~3x).
# ---------------------------------------------------------------------------
ARQUIVOS_DA_RELEASE = (
    "app/routes/report_routes.py",
    "app/services/billing_service.py",
    "app/everything.py",
)

# ---------------------------------------------------------------------------
# 4. ESFORÇO DE CORREÇÃO, em story points
#
#   "capacidade real: ~6 story points por semana" + "não há QA. Não há DevOps"
# ---------------------------------------------------------------------------
ESFORCO_POR_CONCEITO: dict[str, float] = {
    "dynamic_sql": 0.5,          # trocar f-string por placeholder ?
    "hardcoded_secret": 2.0,     # mover para env + ROTACIONAR (já vazou no Git)
    "weak_password_hash": 3.0,   # migrar para bcrypt/Argon2 + rehash no login
    "missing_timeout": 0.5,
    "swallowed_exception": 1.0,
    "broad_exception": 1.0,
    "inconsistent_returns": 1.0,
    "unused_variable": 0.5,
    "todo_comment": 0.5,
    "shadowed_builtin": 0.5,
    "unnecessary_else_after_return": 0.5,
    "excessive_returns": 2.0,
    "excessive_branches": 3.0,
    "excessive_locals": 2.0,
    "import_error": 0.5,
}
ESFORCO_PADRAO = 1.0
ESFORCO_COMPLEXIDADE_ALTA = 8.0   # CC >= 20: reescrita, não ajuste

# ---------------------------------------------------------------------------
# 5. IMPACTO DE NEGÓCIO — em linguagem de CEO, com número do business-context
#
# Números disponíveis: R$ 28.000 MRR, R$ 8.000/mês do enterprise, 47 clientes,
# ~180 usuários, 3 clientes = 60% da receita, 1 VPS, 99,1% de uptime.
# ---------------------------------------------------------------------------
IMPACTO_POR_CONCEITO: dict[str, str] = {
    "dynamic_sql": (
        "Permite ler e alterar a base inteira sem autenticação: as horas "
        "faturadas dos 47 clientes estão no mesmo banco, sem isolamento. "
        "Um vazamento atinge os 3 clientes que respondem por 60% da receita."
    ),
    "weak_password_hash": (
        "Senhas em MD5 são quebráveis em minutos. Derruba duas das sete "
        "respostas do questionário do cliente de R$ 8.000/mês — o contrato "
        "que dobraria o MRR de R$ 28.000."
    ),
    "hardcoded_secret": (
        "Credencial de produção exposta no código e no histórico do Git. "
        "Responder 'Não' à pergunta 4 do questionário trava a assinatura do "
        "contrato enterprise; apagar o arquivo não basta, exige rotação."
    ),
    "missing_timeout": (
        "Chamada externa sem timeout prende o processo. Com 1 VPS de 2GB "
        "atendendo 180 usuários e sem monitoramento, a queda só é descoberta "
        "quando o cliente liga."
    ),
    "swallowed_exception": (
        "Falha silenciosa: a fatura é calculada e não é gravada, sem ninguém "
        "saber. Sem monitoramento, o erro aparece na contestação do cliente."
    ),
    "cyclomatic_complexity": (
        "Função complexa demais para alterar com segurança. O desenvolvedor "
        "que escreveu 90% do código sai em 6 semanas, e não há testes nem "
        "staging — o conhecimento sai junto com ele."
    ),
    "import_error": (
        "Sinal de ambiente de análise incompleto, não de defeito do produto. "
        "Verificar antes de reportar ao cliente."
    ),
}
IMPACTO_PADRAO = (
    "Aumenta o custo de manutenção de um time de 2 desenvolvedores com "
    "capacidade de 6 story points por semana e sem QA."
)

# ---------------------------------------------------------------------------
# 6. FALSOS POSITIVOS VERIFICADOS À MÃO
#
# O enunciado DESCONTA ponto por falso positivo. Cada entrada foi aberta no
# editor, lida e justificada. Chave: (conceito, arquivo) — nunca número de
# linha, que se desloca com qualquer edição do alvo.
# ---------------------------------------------------------------------------
FALSOS_POSITIVOS: dict[tuple[str, str], str] = {
    ("dynamic_sql", "app/everything.py"): (
        "Apenas a ocorrência da linha 205 (rota /delete) é falso positivo: a "
        "f-string interpola TABLE_MAP[thing], dicionário fechado de 4 itens "
        "definido na própria função. O usuário controla a chave, mas o valor "
        "só pode ser um dos 4 nomes de tabela — ou KeyError. Verificado à mão."
    ),
}
# Linhas específicas isentas dentro de um arquivo que tem ocorrências reais.
LINHAS_ISENTAS: dict[tuple[str, str], tuple[int, ...]] = {
    ("dynamic_sql", "app/everything.py"): (205,),
}

# ---------------------------------------------------------------------------
# 7. ONDE DISCORDAMOS DA FERRAMENTA
#
#   "os clientes não sabem que o sistema não tem autenticação real"
#
# O bandit classifica TODA SQL Injection como MEDIUM, em qualquer aplicação.
# Aqui a rota é pública e sem autenticação: a exploração é um comando curl.
# ---------------------------------------------------------------------------
MOTIVO_ELEVACAO_SQLI = (
    "bandit classifica toda SQL Injection como MEDIUM por padrão; neste "
    "sistema a rota é pública e não há autenticação, o que torna a exploração "
    "trivial. Elevado para severidade alta."
)


@dataclass
class ContextoNegocio:
    """Os fatores de negócio de um débito, todos deriváveis e auditáveis."""

    alcancavel: bool = True
    perguntas_questionario: tuple[int, ...] = ()
    expoe_dados: bool = False
    toca_release: bool = False
    rota_publica: bool = False
    esforco_sp: float = ESFORCO_PADRAO
    impacto: str = IMPACTO_PADRAO
    elevacao_severidade: str = ""
    notas: list[str] = field(default_factory=list)


def arquivos_com_rota(raiz: Path) -> set[str]:
    """Arquivos que registram rotas HTTP — a superfície de ataque."""

    encontrados: set[str] = set()
    for caminho in sorted(raiz.rglob("*.py")):
        if {".venv", "__pycache__", "venv"} & set(caminho.parts):
            continue
        try:
            if ".route(" in caminho.read_text(encoding="utf-8"):
                encontrados.add(caminho.relative_to(raiz).as_posix())
        except (UnicodeDecodeError, OSError):
            continue
    return encontrados


def eh_falso_positivo(conceito: str, arquivo: str, linha: int | None) -> str:
    """Devolve a justificativa se for falso positivo verificado, senão ''."""

    chave = (conceito, arquivo)
    if chave not in FALSOS_POSITIVOS:
        return ""
    linhas = LINHAS_ISENTAS.get(chave)
    if linhas is not None and linha not in linhas:
        return ""
    return FALSOS_POSITIVOS[chave]


def avaliar(
    conceito: str,
    arquivo: str | None,
    descricao: str,
    metric_value: float | None,
    mapa_alcancabilidade: dict[str, bool],
    rotas: set[str],
) -> ContextoNegocio:
    """Preenche os fatores de negócio de um débito."""

    ctx = ContextoNegocio()
    arquivo = arquivo or ""

    # .get(..., True): arquivo não mapeado é tratado como vivo — na dúvida,
    # nunca subestime o risco.
    ctx.alcancavel = mapa_alcancabilidade.get(arquivo, True)
    ctx.perguntas_questionario = PERGUNTAS_POR_CONCEITO.get(conceito, ())
    ctx.toca_release = arquivo in ARQUIVOS_DA_RELEASE
    ctx.rota_publica = arquivo in rotas and ctx.alcancavel

    if conceito in CONCEITOS_QUE_EXPOEM_DADOS:
        ctx.expoe_dados = True
    elif conceito == "hardcoded_secret":
        texto = descricao.upper()
        ctx.expoe_dados = any(s in texto for s in SEGREDOS_COM_DADOS_DE_CLIENTE)

    if conceito == "cyclomatic_complexity":
        cc = metric_value or 0
        ctx.esforco_sp = ESFORCO_COMPLEXIDADE_ALTA if cc >= 20 else 3.0
    else:
        ctx.esforco_sp = ESFORCO_POR_CONCEITO.get(conceito, ESFORCO_PADRAO)

    ctx.impacto = IMPACTO_POR_CONCEITO.get(conceito, IMPACTO_PADRAO)

    if conceito == "dynamic_sql" and ctx.rota_publica:
        ctx.elevacao_severidade = MOTIVO_ELEVACAO_SQLI

    if not ctx.alcancavel:
        ctx.notas.append(
            "código morto: nenhuma execução do sistema alcança este arquivo hoje"
        )

    return ctx
