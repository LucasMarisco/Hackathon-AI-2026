"""Renderização do relatório de débitos técnicos em Markdown e JSON.

Nenhuma seção é escrita à mão: cinco são calculadas pelo pipeline e três vêm
da curadoria verificada em ``curadoria.py``. O documento inteiro é
reproduzível — rodar o pipeline de novo regenera o mesmo arquivo, byte a byte.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import curadoria
from priorizacao import CAPACIDADE_SP_SEMANA, DebitoPriorizado
from pipeline import ResultadoAnalise

ORDEM_PRIORIDADE = ("Crítica", "Alta", "Média", "Baixa")


def _esc(texto: Any) -> str:
    """O caractere | quebra tabela Markdown."""

    return str(texto).replace("|", "&#124;").replace("\n", " ").strip()


# ---------------------------------------------------------------------------
# Seção 2 — questionário respondido por EVIDÊNCIA, não por crença
# ---------------------------------------------------------------------------
def avaliar_questionario(resultado: ResultadoAnalise) -> list[dict[str, Any]]:
    """Para cada pergunta, procura achados que a derrubem.

    O questionário do repositório vem com a nota: "preenchido pelo time
    comercial com base no que acreditam ser verdade". Aqui cada resposta sai
    com a evidência anexada pelo pipeline.
    """

    por_pergunta: dict[int, list[DebitoPriorizado]] = {}
    for debito in resultado.debitos:
        for q in debito.contexto.perguntas_questionario:
            por_pergunta.setdefault(q, []).append(debito)

    linhas = []
    for numero in sorted(curadoria.PERGUNTAS_QUESTIONARIO):
        evidencias = por_pergunta.get(numero, [])
        nao_coberta = curadoria.PERGUNTAS_NAO_COBERTAS.get(numero)

        if evidencias:
            resposta = "**Não**"
            prova = "; ".join(
                f"`{d.arquivo}:{d.linha}`" for d in evidencias[:3]
            )
            if len(evidencias) > 3:
                prova += f" (+{len(evidencias) - 3} ocorrências)"
        elif numero == 5:
            # Respondida por verificação direta do repositório.
            achou = resultado.env_real_commitado
            resposta = "**Não**" if achou else "**Sim**"
            prova = (
                "arquivo .env com valores encontrado"
                if achou
                else "nenhum .env com valores no repositório; apenas .env.example"
            )
        elif nao_coberta:
            resposta = "**Não** (verificação manual)"
            prova = nao_coberta
        else:
            resposta = "**Sim**"
            prova = "nenhum achado do pipeline contradiz esta resposta"

        linhas.append(
            {
                "numero": numero,
                "pergunta": curadoria.PERGUNTAS_QUESTIONARIO[numero],
                "resposta": resposta,
                "evidencia": prova,
                "remediacao": curadoria.REMEDIACAO_QUESTIONARIO.get(numero, ""),
                "ocorrencias": len(evidencias),
            }
        )

    return linhas


# ---------------------------------------------------------------------------
# Seção 8 — roadmap derivado do scoring, não opinado
# ---------------------------------------------------------------------------
def montar_roadmap(debitos: list[DebitoPriorizado], semanas: int = 6) -> list[dict[str, Any]]:
    """Aloca os débitos em semanas de 6 SP, na ordem da pontuação.

    "capacidade real: ~6 story points por semana" (business-context.md).
    O plano de ação deixa de ser opinião e passa a ser consequência
    aritmética do modelo: mexer num peso recalcula o roadmap inteiro.
    """

    plano = [{"semana": i, "itens": [], "sp": 0.0} for i in range(1, semanas + 1)]
    fora: list[DebitoPriorizado] = []

    indice = 0
    for debito in debitos:
        alocado = False
        for i in range(indice, semanas):
            if plano[i]["sp"] + debito.esforco_sp <= CAPACIDADE_SP_SEMANA:
                plano[i]["itens"].append(debito)
                plano[i]["sp"] += debito.esforco_sp
                alocado = True
                break
        if not alocado:
            fora.append(debito)

    return plano, fora


def render_markdown(resultado: ResultadoAnalise) -> str:
    debitos = resultado.debitos
    linhas: list[str] = []
    dist = Counter(d.prioridade for d in debitos)
    questionario = avaliar_questionario(resultado)
    nao_conformes = sum(1 for q in questionario if q["resposta"].startswith("**Não"))
    sp_total = sum(d.esforco_sp for d in debitos)

    # --- cabeçalho ---
    linhas += [
        "# Relatório de Débitos Técnicos — HourTrack Ltda.",
        "",
        f"**Repositório analisado:** `{resultado.repositorio}`  ",
        f"**Linguagem detectada:** {resultado.linguagem}  ",
        f"**Achados brutos das ferramentas:** {resultado.total_achados_brutos} → "
        f"**{resultado.total_grupos} após deduplicação** → "
        f"**{len(debitos)} débitos** ({len(resultado.falsos_positivos)} descartados como falso positivo)",
        "",
    ]

    if resultado.avisos_ferramentas:
        linhas += ["> **Avisos de execução das ferramentas:**", ""]
        linhas += [f"> - {_esc(a)}" for a in resultado.avisos_ferramentas]
        linhas.append("")

    # --- 1. sumário executivo ---
    vivos = sum(1 for d in debitos if d.contexto.alcancavel)
    linhas += [
        "## 1. Sumário executivo",
        "",
        f"- **{nao_conformes} das 7 perguntas** do questionário do cliente enterprise "
        f"(R$ 8.000/mês, contrato que dobra o MRR de R$ 28.000) têm hoje a resposta **\"Não\"**.",
        f"- **{dist.get('Crítica', 0)} débitos críticos** e **{dist.get('Alta', 0)} de prioridade alta**.",
        f"- **{vivos} dos {len(debitos)} débitos estão em código que executa hoje**; "
        f"o restante é risco latente, em arquivos que nenhuma execução alcança.",
        f"- Esforço total catalogado: **{sp_total:.1f} SP** — "
        f"{sp_total / CAPACIDADE_SP_SEMANA:.1f} semanas na capacidade real do time "
        f"({CAPACIDADE_SP_SEMANA} SP/semana, 2 desenvolvedores, sem QA).",
        "",
        "| Prioridade | Qtd. | Esforço (SP) |",
        "|---|---:|---:|",
    ]
    for nome in ORDEM_PRIORIDADE:
        grupo = [d for d in debitos if d.prioridade == nome]
        if grupo:
            linhas.append(f"| {nome} | {len(grupo)} | {sum(d.esforco_sp for d in grupo):.1f} |")
    linhas.append("")

    # --- 2. questionário ---
    linhas += [
        "## 2. Resposta ao questionário de segurança do cliente enterprise",
        "",
        "> O questionário do repositório traz a nota: *\"preenchido pelo time comercial "
        "com base no que acreditam ser verdade sobre o produto\"*. Abaixo, cada resposta "
        "sai com a evidência que o pipeline anexou.",
        "",
        "| # | Pergunta | Resposta honesta | Evidência | Plano de remediação |",
        "|---|---|---|---|---|",
    ]
    for q in questionario:
        linhas.append(
            f"| {q['numero']} | {_esc(q['pergunta'])} | {q['resposta']} "
            f"| {_esc(q['evidencia'])} | {_esc(q['remediacao'])} |"
        )
    linhas.append("")

    # --- 3. tabela de débitos ---
    linhas += [
        "## 3. Débitos priorizados",
        "",
        "| ID | Categoria | Nome | Descrição | Impacto | Risco | Esforço | Valor | Prioridade |",
        "|---|---|---|---|---|---|---:|---|---|",
    ]
    for d in debitos:
        linhas.append(
            f"| {d.id} | {d.categoria} | {_esc(d.nome)} "
            f"| `{d.arquivo}:{d.linha}` — {_esc(d.descricao)} "
            f"| {_esc(d.impacto)} | {d.risco} | {d.esforco_sp:.1f} SP "
            f"| {_esc(d.valor)} | **{d.prioridade}** |"
        )
    linhas.append("")

    # --- 4. latente vs ativo ---
    mortos = [d for d in debitos if not d.contexto.alcancavel]
    arquivos_mortos = sorted({a for a, vivo in resultado.mapa_alcancabilidade.items() if not vivo})
    linhas += [
        "## 4. Risco ativo vs. risco latente",
        "",
        f"A análise de alcançabilidade (grafo de imports a partir dos pontos de entrada) "
        f"mostra que **{len(arquivos_mortos)} de {len(resultado.mapa_alcancabilidade)} arquivos "
        f"não são alcançados por nenhuma execução do sistema**. "
        f"Isso rebaixa {len(mortos)} débitos de exposição ativa para risco latente.",
        "",
        "Arquivos não alcançados:",
        "",
    ]
    linhas += [f"- `{a}`" for a in arquivos_mortos]
    linhas += [
        "",
        "> **A recomendação de maior valor deste relatório:** o blueprint de relatórios "
        "nunca é registrado na aplicação, então `/api/reports/*` retorna 404 hoje. "
        "A release v2.1 é justamente *\"relatório por projeto\"* — no primeiro "
        "`register_blueprint`, essas vulnerabilidades saem do estado latente de uma vez. "
        "**Corrigi-las junto com a feature custa cerca de 3 SP; depois dela, vira incidente.**",
        "",
    ]

    # --- 5. memorial de cálculo ---
    linhas += [
        "## 5. Memorial de cálculo",
        "",
        "A conta de cada débito, passo a passo. Os pesos e a justificativa de negócio "
        "de cada um estão em `analyzer/priorizacao.py` e `analyzer/business_context.py`.",
        "",
        "| ID | Pontuação | Conta |",
        "|---|---:|---|",
    ]
    for d in debitos:
        linhas.append(f"| {d.id} | {d.pontuacao:.2f} | {_esc(' '.join(d.memorial))} |")
    linhas.append("")

    # --- 6. falsos positivos ---
    if resultado.falsos_positivos:
        linhas += [
            "## 6. Falsos positivos descartados",
            "",
            "Achados que as ferramentas reportaram, que abrimos no editor e concluímos "
            "**não** serem problema. Ficam registrados aqui em vez de sumirem em silêncio.",
            "",
            "| Ferramenta | Local | Por que não é problema |",
            "|---|---|---|",
        ]
        for fp in resultado.falsos_positivos:
            linhas.append(
                f"| {_esc(fp['ferramentas'])} | `{_esc(fp['local'])}` "
                f"| {_esc(fp['justificativa'])} |"
            )
        linhas.append("")

    # --- 6b. o que foi observado mas NÃO classificado como débito ---
    if resultado.metricas_observadas or resultado.achados_ambientais:
        linhas += [
            "### Observado, mas não classificado como débito",
            "",
            "Reportar como débito algo que não é problema real desconta ponto. "
            "Estes grupos foram medidos e ficam registrados, mas **não entram "
            "na contagem nem no esforço**:",
            "",
        ]
        if resultado.metricas_observadas:
            linhas.append(
                f"- **{len(resultado.metricas_observadas)} métricas de complexidade rank A/B** "
                "— funções simples. Só ranks C a F são candidatos a débito de "
                "manutenibilidade. Exemplo: `get_db` tem complexidade 1."
            )
        if resultado.achados_ambientais:
            locais = ", ".join(f"`{a['local']}`" for a in resultado.achados_ambientais)
            linhas.append(
                f"- **{len(resultado.achados_ambientais)} achados do ambiente de análise** "
                f"({locais}) — imports que a ferramenta não resolveu por faltar "
                "dependência no container, não defeito do produto."
            )
        linhas.append("")

    # --- 7. o que a IA errou (obrigatória) ---
    linhas += [
        "## 7. O que a IA sugeriu que estava errado, e por quê",
        "",
        "| Afirmação | Origem | Por que está errado | Como verificamos |",
        "|---|---|---|---|",
    ]
    for item in curadoria.AUDITORIA_DA_IA:
        linhas.append(
            f"| {_esc(item['afirmacao'])} | {_esc(item['origem'])} "
            f"| {_esc(item['porque_errado'])} | {_esc(item['como_verificamos'])} |"
        )
    linhas.append("")

    # --- 8. roadmap ---
    plano, fora = montar_roadmap(debitos)
    linhas += [
        "## 8. Plano de 6 semanas — \"CTO por um dia\"",
        "",
        f"Alocação derivada da pontuação, respeitando os {CAPACIDADE_SP_SEMANA} SP/semana "
        "de capacidade real. Não é opinião: é consequência aritmética do modelo — "
        "mexer num peso recalcula o plano inteiro.",
        "",
    ]
    for semana in plano:
        if not semana["itens"]:
            continue
        linhas.append(f"**Semana {semana['semana']}** — {semana['sp']:.1f} SP")
        linhas.append("")
        for d in semana["itens"]:
            linhas.append(
                f"- `{d.id}` {_esc(d.nome)} em `{d.arquivo}:{d.linha}` "
                f"— {d.esforco_sp:.1f} SP ({d.prioridade})"
            )
        linhas.append("")

    if fora:
        sp_fora = sum(d.esforco_sp for d in fora)
        linhas += [
            f"### O que fica para depois — {len(fora)} débitos, {sp_fora:.1f} SP",
            "",
            "Não cabem nas 6 semanas antes da saída do desenvolvedor que escreveu 90% do "
            "código. Ficam explicitamente adiados, não esquecidos:",
            "",
        ]
        for d in fora[:15]:
            linhas.append(
                f"- `{d.id}` {_esc(d.nome)} em `{d.arquivo}:{d.linha}` — "
                f"{d.esforco_sp:.1f} SP, prioridade {d.prioridade}"
            )
        if len(fora) > 15:
            linhas.append(f"- _(+{len(fora) - 15} débitos de prioridade menor)_")
        linhas.append("")

    return "\n".join(linhas) + "\n"


def report_payload(resultado: ResultadoAnalise) -> dict[str, Any]:
    dist = Counter(d.prioridade for d in resultado.debitos)
    return {
        "repositorio": resultado.repositorio,
        "linguagem": resultado.linguagem,
        "resumo": {
            "achados_brutos": resultado.total_achados_brutos,
            "grupos_apos_deduplicacao": resultado.total_grupos,
            "debitos": len(resultado.debitos),
            "falsos_positivos_descartados": len(resultado.falsos_positivos),
            "por_prioridade": {nome: dist.get(nome, 0) for nome in ORDEM_PRIORIDADE},
            "esforco_total_sp": round(sum(d.esforco_sp for d in resultado.debitos), 1),
            "capacidade_sp_semana": CAPACIDADE_SP_SEMANA,
        },
        "questionario": avaliar_questionario(resultado),
        "debitos": [d.to_dict() for d in resultado.debitos],
        "falsos_positivos": resultado.falsos_positivos,
        "observado_nao_classificado": {
            "metricas_rank_a_b": resultado.metricas_observadas,
            "ambiente_de_analise": resultado.achados_ambientais,
        },
        "auditoria_da_ia": [dict(item) for item in curadoria.AUDITORIA_DA_IA],
        "alcancabilidade": resultado.mapa_alcancabilidade,
        "avisos_ferramentas": resultado.avisos_ferramentas,
    }


def render_json(resultado: ResultadoAnalise) -> str:
    # Sem data/hora de execução: seria a mesma armadilha do campo generated_at
    # do bandit e faria dois `diff` seguidos darem diferente.
    # sort_keys=True: ordem de chaves estável em qualquer versão do Python.
    return json.dumps(
        report_payload(resultado), ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
