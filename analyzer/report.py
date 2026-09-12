"""Markdown and JSON rendering for the analyzer pipeline."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from scoring import ScoredFindingGroup, score_priority_label


CONCEPT_GUIDANCE: dict[str, dict[str, str]] = {
    "dynamic_sql": {
        "description": "Construção de consultas SQL com dados dinâmicos em vez de parâmetros seguros.",
        "impact": "Pode permitir alteração indevida da consulta e exposição ou alteração de dados.",
        "recommendation": "Validar a origem dos valores e usar consultas parametrizadas ou APIs de composição segura.",
    },
    "hardcoded_secret": {
        "description": "Uma senha, credencial ou segredo aparece diretamente no código.",
        "impact": "O segredo pode ser exposto a qualquer pessoa com acesso ao repositório ou aos artefatos.",
        "recommendation": "Remover o valor do código, revogar o segredo quando aplicável e usar configuração segura.",
    },
    "weak_password_hash": {
        "description": "Uso de algoritmo de hash inadequado para proteger senhas.",
        "impact": "Senhas podem ficar mais suscetíveis a recuperação caso os dados armazenados sejam expostos.",
        "recommendation": "Validar o fluxo e migrar para um algoritmo de hash de senha resistente a ataques de força bruta.",
    },
    "missing_timeout": {
        "description": "Uma chamada externa não define limite explícito de tempo de espera.",
        "impact": "A operação pode ficar bloqueada e consumir recursos, afetando a disponibilidade do serviço.",
        "recommendation": "Definir timeouts adequados e tratar timeout, retry e falhas de forma controlada.",
    },
    "broad_exception": {
        "description": "O código captura uma classe ampla de exceções.",
        "impact": "Erros diferentes podem ser tratados da mesma forma e dificultar diagnóstico ou recuperação.",
        "recommendation": "Capturar exceções específicas e registrar ou propagar cada falha conforme o caso.",
    },
    "swallowed_exception": {
        "description": "Uma exceção é capturada sem tratamento ou sinalização suficiente.",
        "impact": "Falhas podem desaparecer silenciosamente e produzir comportamento incorreto difícil de investigar.",
        "recommendation": "Tratar a condição explicitamente, registrar contexto útil e preservar a sinalização do erro.",
    },
    "inconsistent_returns": {
        "description": "Um fluxo de função retorna valores diferentes ou não retorna em todos os caminhos.",
        "impact": "Chamadores podem receber resultados inesperados e precisar lidar com estados implícitos.",
        "recommendation": "Definir um contrato de retorno único e cobrir todos os caminhos de execução.",
    },
    "import_error": {
        "description": "A ferramenta não conseguiu resolver um import durante a análise.",
        "impact": "Pode indicar dependência ausente ou apenas uma diferença entre o ambiente da ferramenta e o ambiente de execução.",
        "recommendation": "Verificar o ambiente e as dependências antes de tratar o resultado como defeito confirmado.",
    },
    "cyclomatic_complexity": {
        "description": "A função ou método possui muitos caminhos condicionais de execução.",
        "impact": "Aumenta o esforço de entendimento, teste e manutenção do comportamento.",
        "recommendation": "Validar os caminhos e considerar decomposição em funções menores e coesas.",
    },
    "excessive_branches": {
        "description": "Uma função possui quantidade elevada de ramificações condicionais.",
        "impact": "Torna o fluxo mais difícil de testar e aumenta o risco de comportamento não coberto.",
        "recommendation": "Simplificar o fluxo ou separar responsabilidades em unidades menores.",
    },
    "excessive_returns": {
        "description": "Uma função possui muitos pontos de retorno.",
        "impact": "Pode dificultar a leitura do fluxo e a verificação de invariantes da função.",
        "recommendation": "Revisar o fluxo e reduzir saídas dispersas quando isso melhorar a clareza.",
    },
    "excessive_locals": {
        "description": "Uma função utiliza muitas variáveis locais.",
        "impact": "Indica concentração de responsabilidades e aumenta a carga cognitiva para manutenção.",
        "recommendation": "Revisar responsabilidades e extrair operações coesas quando apropriado.",
    },
    "unused_variable": {
        "description": "Uma variável atribuída não é utilizada posteriormente.",
        "impact": "Pode indicar lógica residual, erro de implementação ou intenção não expressa.",
        "recommendation": "Confirmar a intenção e remover a variável ou completar o uso necessário.",
    },
    "shadowed_builtin": {
        "description": "Um nome local sobrescreve o nome de uma função ou tipo embutido da linguagem.",
        "impact": "Pode confundir leitores e impedir o uso esperado da operação embutida naquele escopo.",
        "recommendation": "Renomear o identificador para preservar a clareza e o acesso à operação original.",
    },
    "unnecessary_else_after_return": {
        "description": "Um bloco else aparece depois de um caminho que já retorna.",
        "impact": "Adiciona aninhamento desnecessário e torna o fluxo mais difícil de ler.",
        "recommendation": "Remover o else quando equivalente e manter o caminho principal mais direto.",
    },
    "todo_comment": {
        "description": "Existe um comentário TODO indicando trabalho pendente no código.",
        "impact": "A pendência pode permanecer sem responsável, prazo ou decisão explícita.",
        "recommendation": "Avaliar a pendência, convertê-la em tarefa rastreável ou removê-la se não for mais necessária.",
    },
}


def _guidance_for(concept: str) -> dict[str, str]:
    return CONCEPT_GUIDANCE.get(
        concept,
        {
            "description": "Resultado técnico identificado por uma ferramenta estática.",
            "impact": "O impacto depende da validação do contexto indicado no grupo.",
            "recommendation": "Revisar a ocorrência e confirmar a ação adequada antes de alterar o código.",
        },
    )


def _result_payload(result: ScoredFindingGroup) -> dict[str, Any]:
    payload = result.to_dict()
    payload.update(_guidance_for(result.concept))
    return payload


def report_payload(results: list[ScoredFindingGroup]) -> dict[str, Any]:
    distribution = Counter(
        score_priority_label(result.score_priority) for result in results
    )
    return {
        "summary": {
            "scored_groups": len(results),
            "high": distribution["high"],
            "medium": distribution["medium"],
            "low": distribution["low"],
            "without_priority": 0,
        },
        "results": [_result_payload(result) for result in results],
    }


def render_json(results: list[ScoredFindingGroup]) -> str:
    return json.dumps(report_payload(results), ensure_ascii=False, indent=2) + "\n"


def render_markdown(results: list[ScoredFindingGroup]) -> str:
    payload = report_payload(results)
    summary = payload["summary"]
    lines = [
        "# Radar de Débitos Técnicos — Relatório Determinístico",
        "",
        "## Resumo executivo",
        "",
        f"O pipeline consolidou {summary['scored_groups']} grupos de débito a partir das evidências dos analisadores. A distribuição atual é **{summary['high']} high**, **{summary['medium']} medium** e **{summary['low']} low**, sem grupos sem prioridade.",
        "",
        "Cada linha detalhada representa um **grupo de débito**, isto é, uma ocorrência consolidada por conceito e localização. As evidências retidas em `evidence_count` e `source_tools` mostram os resultados das ferramentas que sustentam o grupo; elas não são novos débitos.",
        "",
        "## Principais riscos",
        "",
        "Os itens high devem ser investigados primeiro porque combinam maior prioridade quantitativa com potencial de afetar dados, disponibilidade ou compromissos de clientes. A prioridade é a produzida pelo motor determinístico; as descrições abaixo apenas explicam o significado geral de cada conceito.",
        "",
        "## Principais problemas",
        "",
        "| Conceito | Descrição | Impacto potencial | Prioridade | Score | Ferramentas |",
        "|---|---|---|---|---:|---|",
    ]
    by_concept: dict[str, list[ScoredFindingGroup]] = {}
    for result in results:
        by_concept.setdefault(result.concept, []).append(result)
    for concept, concept_results in sorted(
        by_concept.items(),
        key=lambda item: (-max(item_result.score for item_result in item[1]), item[0]),
    ):
        representative = max(concept_results, key=lambda item: item.score)
        guidance = _guidance_for(concept)
        tools = sorted(
            {
                tool
                for item in concept_results
                for tool in item.factors.get("source_tools", [])
            }
        )
        lines.append(
            f"| {concept} | {guidance['description']} | {guidance['impact']} | {score_priority_label(representative.score_priority)} | {representative.score:.2f} | {', '.join(tools) or 'não informado'} |"
        )
    lines.extend(
        [
            "",
            "## Plano de ação",
            "",
            "1. Investigar primeiro os grupos `high`, começando por segurança e disponibilidade, antes da release e da revisão de segurança do cliente.",
            "2. Validar em seguida os grupos `medium`, priorizando aqueles que podem afetar estabilidade ou manutenção do fluxo de produção.",
            "3. Organizar os grupos `low` em tarefas de manutenção, começando por itens recorrentes ou concentrados no mesmo módulo.",
            "4. Para cada grupo, confirmar a evidência, definir responsável e registrar a correção sem confundir ferramentas corroborantes com novos débitos.",
            "",
            "## Origem das recomendações",
            "",
            "As recomendações deste relatório são explicações determinísticas baseadas no conceito e nos resultados já produzidos pelas ferramentas. Elas não alteram categoria, prioridade, score ou quantidade de grupos. Uma camada opcional de IA generativa pode interpretar o `report.json`, mas não é necessária para gerar este relatório nem é fonte de verdade.",
            "",
            "## Limitações",
            "",
            "- A análise é estática e não executa o sistema.",
            "- Ferramentas estáticas podem produzir falsos positivos; cada evidência deve ser revisada no contexto.",
            "- O score e as prioridades são definidos pelo motor determinístico e não são recalculados na apresentação.",
            "- Resultados ambientais, como imports não resolvidos, podem refletir configuração do ambiente de análise.",
            "",
            "## Grupos e evidências",
            "",
            "A tabela abaixo mantém a rastreabilidade completa. `evidence_count` é a quantidade de evidências retidas no grupo e `source_tools` lista as ferramentas correspondentes.",
            "",
            "| Grupo | Conceito | Categoria | Score | Prioridade V1 | Prioridade scoring | Evidências | Ferramentas |",
            "|---|---|---|---:|---|---|---:|---|",
        ]
    )
    for result in results:
        factors = result.factors
        lines.append(
            "| {group_id} | {concept} | {category} | {score:.2f} | {v1} | {scoring} | {evidence_count} | {tools} |".format(
                group_id=result.group_id,
                concept=result.concept,
                category=result.category,
                score=result.score,
                v1=result.classification_priority or "sem prioridade",
                scoring=score_priority_label(result.score_priority),
                evidence_count=factors.get("evidence_count", 0),
                tools=", ".join(factors.get("source_tools", [])) or "não informado",
            )
        )
    lines.extend(
        [
            "",
            "## Distribuição",
            "",
            f"- high: {summary['high']}",
            f"- medium: {summary['medium']}",
            f"- low: {summary['low']}",
            f"- sem prioridade: {summary['without_priority']}",
            "",
        ]
    )
    return "\n".join(lines)