"""Radar de Débitos Técnicos — entry point do pipeline.

Uso:
    python analyzer/main.py <caminho-do-repositorio> [--out PASTA]

O pipeline, ponta a ponta:

    1. coleta      executa bandit/radon/pylint via subprocess   tool_runner.py
    2. normaliza   converte a saída em Finding unificado        detectors/python.py
    3. deduplica   agrupa o mesmo problema visto por N tools    deduplication.py
    4. classifica  conceito -> categoria (política V1)          classification.py
    5. pontua      score técnico determinístico                 scoring.py
    6. contextualiza  alcançabilidade + contexto de negócio     reachability.py, business_context.py
    7. prioriza    fórmula justificada pelo business-context    priorizacao.py
    8. renderiza   relatório em Markdown e JSON                 report.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline import analisar
from report import render_json, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analisa um repositório e gera um relatório priorizado de débitos técnicos.",
    )
    parser.add_argument("repositorio", type=Path, help="caminho do repositório a analisar")
    parser.add_argument(
        "--out", type=Path, default=Path("analyzer/output"),
        help="pasta de saída do relatório (padrão: analyzer/output)",
    )
    parser.add_argument(
        "--semgrep", action="store_true",
        help="inclui semgrep na coleta (exige rede para baixar as regras)",
    )
    parser.add_argument(
        "--ai-report", action="store_true",
        help="gera, além do relatório determinístico, uma leitura em linguagem natural via Gemini",
    )
    args = parser.parse_args()

    if not args.repositorio.is_dir():
        print(f"erro: repositório não encontrado: {args.repositorio}", file=sys.stderr)
        return 1

    try:
        resultado = analisar(args.repositorio, incluir_semgrep=args.semgrep)
    except Exception as erro:  # noqa: BLE001 - o avaliador não pode receber traceback cru
        print(f"erro ao analisar o repositório: {erro}", file=sys.stderr)
        return 1

    # Avisos vão para stderr: separados do resultado, e nunca silenciosos.
    for aviso in resultado.avisos_ferramentas:
        print(f"aviso: {aviso}", file=sys.stderr)

    args.out.mkdir(parents=True, exist_ok=True)
    caminho_md = args.out / "report.md"
    caminho_json = args.out / "report.json"
    caminho_md.write_text(render_markdown(resultado), encoding="utf-8")
    caminho_json.write_text(render_json(resultado), encoding="utf-8")

    print(f"repositório      {resultado.repositorio} ({resultado.linguagem})")
    print(f"achados brutos   {resultado.total_achados_brutos}")
    print(f"após dedup       {resultado.total_grupos}")
    print(f"falsos positivos {len(resultado.falsos_positivos)} descartados")
    print(f"débitos          {len(resultado.debitos)}")
    print(f"relatório        {caminho_md}")
    print(f"json             {caminho_json}")

    if args.ai_report:
        try:
            from ai_report import generate_ai_report

            destino = generate_ai_report(caminho_json, args.out / "ai_report.md")
            print(f"leitura por IA   {destino}")
        except Exception as erro:  # noqa: BLE001
            print(f"aviso: leitura por IA indisponível: {erro}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
