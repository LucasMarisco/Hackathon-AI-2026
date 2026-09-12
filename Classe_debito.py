from dataclasses import dataclass

@dataclass
class DebitoTecnico:
    id: str
    nome: str
    # Variáveis do numerador (fatores de impacto)
    financeiro: float
    segurança: float
    aumento_problema: float
    imagem_empresa: float
    emocional: float
    # Variáveis do denominador (fatores redutores/atenuantes)
    tempo: float
    custo_tempo: float
    saber_cliente: float = 1.0
    
    # Campos calculados
    risco: float = 0.0
    risco_quantitativo: str = ""

    def calcular_prioridade(self):
        # Sua fórmula original
        denominador = self.tempo * self.custo_tempo * self.saber_cliente
        
        # Evita divisão por zero caso algum tempo seja 0
        if denominador == 0:
            denominador = 0.0001

        self.risco = (
            self.financeiro
            * self.segurança
            * self.aumento_problema
            * self.imagem_empresa
            * self.emocional
        ) / denominador

        if self.risco > 300:
            self.risco_quantitativo = "alto"
        elif 200 < self.risco <= 300:
            self.risco_quantitativo = "medio"
        else:
            self.risco_quantitativo = "baixo"

        return self.risco, self.risco_quantitativo


# --- TESTE COM DADOS DE EXEMPLO ---

debito_1 = DebitoTecnico(
    id="DT-01",
    nome="Vazamento de dados por falta de autenticação",
    financeiro=5,
    segurança=5,
    aumento_problema=4,
    imagem_empresa=5,
    emocional=4,
    tempo=2,
    custo_tempo=2,
    saber_cliente=1  # Cliente ainda não descobriu
)

debito_2 = DebitoTecnico(
    id="DT-02",
    nome="Refatoração de CSS/Layout",
    financeiro=1,
    segurança=1,
    aumento_problema=1,
    imagem_empresa=2,
    emocional=1,
    tempo=3,
    custo_tempo=2
    # saber_cliente assume o padrão 1.0 automaticamente
)

# Executando o cálculo
for dt in [debito_1, debito_2]:
    score, nivel = dt.calcular_prioridade()
    print(f"[{dt.id}] {dt.nome}")
    print(f"   Score Numérico: {score:.2f} | Prioridade: {nivel.upper()}\n")
