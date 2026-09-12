"""Execução das ferramentas de análise estática sobre um repositório.

Esta camada é a que faltava entre o repositório-alvo e os parsers já
existentes em ``detectors/python.py``: ela invoca cada ferramenta via
``subprocess``, carrega o JSON e entrega para o parser correspondente.
Nenhum parser é reescrito.

Três garantias que o enunciado exige e que este módulo implementa:

1. ``subprocess`` de verdade — o pipeline recebe o path do repositório, não
   uma pasta de JSONs pré-gerados.
2. Falha nunca é silenciosa. Ferramenta ausente, saída vazia ou JSON inválido
   viram um aviso explícito na lista devolvida, jamais "zero problemas".
3. Caminhos relativos ao repositório. As ferramentas devolvem caminho
   absoluto; mantê-lo faria o relatório mudar de máquina para máquina e
   quebraria o determinismo.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from detectors.python import parse_bandit, parse_pylint, parse_radon, parse_semgrep
from models import Finding

# Tempo máximo por ferramenta. O pipeline reporta `missing_timeout` como
# débito; seria incoerente chamar subprocess sem timeout.
TIMEOUT_SEGUNDOS = 300

# Pastas que não fazem parte do sistema analisado.
PASTAS_IGNORADAS = ("*/.venv/*", "*/venv/*", "*/__pycache__/*", "*/node_modules/*", "*/vendor/*")
_IGNORE_NOMES = "\\.venv,venv,__pycache__,node_modules,vendor,\\.git"


def _executar(comando: list[str]) -> tuple[str, str, int | None]:
    """Roda um comando e devolve (stdout, stderr, returncode).

    returncode ``None`` significa que a ferramenta não pôde ser executada
    (não instalada) ou estourou o timeout.
    """

    try:
        processo = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEGUNDOS,
        )
    except FileNotFoundError:
        return "", "interpretador não encontrado", None
    except subprocess.TimeoutExpired:
        return "", f"timeout de {TIMEOUT_SEGUNDOS}s excedido", None

    return processo.stdout, processo.stderr, processo.returncode


def _coletar(
    nome: str,
    comando: list[str],
    parser: Callable[[Any], list[Finding]],
    avisos: list[str],
) -> list[Finding]:
    """Executa uma ferramenta e converte a saída com o parser já existente.

    Nota sobre returncode: bandit sai com 1 quando ENCONTRA problemas e
    pylint usa um bitmask — nos dois casos, código diferente de zero é
    operação normal. Por isso o sinal de falha aqui é ausência de JSON
    utilizável, não o returncode.
    """

    stdout, stderr, returncode = _executar(comando)

    if returncode is None:
        avisos.append(f"{nome}: não executado ({stderr.strip() or 'indisponível'})")
        return []

    if not stdout.strip():
        primeira_linha = (stderr.strip().splitlines() or ["sem detalhes"])[0]
        avisos.append(f"{nome}: nenhuma saída (returncode={returncode}) — {primeira_linha}")
        return []

    try:
        dados = json.loads(stdout)
    except json.JSONDecodeError as erro:
        avisos.append(f"{nome}: JSON inválido — {erro}")
        return []

    try:
        return parser(dados)
    except (ValueError, KeyError, TypeError) as erro:
        avisos.append(f"{nome}: saída inesperada para o parser — {erro}")
        return []


def _relativizar(achados: list[Finding], raiz: Path) -> list[Finding]:
    """Troca caminho absoluto por caminho relativo ao repositório."""

    for achado in achados:
        if not achado.file_path:
            continue
        try:
            achado.file_path = Path(achado.file_path).resolve().relative_to(raiz).as_posix()
        except ValueError:
            achado.file_path = Path(achado.file_path).name
    return achados


def run_bandit(raiz: Path, avisos: list[str]) -> list[Finding]:
    comando = [
        sys.executable, "-m", "bandit",
        "-r", str(raiz),
        "-f", "json", "-q",
        "-x", ",".join(PASTAS_IGNORADAS),
    ]
    return _coletar("bandit", comando, parse_bandit, avisos)


def run_radon(raiz: Path, avisos: list[str]) -> list[Finding]:
    comando = [
        sys.executable, "-m", "radon", "cc", str(raiz),
        "-j", "-i", _IGNORE_NOMES,
    ]
    return _coletar("radon", comando, parse_radon, avisos)


def run_pylint(raiz: Path, avisos: list[str]) -> list[Finding]:
    comando = [
        sys.executable, "-m", "pylint", str(raiz),
        "--recursive=y",
        "--output-format=json",
        "--disable=C",
        f"--ignore={_IGNORE_NOMES.replace(chr(92), '')}",
    ]
    return _coletar("pylint", comando, parse_pylint, avisos)


def run_semgrep(raiz: Path, avisos: list[str]) -> list[Finding]:
    """Opcional: exige rede para baixar as regras. Ausência não é erro."""

    comando = [sys.executable, "-m", "semgrep", "--config=p/owasp-top-ten", "--json", str(raiz)]
    return _coletar("semgrep", comando, parse_semgrep, avisos)


FERRAMENTAS_PYTHON: dict[str, Callable[[Path, list[str]], list[Finding]]] = {
    "bandit": run_bandit,
    "radon": run_radon,
    "pylint": run_pylint,
}


def coletar_python(
    raiz: Path, incluir_semgrep: bool = False
) -> tuple[list[Finding], list[str]]:
    """Roda as ferramentas Python e devolve (achados, avisos).

    A lista de avisos nunca é descartada: ela vai para o relatório, para que
    "zero achados" e "ferramenta quebrada" sejam sempre distinguíveis.
    """

    raiz = raiz.resolve()
    avisos: list[str] = []
    achados: list[Finding] = []

    ferramentas = dict(FERRAMENTAS_PYTHON)
    if incluir_semgrep:
        ferramentas["semgrep"] = run_semgrep

    # sorted(): a ordem de execução não pode influenciar a saída.
    for nome in sorted(ferramentas):
        achados.extend(ferramentas[nome](raiz, avisos))

    return _relativizar(achados, raiz), avisos
