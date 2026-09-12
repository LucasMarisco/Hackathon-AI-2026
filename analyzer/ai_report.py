"""Gemini interpretation layer for the deterministic analyzer report."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from google import genai
except ImportError:  # Keep deterministic pipeline usable without the optional SDK.
    genai = None

try:
    from dotenv import load_dotenv
except ImportError:  # Keep local execution usable before optional dependencies install.
    load_dotenv = None


MODEL_NAME = "gemini-3.8-flash"


def generate_ai_report(report_path: Path, output_path: Path) -> Path:
    """Interpret an existing deterministic report and save a Markdown report.

    Only the parsed report JSON is sent to Gemini. The source repositories and
    detector JSONs never enter the prompt.
    """

    report = _load_report(report_path)
    _load_local_environment()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured; deterministic reports were preserved."
        )
    if genai is None:
        raise RuntimeError(
            "google-genai is not installed; deterministic reports were preserved."
        )

    prompt = _build_prompt(report)
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    text = getattr(response, "text", None)
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("Gemini returned an empty response; deterministic reports were preserved.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return output_path


def _load_report(report_path: Path) -> dict[str, Any]:
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read report JSON '{report_path}': {exc}") from exc
    if not isinstance(report, dict) or not isinstance(report.get("summary"), dict):
        raise ValueError("report.json must contain an object field named 'summary'.")
    if not isinstance(report.get("results"), list):
        raise ValueError("report.json must contain an array field named 'results'.")
    return report


def _load_local_environment() -> None:
    if load_dotenv is not None:
        load_dotenv()


def _build_prompt(report: dict[str, Any]) -> str:
    report_data = json.dumps(report, ensure_ascii=False, indent=2)
    return f"""Você é um analista assistente do Radar de Débitos Técnicos da HourTrack Ltda.

Contexto empresarial:
- SaaS B2B de controle de horas faturáveis; 47 agências, aproximadamente 180 usuários e R$28 mil de MRR.
- Equipe de 8 pessoas, com 2 desenvolvedores full-stack; o principal desenvolvedor escreveu cerca de 90% do código e sai em 6 semanas.
- Release v2.1 em 14 dias e questionário de segurança de cliente enterprise em 30 dias.
- O cliente enterprise tem mais de 200 usuários e representa R$8 mil/mês; 3 clientes representam 60% da receita.
- Não existe staging, alterações são feitas diretamente em produção e SQLite está versionado no repositório.

Objetivo: apresentar os resultados já produzidos pelo Radar de Débitos Técnicos para uma apresentação de hackathon.

Regras obrigatórias:
- O JSON abaixo é a única fonte de verdade. Não crie findings e não invente fatos, arquivos, linhas, causas ou impactos comprovados.
- Preserve literalmente category, classification_priority, score, score_priority e score_priority_mapped.
- Não recalcule score nem altere prioridades. score_priority_mapped já é a prioridade final legível: high, medium ou low.
- Nenhum finding está confirmado: todos vêm de análise estática, sem execução do sistema. Use linguagem como "pode indicar" e "deve ser validado".
- Ferramentas estáticas podem gerar falsos positivos. Não execute o sistema e não proponha novas detecções.
- Recomendações são interpretações dos dados existentes, não decisões do motor determinístico.

Escreva em português profissional, claro e específico, usando exatamente estes títulos:
# Radar de Débitos Técnicos — Análise Assistida por IA
## 1. Resumo executivo
## 2. Principais riscos
## 3. Segurança
## 4. Confiabilidade e disponibilidade
## 5. Manutenibilidade e qualidade
## 6. Priorização
Inclua uma tabela com ID/conceito, categoria, score, prioridade e status de validação. Inclua ferramentas quando disponíveis em factors.source_tools.
## 7. Plano de ação
## 8. O que a IA sugeriu que estava errado, e por quê
Explique que a IA recebeu resultados de ferramentas estáticas e do motor determinístico e que não corrigiu nem criou findings.
## 9. Limitações
Inclua as limitações de validação, falsos positivos, problemas ambientais do PHPStan, motor determinístico e ausência de execução do sistema.

Dados agregados do report.json:
{report_data}
"""