"""Priorização final: o score técnico do time modulado pelo contexto de negócio.

A camada de `scoring.py` responde "quão grave é isto tecnicamente?".
Esta camada responde "o que a HourTrack deve fazer primeiro?" — e são
perguntas diferentes. Uma SQL Injection numa rota que retorna 404 é gravíssima
em abstrato e não é urgente hoje.

FÓRMULA (implementada exatamente como descrita — confira em `pontuar`):

    pontuacao = base_tecnica
              x alcancabilidade
              x exposicao_de_dados
              x rota_publica
              + bonus_questionario
              + bonus_release
              - (esforco_sp x penalidade_por_sp)

Duas propriedades exigidas pelo enunciado:

1. DETERMINÍSTICA — só aritmética sobre campos e constantes. Sem
   `datetime.now()`, sem `random`, sem `hash()`, sem chamada de IA.
2. JUSTIFICÁVEL — cada termo tem a citação do business-context.md em
   `business_context.py`, e o memorial de cálculo de cada débito é guardado
   para o relatório mostrar a conta aberta.

SOBRE OS PESOS: as magnitudes NÃO são derivadas de dados. São calibração
contra âncoras de julgamento declaradas pelo time:

    SQLi alcançável > MD5 em senha > segredo de produção
        > SQLi em código morto > exceção engolida > ruído de linter

Os pesos foram escolhidos para satisfazer essa ordem. A ordem é a tese que o
time defende; os números são a codificação dela.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from business_context import ContextoNegocio

# --- base técnica: vem do score_priority do scoring.py do time -------------
# O modelo quantitativo do time classifica em alto/medio/baixo. Aqui isso
# entra como SEVERIDADE-BASE, não como resposta final.
BASE_POR_PRIORIDADE_TECNICA = {"alto": 7.0, "medio": 4.0, "baixo": 2.0}
BASE_PADRAO = 2.0

# --- multiplicadores -------------------------------------------------------
# "uptime nos últimos 6 meses: 99,1%" — o sistema funciona; o que não executa
# não gera incidente hoje. Não zeramos: vira risco real no primeiro commit
# que registrar o blueprint.
FATOR_ALCANCAVEL = 1.0
FATOR_CODIGO_MORTO = 0.35

# "vazamento poderia gerar processo" + "dados de todos os clientes no mesmo
# banco sem isolamento"
AMPLIFICADOR_EXPOE_DADOS = 1.6

# "os clientes não sabem que o sistema não tem autenticação real"
# Muda a probabilidade de exploração, não a gravidade — por isso multiplica.
AMPLIFICADOR_ROTA_PUBLICA = 1.3

# --- bônus -----------------------------------------------------------------
# "questionário de segurança... respostas necessárias em 30 dias... Se fechar,
# dobra o MRR". Maior bônus do modelo: é o único prazo com preço e o único que
# NÃO compete com a release pelo tempo dos devs — escrever resposta não é
# escrever feature.
BONUS_QUESTIONARIO = 4.0
BONUS_QUESTIONARIO_EXTRA = 2.0   # por pergunta adicional que o mesmo achado derruba

# "release v2.1 em 14 dias... dois clientes ameaçaram cancelar"
BONUS_TOCA_RELEASE = 1.5

# --- penalidade ------------------------------------------------------------
# "capacidade real: ~6 story points por semana". Um achado de 8 SP não é
# prioridade alta: é prioridade que não cabe na agenda.
PENALIDADE_POR_SP = 0.8

# --- faixas ----------------------------------------------------------------
FAIXAS = ((15.0, "Crítica"), (10.0, "Alta"), (5.0, "Média"), (0.0, "Baixa"))

CAPACIDADE_SP_SEMANA = 6   # "capacidade real: ~6 story points por semana"


@dataclass
class DebitoPriorizado:
    """Um débito com os 9 campos que o enunciado exige no relatório."""

    id: str
    conceito: str
    categoria: str
    nome: str
    descricao: str
    arquivo: str
    linha: int | None
    impacto: str
    risco: str
    esforco_sp: float
    valor: str
    prioridade: str
    pontuacao: float
    memorial: list[str] = field(default_factory=list)
    contexto: ContextoNegocio | None = None
    ferramentas: tuple[str, ...] = ()
    prioridade_tecnica: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conceito": self.conceito,
            "categoria": self.categoria,
            "nome": self.nome,
            "descricao": self.descricao,
            "arquivo": self.arquivo,
            "linha": self.linha,
            "impacto": self.impacto,
            "risco": self.risco,
            "esforco_sp": self.esforco_sp,
            "valor": self.valor,
            "prioridade": self.prioridade,
            "pontuacao": self.pontuacao,
            "memorial": self.memorial,
            "ferramentas": list(self.ferramentas),
            "prioridade_tecnica": self.prioridade_tecnica,
            "alcancavel": self.contexto.alcancavel if self.contexto else True,
            "perguntas_questionario": (
                list(self.contexto.perguntas_questionario) if self.contexto else []
            ),
        }


def pontuar(prioridade_tecnica: str, ctx: ContextoNegocio) -> tuple[float, list[str]]:
    """Calcula a pontuação de um débito e o memorial da conta."""

    passos: list[str] = []

    pontos = BASE_POR_PRIORIDADE_TECNICA.get(prioridade_tecnica, BASE_PADRAO)
    passos.append(f"base técnica ({prioridade_tecnica}) = {pontos:.2f}")

    if not ctx.alcancavel:
        pontos *= FATOR_CODIGO_MORTO
        passos.append(f"x código morto ({FATOR_CODIGO_MORTO}) = {pontos:.2f}")

    if ctx.expoe_dados:
        pontos *= AMPLIFICADOR_EXPOE_DADOS
        passos.append(f"x expõe dados de cliente ({AMPLIFICADOR_EXPOE_DADOS}) = {pontos:.2f}")

    if ctx.rota_publica:
        pontos *= AMPLIFICADOR_ROTA_PUBLICA
        passos.append(f"x rota pública sem auth ({AMPLIFICADOR_ROTA_PUBLICA}) = {pontos:.2f}")

    if ctx.perguntas_questionario:
        extras = len(ctx.perguntas_questionario) - 1
        bonus = BONUS_QUESTIONARIO + extras * BONUS_QUESTIONARIO_EXTRA
        pontos += bonus
        qs = ", ".join(f"Q{q}" for q in ctx.perguntas_questionario)
        passos.append(f"+ questionário {qs} ({bonus}) = {pontos:.2f}")

    if ctx.toca_release:
        pontos += BONUS_TOCA_RELEASE
        passos.append(f"+ caminho da release v2.1 ({BONUS_TOCA_RELEASE}) = {pontos:.2f}")

    penalidade = ctx.esforco_sp * PENALIDADE_POR_SP
    pontos -= penalidade
    passos.append(f"- esforço {ctx.esforco_sp} SP ({penalidade:.2f}) = {pontos:.2f}")

    # round() evita que ruído de ponto flutuante empurre um débito de faixa.
    return round(pontos, 2), passos


def faixa(pontuacao: float) -> str:
    for corte, nome in FAIXAS:
        if pontuacao >= corte:
            return nome
    return "Baixa"


def calcular_risco(ctx: ContextoNegocio, prioridade_tecnica: str) -> str:
    """Risco = probabilidade de o problema se manifestar (campo exigido)."""

    if not ctx.alcancavel:
        return "Baixo"
    if ctx.rota_publica and prioridade_tecnica == "alto":
        return "Alto"
    if prioridade_tecnica == "alto":
        return "Médio"
    return "Baixo" if prioridade_tecnica == "baixo" else "Médio"


VALOR_POR_CATEGORIA = {
    "security": "Segurança e conformidade — destrava o contrato enterprise",
    "reliability": "Confiabilidade — evita erro de faturamento",
    "availability": "Disponibilidade — protege o uptime de 99,1%",
    "maintainability": "Manutenibilidade — reduz o risco da saída do dev em 6 semanas",
    "code_quality": "Qualidade — acelera o time de 2 devs",
    "architecture": "Arquitetura — sustenta o crescimento pós-enterprise",
    "environmental": "Higiene do ambiente de análise",
}

CATEGORIA_PT = {
    "security": "Segurança",
    "reliability": "Manutenibilidade",
    "availability": "Performance",
    "maintainability": "Manutenibilidade",
    "code_quality": "Design",
    "architecture": "Arquitetura",
    "environmental": "Arquitetura",
}


def ordenar_e_numerar(debitos: list[DebitoPriorizado]) -> list[DebitoPriorizado]:
    """Ordena por pontuação e só então atribui os IDs.

    A ordem de desempate é parte do determinismo: duas execuções precisam
    produzir a mesma sequência mesmo quando dois débitos empatam. Desempate
    por campos estáveis, nunca pela ordem em que a ferramenta devolveu.
    """

    debitos.sort(key=lambda d: (-d.pontuacao, d.arquivo, d.linha or 0, d.conceito))
    for i, debito in enumerate(debitos, start=1):
        debito.id = f"DT-{i:02d}"
    return debitos
