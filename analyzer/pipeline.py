"""Orquestração: do repositório-alvo aos débitos priorizados.

Encadeia as camadas já existentes (parsers -> deduplicação -> classificação
-> scoring) com as camadas de negócio (alcançabilidade -> contexto ->
priorização).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import business_context as bc
from business_context import ContextoNegocio, arquivos_com_rota, avaliar, eh_falso_positivo
from classification import classify_groups
from deduplication import deduplicate_findings
from priorizacao import (
    CATEGORIA_PT,
    VALOR_POR_CATEGORIA,
    DebitoPriorizado,
    calcular_risco,
    faixa,
    ordenar_e_numerar,
    pontuar,
)
from reachability import mapear_alcancabilidade
from scoring import score_groups
from tool_runner import coletar_python


@dataclass
class ResultadoAnalise:
    """Tudo o que o relatório precisa, já calculado."""

    repositorio: str
    linguagem: str
    debitos: list[DebitoPriorizado] = field(default_factory=list)
    falsos_positivos: list[dict[str, str]] = field(default_factory=list)
    avisos_ferramentas: list[str] = field(default_factory=list)
    mapa_alcancabilidade: dict[str, bool] = field(default_factory=dict)
    total_achados_brutos: int = 0
    total_grupos: int = 0
    env_real_commitado: bool = False


def detectar_linguagem(raiz: Path) -> str:
    """Item 2 obrigatório do enunciado: detectar a linguagem do repositório."""

    tem_python = any(raiz.rglob("*.py")) or (raiz / "requirements.txt").exists()
    tem_php = (raiz / "composer.json").exists() or any(raiz.rglob("*.php"))

    if tem_python and not tem_php:
        return "python"
    if tem_php and not tem_python:
        return "php"
    if tem_python and tem_php:
        return "python"  # o alvo principal do desafio
    return "desconhecida"


def _tem_env_real(raiz: Path) -> bool:
    """Pergunta 5 do questionário, respondida por verificação e não por crença."""

    for caminho in raiz.rglob(".env*"):
        if caminho.name == ".env.example" or not caminho.is_file():
            continue
        try:
            conteudo = caminho.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # .env com pelo menos uma variável preenchida
        for linha in conteudo.splitlines():
            if "=" in linha and linha.split("=", 1)[1].strip():
                return True
    return False


def analisar(raiz: Path, incluir_semgrep: bool = False) -> ResultadoAnalise:
    raiz = raiz.resolve()
    resultado = ResultadoAnalise(repositorio=raiz.name, linguagem=detectar_linguagem(raiz))

    if resultado.linguagem != "python":
        resultado.avisos_ferramentas.append(
            f"linguagem detectada: {resultado.linguagem} — "
            "a análise PHP está fora do escopo desta entrega; "
            "nenhum achado foi produzido (isto NÃO significa ausência de débitos)"
        )
        return resultado

    achados, avisos = coletar_python(raiz, incluir_semgrep=incluir_semgrep)
    resultado.avisos_ferramentas = avisos
    resultado.total_achados_brutos = len(achados)

    grupos = deduplicate_findings(achados)
    resultado.total_grupos = len(grupos)

    classificados = classify_groups(grupos)
    pontuados = score_groups(classificados)

    resultado.mapa_alcancabilidade = mapear_alcancabilidade(raiz)
    resultado.env_real_commitado = _tem_env_real(raiz)
    rotas = arquivos_com_rota(raiz)

    debitos: list[DebitoPriorizado] = []

    for classificado, tecnico in zip(classificados, pontuados):
        finding = classificado.group.representative_finding
        arquivo = finding.file_path or ""
        conceito = classificado.concept

        justificativa = eh_falso_positivo(conceito, arquivo, finding.line)
        if justificativa:
            resultado.falsos_positivos.append(
                {
                    "conceito": conceito,
                    "local": f"{arquivo}:{finding.line}",
                    "ferramentas": ", ".join(classificado.group.source_tools),
                    "justificativa": justificativa,
                }
            )
            continue

        ctx: ContextoNegocio = avaliar(
            conceito=conceito,
            arquivo=arquivo,
            descricao=finding.description,
            metric_value=finding.metric_value,
            mapa_alcancabilidade=resultado.mapa_alcancabilidade,
            rotas=rotas,
        )

        pontuacao, memorial = pontuar(tecnico.score_priority, ctx)

        debitos.append(
            DebitoPriorizado(
                id="",
                conceito=conceito,
                categoria=CATEGORIA_PT.get(classificado.category, "Design"),
                nome=_nome_legivel(conceito, finding.description),
                descricao=finding.description,
                arquivo=arquivo,
                linha=finding.line,
                impacto=ctx.impacto,
                risco=calcular_risco(ctx, tecnico.score_priority),
                esforco_sp=ctx.esforco_sp,
                valor=VALOR_POR_CATEGORIA.get(classificado.category, "Qualidade"),
                prioridade=faixa(pontuacao),
                pontuacao=pontuacao,
                memorial=memorial,
                contexto=ctx,
                ferramentas=tuple(classificado.group.source_tools),
                prioridade_tecnica=tecnico.score_priority,
            )
        )

    resultado.debitos = ordenar_e_numerar(debitos)
    return resultado


NOMES_LEGIVEIS = {
    "dynamic_sql": "SQL montado por concatenação de string",
    "hardcoded_secret": "Segredo hardcoded no código-fonte",
    "weak_password_hash": "Hash inseguro (MD5/SHA-1) em dado sensível",
    "missing_timeout": "Chamada HTTP sem timeout",
    "swallowed_exception": "Exceção engolida silenciosamente",
    "broad_exception": "Captura de exceção genérica demais",
    "cyclomatic_complexity": "Função com complexidade ciclomática alta",
    "unused_variable": "Variável calculada e nunca usada",
    "todo_comment": "TODO deixado no código",
    "excessive_branches": "Excesso de ramificações na função",
    "excessive_returns": "Excesso de pontos de retorno",
    "excessive_locals": "Excesso de variáveis locais",
    "inconsistent_returns": "Retornos inconsistentes",
    "shadowed_builtin": "Nome sombreia um builtin do Python",
    "unnecessary_else_after_return": "else desnecessário após return",
    "import_error": "Import não resolvido no ambiente de análise",
}


def _nome_legivel(conceito: str, descricao: str) -> str:
    if conceito in NOMES_LEGIVEIS:
        return NOMES_LEGIVEIS[conceito]
    return descricao[:70]
