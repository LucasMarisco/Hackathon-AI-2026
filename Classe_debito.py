from dataclasses import dataclass, field

# ==========================================================
# ⚙️ PAINEL DE CONFIGURAÇÃO (ADICIONE, REMOVA OU EDITE AQUI)
# ==========================================================

# Parâmetros que multiplicam no numerador (quanto maior, pior o débito)
PESOS_AGRAVANTES = {
    "financeiro": 1.0,
    "segurança": 2.5,          # Foco na auditoria enterprise
    "aumento_problema": 1.2,
    "imagem_empresa": 1.5,
    "emocional": 0.8,
}

# Parâmetros que multiplicam no denominador (quanto maior, mais atenua/reduz a prioridade)
PESOS_ATENUANTES = {
    "tempo": 1.0,
    "custo_tempo": 1.0,
    "saber_cliente": 1.0,      # Default: 1.0 caso não seja passado
}

# Limiares de classificação
LIMIAR_ALTO = 300.0
LIMIAR_MEDIO = 200.0


# ==========================================================
# 📦 ESTRUTURA DO DÉBITO TÉCNICO
# ==========================================================

@dataclass
class DebitoTecnico:
    id: str
    nome: str
    
    # Dicionários dinâmicos com as notas atribuídas (ex: escala de 1 a 5)
    agravantes: dict[str, float] = field(default_factory=dict)
    atenuantes: dict[str, float] = field(default_factory=dict)
    
    # Resultados calculados
    risco: float = 0.0
    risco_quantitativo: str = ""

    def calcular_prioridade(self):
        # --------------------------------------------------
        # 📈 1. PRODUTÓRIO DOS AGRAVANTES (NUMERADOR)
        # --------------------------------------------------
        prod_agravantes = 1.0
        for fator, peso in PESOS_AGRAVANTES.items():
            # Pega a nota informada; se não foi passada, assume valor neutro 1.0
            nota = self.agravantes.get(fator, 1.0)
            prod_agravantes *= (nota * peso)

        # --------------------------------------------------
        # 📉 2. PRODUTÓRIO DOS ATENUANTES (DENOMINADOR)
        # --------------------------------------------------
        prod_atenuantes = 1.0
        for fator, peso in PESOS_ATENUANTES.items():
            nota = self.atenuantes.get(fator, 1.0)
            prod_atenuantes *= (nota * peso)

        # Proteção contra divisão por zero
        if prod_atenuantes == 0:
            prod_atenuantes = 0.0001

        # --------------------------------------------------
        # 🎯 3. SCORE E CLASSIFICAÇÃO DETERMINÍSTICA
        # --------------------------------------------------
        self.risco = prod_agravantes / prod_atenuantes

        if self.risco > LIMIAR_ALTO:
            self.risco_quantitativo = "alto"
        elif self.risco > LIMIAR_MEDIO:
            self.risco_quantitativo = "medio"
        else:
            self.risco_quantitativo = "baixo"

        return self.risco, self.risco_quantitativo


# ==========================================================
# 🧪 EXEMPLOS DE TESTE
# ==========================================================

# Exemplo 1: Falha crítica onde preenchemos todos os fatores
debito_1 = DebitoTecnico(
    id="DT-01",
    nome="Vazamento de credenciais de clientes",
    agravantes={
        "financeiro": 5,
        "segurança": 5,
        "aumento_problema": 4,
        "imagem_empresa": 5,
        "emocional": 3
    },
    atenuantes={
        "tempo": 1,
        "custo_tempo": 1,
        "saber_cliente": 1
    }
)

# Exemplo 2: Débito onde omitimos 'saber_cliente' (assume 1.0 automático)
debito_2 = DebitoTecnico(
    id="DT-02",
    nome="Refatoração de CSS/Layout legado",
    agravantes={
        "financeiro": 1,
        "segurança": 1,
        "aumento_problema": 1,
        "imagem_empresa": 1,
        "emocional": 2
    },
    atenuantes={
        "tempo": 3,
        "custo_tempo": 2
    }
)

for dt in [debito_1, debito_2]:
    score, nivel = dt.calcular_prioridade()
    print(f"[{dt.id}] {dt.nome}")
    print(f"   Score: {score:.2f} | Prioridade: {nivel.upper()}\n")
