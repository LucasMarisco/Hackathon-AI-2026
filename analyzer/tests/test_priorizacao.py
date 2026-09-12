"""Testes da camada de priorização por contexto de negócio.

O enunciado faz duas exigências que testes conseguem PROVAR, em vez de só
prometer:

  1. "O scoring deve ser determinístico — rodado duas vezes no mesmo
      repositório, gera o mesmo resultado."
  2. "Não pode depender de LLM para calcular a prioridade."
"""

from __future__ import annotations

import random
import unittest

from business_context import ContextoNegocio
from priorizacao import (
    DebitoPriorizado,
    calcular_risco,
    faixa,
    ordenar_e_numerar,
    pontuar,
)


def ctx(**ajustes) -> ContextoNegocio:
    base = ContextoNegocio(esforco_sp=0.5)
    for nome, valor in ajustes.items():
        setattr(base, nome, valor)
    return base


def debito(pontuacao: float, arquivo: str = "a.py", linha: int = 1) -> DebitoPriorizado:
    return DebitoPriorizado(
        id="", conceito="dynamic_sql", categoria="Segurança", nome="n",
        descricao="d", arquivo=arquivo, linha=linha, impacto="i", risco="Alto",
        esforco_sp=0.5, valor="v", prioridade=faixa(pontuacao), pontuacao=pontuacao,
    )


class ConformidadeIATests(unittest.TestCase):
    """A IA pode redigir descrição; não pode calcular prioridade."""

    def test_priorizacao_nao_importa_biblioteca_de_llm(self):
        import priorizacao

        fonte = open(priorizacao.__file__, encoding="utf-8").read()
        for proibido in ("genai", "openai", "anthropic", "requests", "urllib"):
            self.assertNotIn(
                f"import {proibido}", fonte,
                f"priorizacao.py não pode importar {proibido}",
            )
            self.assertNotIn(f"from {proibido}", fonte)

    def test_pontuacao_depende_apenas_dos_fatores_declarados(self):
        """Mesmo contexto, mesma pontuação — sempre."""
        contexto = ctx(expoe_dados=True, perguntas_questionario=(1,))
        primeira, passos_a = pontuar("alto", contexto)
        segunda, passos_b = pontuar("alto", contexto)
        self.assertEqual(primeira, segunda)
        self.assertEqual(passos_a, passos_b)


class DeterminismoTests(unittest.TestCase):
    def test_ordem_final_independe_da_ordem_de_entrada(self):
        """A ordem do relatório não pode depender da ordem em que a
        ferramenta devolveu os achados.

        Comparamos (arquivo, linha) e NÃO a lista de IDs: os IDs são
        atribuídos sequencialmente depois da ordenação, então compará-los
        seria vacuamente verdadeiro — o teste passaria mesmo sem o sort.
        """
        base = [
            debito(19.7, "z.py", 10),
            debito(5.0, "a.py", 1),
            debito(13.6, "m.py", 5),
            debito(9.0, "b.py", 2),
        ]

        esperado = [
            (d.arquivo, d.linha) for d in ordenar_e_numerar([debito(d.pontuacao, d.arquivo, d.linha) for d in base])
        ]

        embaralhado = [debito(d.pontuacao, d.arquivo, d.linha) for d in base]
        random.Random(42).shuffle(embaralhado)
        obtido = [(d.arquivo, d.linha) for d in ordenar_e_numerar(embaralhado)]

        self.assertEqual(esperado, obtido)
        self.assertEqual(esperado[0][0], "z.py")  # maior pontuação primeiro

    def test_empate_desempata_por_campo_estavel(self):
        ordenados = ordenar_e_numerar([debito(9.0, "z.py", 1), debito(9.0, "a.py", 1)])
        self.assertEqual(ordenados[0].arquivo, "a.py")
        self.assertEqual(ordenados[0].id, "DT-01")


class RegrasDeNegocioTests(unittest.TestCase):
    def test_codigo_morto_pontua_menos_que_codigo_vivo(self):
        """Mesma SQLi: a que está no ar é mais urgente que a que retorna 404."""
        viva = pontuar("alto", ctx(alcancavel=True, rota_publica=True,
                                   expoe_dados=True, perguntas_questionario=(1,)))[0]
        morta = pontuar("alto", ctx(alcancavel=False, rota_publica=False,
                                    expoe_dados=True, perguntas_questionario=(1,)))[0]
        self.assertGreater(viva, morta)
        self.assertNotEqual(faixa(viva), faixa(morta))

    def test_questionario_eleva_a_pontuacao(self):
        """O prazo de 30 dias do cliente enterprise move o resultado."""
        self.assertGreater(
            pontuar("alto", ctx(perguntas_questionario=(1,)))[0],
            pontuar("alto", ctx())[0],
        )

    def test_achado_que_derruba_duas_perguntas_vale_mais(self):
        """MD5 responde 'Não' às perguntas 3 e 7 de uma vez."""
        self.assertGreater(
            pontuar("alto", ctx(perguntas_questionario=(3, 7)))[0],
            pontuar("alto", ctx(perguntas_questionario=(3,)))[0],
        )

    def test_esforco_alto_e_penalizado(self):
        """Com 6 SP/semana, correção cara desce na lista."""
        self.assertGreater(
            pontuar("alto", ctx(esforco_sp=0.5))[0],
            pontuar("alto", ctx(esforco_sp=8.0))[0],
        )

    def test_ruido_de_baixa_severidade_em_codigo_morto_fica_em_baixa(self):
        pontos, _ = pontuar("baixo", ctx(alcancavel=False, esforco_sp=0.5))
        self.assertEqual(faixa(pontos), "Baixa")

    def test_memorial_registra_cada_fator_aplicado(self):
        """A conta tem que ser auditável pelo jurado, não só o resultado."""
        _, passos = pontuar("alto", ctx(expoe_dados=True, rota_publica=True,
                                        perguntas_questionario=(3, 7), toca_release=True))
        texto = " ".join(passos)
        self.assertIn("base técnica", texto)
        self.assertIn("expõe dados", texto)
        self.assertIn("rota pública", texto)
        self.assertIn("Q3, Q7", texto)
        self.assertIn("release", texto)
        self.assertIn("esforço", texto)


class RiscoTests(unittest.TestCase):
    def test_codigo_morto_tem_risco_baixo(self):
        self.assertEqual(calcular_risco(ctx(alcancavel=False), "alto"), "Baixo")

    def test_rota_publica_com_severidade_alta_tem_risco_alto(self):
        self.assertEqual(calcular_risco(ctx(rota_publica=True), "alto"), "Alto")


class FaixasTests(unittest.TestCase):
    def test_limites_das_faixas(self):
        casos = [
            (20.0, "Crítica"), (15.0, "Crítica"), (14.99, "Alta"),
            (10.0, "Alta"), (9.99, "Média"), (5.0, "Média"),
            (4.99, "Baixa"), (-3.0, "Baixa"),
        ]
        for pontos, esperado in casos:
            with self.subTest(pontos=pontos):
                self.assertEqual(faixa(pontos), esperado)


if __name__ == "__main__":
    unittest.main()
