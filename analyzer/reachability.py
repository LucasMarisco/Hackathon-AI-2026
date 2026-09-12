"""Quais arquivos do repositório realmente executam?

Monta o grafo de imports com ``ast`` a partir dos pontos de entrada (arquivos
com ``if __name__ == "__main__"``) e caminha por ele. O que não for alcançado
é código morto: está no repositório, mas nenhuma execução do sistema passa
por ele.

Por que isso importa para a priorização: uma vulnerabilidade em código morto é
risco LATENTE, não exposição ativa. Nenhuma das ferramentas usadas faz essa
distinção — bandit, pylint e radon analisam arquivo por arquivo, sem saber se
o arquivo é alcançado. É o que separa "97 achados" de "os achados que estão no
ar agora".
"""

from __future__ import annotations

import ast
from pathlib import Path

PASTAS_IGNORADAS = {".venv", "venv", "__pycache__", ".git", "node_modules", "vendor"}


def _arquivos_python(raiz: Path) -> list[Path]:
    """Todos os .py do repositório, em ordem estável (sorted = determinismo)."""

    return sorted(
        caminho
        for caminho in raiz.rglob("*.py")
        if not PASTAS_IGNORADAS & set(caminho.parts)
    )


def _nome_modulo(arquivo: Path, raiz: Path) -> str:
    """app/services/billing_service.py -> app.services.billing_service"""

    partes = list(arquivo.relative_to(raiz).parts)
    if partes[-1] == "__init__.py":
        partes.pop()
    else:
        partes[-1] = partes[-1][: -len(".py")]
    return ".".join(partes)


def _imports_do_arquivo(arvore: ast.Module) -> set[str]:
    encontrados: set[str] = set()

    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for apelido in no.names:
                encontrados.add(apelido.name)
        elif isinstance(no, ast.ImportFrom) and no.module:
            encontrados.add(no.module)
            # `from app.services import billing_service` importa um MÓDULO,
            # não uma classe — por isso testamos as duas leituras.
            for apelido in no.names:
                encontrados.add(f"{no.module}.{apelido.name}")

    return encontrados


def _eh_ponto_de_entrada(arvore: ast.Module) -> bool:
    """O arquivo tem `if __name__ == '__main__':`?"""

    for no in ast.walk(arvore):
        if isinstance(no, ast.If):
            teste = no.test
            if (
                isinstance(teste, ast.Compare)
                and isinstance(teste.left, ast.Name)
                and teste.left.id == "__name__"
            ):
                return True
    return False


def mapear_alcancabilidade(raiz: Path) -> dict[str, bool]:
    """Devolve {caminho_relativo: True se o arquivo é alcançável}.

    LIMITAÇÕES CONHECIDAS (declarar limitação é parte de fazer análise séria):
      - Alcançabilidade no nível de ARQUIVO. Uma função morta dentro de um
        arquivo vivo continua marcada como alcançável.
      - Não segue import dinâmico (importlib, __import__) nem carregamento por
        framework (autoload do Composer, no caso do PHP).
      - Imports relativos (`from . import x`) não são resolvidos — o
        repositório-alvo não usa nenhum.
    """

    raiz = raiz.resolve()
    arquivos = _arquivos_python(raiz)

    modulo_para_arquivo: dict[str, Path] = {}
    imports_por_arquivo: dict[Path, set[str]] = {}
    pontos_de_entrada: list[Path] = []

    for arquivo in arquivos:
        try:
            arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            # Arquivo ilegível: trata como alcançável. Na dúvida, não
            # subestime o risco.
            imports_por_arquivo[arquivo] = set()
            continue

        modulo_para_arquivo[_nome_modulo(arquivo, raiz)] = arquivo
        imports_por_arquivo[arquivo] = _imports_do_arquivo(arvore)

        if _eh_ponto_de_entrada(arvore):
            pontos_de_entrada.append(arquivo)

    # Sem ponto de entrada não há como provar que algo é morto.
    if not pontos_de_entrada:
        return {a.relative_to(raiz).as_posix(): True for a in arquivos}

    alcancados: set[Path] = set()
    fila = list(pontos_de_entrada)

    while fila:
        atual = fila.pop(0)
        if atual in alcancados:
            continue
        alcancados.add(atual)

        for modulo in sorted(imports_por_arquivo.get(atual, set())):
            # Importar `app.services.billing_service` executa também os
            # __init__.py de `app` e de `app.services`.
            partes = modulo.split(".")
            for i in range(len(partes)):
                destino = modulo_para_arquivo.get(".".join(partes[: i + 1]))
                if destino is not None and destino not in alcancados:
                    fila.append(destino)

    return {
        arquivo.relative_to(raiz).as_posix(): (arquivo in alcancados)
        for arquivo in arquivos
    }
