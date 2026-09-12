# Relatório de Débitos Técnicos — HourTrack Ltda.

**Repositório analisado:** `bad-codebase-python`  
**Linguagem detectada:** python  
**Achados brutos das ferramentas:** 97 → **93 após deduplicação** → **92 débitos** (1 descartados como falso positivo)

## 1. Sumário executivo

- **6 das 7 perguntas** do questionário do cliente enterprise (R$ 8.000/mês, contrato que dobra o MRR de R$ 28.000) têm hoje a resposta **"Não"**.
- **2 débitos críticos** e **2 de prioridade alta**.
- **26 dos 92 débitos estão em código que executa hoje**; o restante é risco latente, em arquivos que nenhuma execução alcança.
- Esforço total catalogado: **170.0 SP** — 28.3 semanas na capacidade real do time (6 SP/semana, 2 desenvolvedores, sem QA).

| Prioridade | Qtd. | Esforço (SP) |
|---|---:|---:|
| Crítica | 2 | 3.5 |
| Alta | 2 | 4.0 |
| Média | 8 | 5.5 |
| Baixa | 80 | 157.0 |

## 2. Resposta ao questionário de segurança do cliente enterprise

> O questionário do repositório traz a nota: *"preenchido pelo time comercial com base no que acreditam ser verdade sobre o produto"*. Abaixo, cada resposta sai com a evidência que o pipeline anexou.

| # | Pergunta | Resposta honesta | Evidência | Plano de remediação |
|---|---|---|---|---|
| 1 | O sistema é protegido contra SQL Injection? | **Não** | `app/everything.py:219`; `app/routes/report_routes.py:29`; `app/routes/report_routes.py:44` (+3 ocorrências) | Trocar toda f-string em query por placeholder `?`. 0,5 SP por ocorrência. |
| 2 | O sistema é protegido contra Cross-Site Scripting (XSS)? | **Não** (verificação manual) | Nenhuma ferramenta do pipeline detecta XSS em HTML montado por f-string. Verificação manual encontrou o problema em app/everything.py:87-148 — o dashboard concatena nome de cliente sem escape, e o seed do banco já inclui um cliente chamado <script>alert(1)</script>. | Escapar o output do dashboard (usar template com autoescape). 2 SP. |
| 3 | As senhas são armazenadas com hash seguro (bcrypt, PBKDF2 ou Argon2)? | **Não** | `app/everything.py:168` | Migrar para bcrypt/Argon2 com rehash no próximo login. 3 SP. |
| 4 | Credenciais e API keys estão fora do código-fonte e do repositório Git? | **Não** | `sync_data.py:10`; `app/everything.py:6`; `app/routes/report_routes.py:103` (+2 ocorrências) | Mover segredos para variáveis de ambiente e ROTACIONAR — já estão no histórico do Git. 2 SP. |
| 5 | O repositório não contém arquivos .env com valores reais commitados? | **Sim** | nenhum .env com valores no repositório; apenas .env.example | Nenhuma ação: já conforme. Manter a regra no .gitignore. |
| 6 | O modo debug/desenvolvimento está desativado em produção? | **Não** (verificação manual) | bandit possui a regra B201 para debug=True, mas ela não dispara aqui: `app` é importado de outro módulo e a ferramenta não consegue provar que é um objeto Flask. Verificação manual confirma debug=True em run.py:4. | Definir debug=False em produção. 0,5 SP, uma linha. |
| 7 | O código não utiliza algoritmos de hash inseguros (MD5, SHA-1)? | **Não** | `app/everything.py:168` | Coberto pela migração da pergunta 3 — o mesmo commit resolve as duas. |

## 3. Débitos priorizados

| ID | Categoria | Nome | Descrição | Impacto | Risco | Esforço | Valor | Prioridade |
|---|---|---|---|---|---|---:|---|---|
| DT-01 | Segurança | Hash inseguro (MD5/SHA-1) em dado sensível | `app/everything.py:168` — Use of weak MD5 hash for security. Consider usedforsecurity=False | Senhas em MD5 são quebráveis em minutos. Derruba duas das sete respostas do questionário do cliente de R$ 8.000/mês — o contrato que dobraria o MRR de R$ 28.000. | Alto | 3.0 SP | Segurança e conformidade — destrava o contrato enterprise | **Crítica** |
| DT-02 | Segurança | SQL montado por concatenação de string | `app/everything.py:219` — Possible SQL injection vector through string-based query construction. | Permite ler e alterar a base inteira sem autenticação: as horas faturadas dos 47 clientes estão no mesmo banco, sem isolamento. Um vazamento atinge os 3 clientes que respondem por 60% da receita. | Alto | 0.5 SP | Segurança e conformidade — destrava o contrato enterprise | **Crítica** |
| DT-03 | Segurança | Segredo hardcoded no código-fonte | `sync_data.py:10` — Possible hardcoded password: 'ERP_TOKEN_production_abc123xyz789' | Credencial de produção exposta no código e no histórico do Git. Responder 'Não' à pergunta 4 do questionário trava a assinatura do contrato enterprise; apagar o arquivo não basta, exige rotação. | Médio | 2.0 SP | Segurança e conformidade — destrava o contrato enterprise | **Alta** |
| DT-04 | Segurança | Segredo hardcoded no código-fonte | `app/everything.py:6` — Possible hardcoded password: '123456' | Credencial de produção exposta no código e no histórico do Git. Responder 'Não' à pergunta 4 do questionário trava a assinatura do contrato enterprise; apagar o arquivo não basta, exige rotação. | Alto | 2.0 SP | Segurança e conformidade — destrava o contrato enterprise | **Alta** |
| DT-05 | Segurança | SQL montado por concatenação de string | `app/routes/report_routes.py:29` — Possible SQL injection vector through string-based query construction. | Permite ler e alterar a base inteira sem autenticação: as horas faturadas dos 47 clientes estão no mesmo banco, sem isolamento. Um vazamento atinge os 3 clientes que respondem por 60% da receita. | Baixo | 0.5 SP | Segurança e conformidade — destrava o contrato enterprise | **Média** |
| DT-06 | Segurança | SQL montado por concatenação de string | `app/routes/report_routes.py:44` — Possible SQL injection vector through string-based query construction. | Permite ler e alterar a base inteira sem autenticação: as horas faturadas dos 47 clientes estão no mesmo banco, sem isolamento. Um vazamento atinge os 3 clientes que respondem por 60% da receita. | Baixo | 0.5 SP | Segurança e conformidade — destrava o contrato enterprise | **Média** |
| DT-07 | Segurança | SQL montado por concatenação de string | `app/routes/report_routes.py:107` — Possible SQL injection vector through string-based query construction. | Permite ler e alterar a base inteira sem autenticação: as horas faturadas dos 47 clientes estão no mesmo banco, sem isolamento. Um vazamento atinge os 3 clientes que respondem por 60% da receita. | Baixo | 0.5 SP | Segurança e conformidade — destrava o contrato enterprise | **Média** |
| DT-08 | Segurança | SQL montado por concatenação de string | `app/services/billing_service.py:27` — Possible SQL injection vector through string-based query construction. | Permite ler e alterar a base inteira sem autenticação: as horas faturadas dos 47 clientes estão no mesmo banco, sem isolamento. Um vazamento atinge os 3 clientes que respondem por 60% da receita. | Baixo | 0.5 SP | Segurança e conformidade — destrava o contrato enterprise | **Média** |
| DT-09 | Segurança | Segredo hardcoded no código-fonte | `app/routes/report_routes.py:103` — Possible hardcoded password: 'CONTABILIZEI_TOKEN_prod_123abc' | Credencial de produção exposta no código e no histórico do Git. Responder 'Não' à pergunta 4 do questionário trava a assinatura do contrato enterprise; apagar o arquivo não basta, exige rotação. | Baixo | 2.0 SP | Segurança e conformidade — destrava o contrato enterprise | **Média** |
| DT-10 | Segurança | SQL montado por concatenação de string | `app/models/customer.py:38` — Possible SQL injection vector through string-based query construction. | Permite ler e alterar a base inteira sem autenticação: as horas faturadas dos 47 clientes estão no mesmo banco, sem isolamento. Um vazamento atinge os 3 clientes que respondem por 60% da receita. | Baixo | 0.5 SP | Segurança e conformidade — destrava o contrato enterprise | **Média** |
| DT-11 | Performance | Chamada HTTP sem timeout | `sync_data.py:71` — Requests call without timeout | Chamada externa sem timeout prende o processo. Com 1 VPS de 2GB atendendo 180 usuários e sem monitoramento, a queda só é descoberta quando o cliente liga. | Médio | 0.5 SP | Disponibilidade — protege o uptime de 99,1% | **Média** |
| DT-12 | Arquitetura | Import não resolvido no ambiente de análise | `app/everything.py:2` — Unable to import 'flask' | Sinal de ambiente de análise incompleto, não de defeito do produto. Verificar antes de reportar ao cliente. | Médio | 0.5 SP | Higiene do ambiente de análise | **Média** |
| DT-13 | Segurança | Segredo hardcoded no código-fonte | `app/services/notification_service.py:10` — Possible hardcoded password: 'SMSGLOBAL_SECRET_xyz789' | Credencial de produção exposta no código e no histórico do Git. Responder 'Não' à pergunta 4 do questionário trava a assinatura do contrato enterprise; apagar o arquivo não basta, exige rotação. | Baixo | 2.0 SP | Segurança e conformidade — destrava o contrato enterprise | **Baixa** |
| DT-14 | Segurança | Segredo hardcoded no código-fonte | `app/services/notification_service.py:15` — Possible hardcoded password: 'gmail_app_password_hardcoded_123' | Credencial de produção exposta no código e no histórico do Git. Responder 'Não' à pergunta 4 do questionário trava a assinatura do contrato enterprise; apagar o arquivo não basta, exige rotação. | Baixo | 2.0 SP | Segurança e conformidade — destrava o contrato enterprise | **Baixa** |
| DT-15 | Design | Variável calculada e nunca usada | `app/everything.py:76` — Unused variable 'total_hours' | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-16 | Design | Variável calculada e nunca usada | `app/everything.py:77` — Unused variable 'avg_rate' | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-17 | Design | Variável calculada e nunca usada | `app/everything.py:78` — Unused variable 'entry_count' | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-18 | Design | Variável calculada e nunca usada | `app/everything.py:79` — Unused variable 'last_customer_id' | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-19 | Design | TODO deixado no código | `app/everything.py:83` — TODO: adicionar paginação aqui | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-20 | Design | Nome sombreia um builtin do Python | `app/everything.py:196` — Redefining built-in 'id' | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-21 | Performance | Chamada HTTP sem timeout | `app/routes/report_routes.py:116` — Requests call without timeout | Chamada externa sem timeout prende o processo. Com 1 VPS de 2GB atendendo 180 usuários e sem monitoramento, a queda só é descoberta quando o cliente liga. | Baixo | 0.5 SP | Disponibilidade — protege o uptime de 99,1% | **Baixa** |
| DT-22 | Manutenibilidade | Excesso de variáveis locais | `app/everything.py:40` — Too many local variables (27/15) | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 2.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-23 | Arquitetura | Import não resolvido no ambiente de análise | `app/routes/report_routes.py:5` — Unable to import 'flask' | Sinal de ambiente de análise incompleto, não de defeito do produto. Verificar antes de reportar ao cliente. | Baixo | 0.5 SP | Higiene do ambiente de análise | **Baixa** |
| DT-24 | Performance | Chamada HTTP sem timeout | `app/services/notification_service.py:44` — Requests call without timeout | Chamada externa sem timeout prende o processo. Com 1 VPS de 2GB atendendo 180 usuários e sem monitoramento, a queda só é descoberta quando o cliente liga. | Baixo | 0.5 SP | Disponibilidade — protege o uptime de 99,1% | **Baixa** |
| DT-25 | Performance | Chamada HTTP sem timeout | `app/services/notification_service.py:53` — Requests call without timeout | Chamada externa sem timeout prende o processo. Com 1 VPS de 2GB atendendo 180 usuários e sem monitoramento, a queda só é descoberta quando o cliente liga. | Baixo | 0.5 SP | Disponibilidade — protege o uptime de 99,1% | **Baixa** |
| DT-26 | Design | else desnecessário após return | `app/routes/report_routes.py:60` — Unnecessary "elif" after "return", remove the leading "el" from "elif" | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-27 | Manutenibilidade | Função com complexidade ciclomática alta | `app/everything.py:31` — Cyclomatic complexity for get_db: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-28 | Manutenibilidade | Função com complexidade ciclomática alta | `app/everything.py:40` — Cyclomatic complexity for dashboard: 16 (rank C) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-29 | Manutenibilidade | Função com complexidade ciclomática alta | `app/everything.py:153` — Cyclomatic complexity for save: 6 (rank B) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-30 | Manutenibilidade | Função com complexidade ciclomática alta | `app/everything.py:196` — Cyclomatic complexity for delete: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-31 | Manutenibilidade | Função com complexidade ciclomática alta | `app/everything.py:211` — Cyclomatic complexity for report: 3 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-32 | Manutenibilidade | Captura de exceção genérica demais | `app/routes/report_routes.py:127` — Catching too general exception Exception | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-33 | Manutenibilidade | Exceção engolida silenciosamente | `app/routes/report_routes.py:127` — Try, Except, Pass detected. | Falha silenciosa: a fatura é calculada e não é gravada, sem ninguém saber. Sem monitoramento, o erro aparece na contestação do cliente. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-34 | Manutenibilidade | Captura de exceção genérica demais | `app/services/billing_service.py:77` — Catching too general exception Exception | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-35 | Manutenibilidade | Exceção engolida silenciosamente | `app/services/billing_service.py:77` — Try, Except, Pass detected. | Falha silenciosa: a fatura é calculada e não é gravada, sem ninguém saber. Sem monitoramento, o erro aparece na contestação do cliente. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-36 | Manutenibilidade | Redefining name 'dry_run' from outer scope (line 108) | `sync_data.py:18` — Redefining name 'dry_run' from outer scope (line 108) | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-37 | Manutenibilidade | Captura de exceção genérica demais | `sync_data.py:25` — Catching too general exception Exception | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-38 | Manutenibilidade | Captura de exceção genérica demais | `sync_data.py:72` — Catching too general exception Exception | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-39 | Manutenibilidade | Exceção engolida silenciosamente | `sync_data.py:72` — Try, Except, Pass detected. | Falha silenciosa: a fatura é calculada e não é gravada, sem ninguém saber. Sem monitoramento, o erro aparece na contestação do cliente. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-40 | Manutenibilidade | Redefining name 'dry_run' from outer scope (line 108) | `sync_data.py:77` — Redefining name 'dry_run' from outer scope (line 108) | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-41 | Manutenibilidade | Captura de exceção genérica demais | `sync_data.py:85` — Catching too general exception Exception | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-42 | Design | else desnecessário após return | `app/helpers/date_helper.py:15` — Unnecessary "else" after "return", remove the "else" and de-indent the code inside it | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-43 | Design | else desnecessário após return | `app/helpers/date_helper.py:65` — Unnecessary "else" after "return", remove the "else" and de-indent the code inside it | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-44 | Design | else desnecessário após return | `app/helpers/date_helper.py:68` — Unnecessary "else" after "return", remove the "else" and de-indent the code inside it | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-45 | Design | else desnecessário após return | `app/helpers/date_helper.py:74` — Unnecessary "elif" after "return", remove the leading "el" from "elif" | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-46 | Design | else desnecessário após return | `app/models/billing_category.py:22` — Unnecessary "elif" after "return", remove the leading "el" from "elif" | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-47 | Design | else desnecessário após return | `app/models/billing_category.py:29` — Unnecessary "else" after "return", remove the "else" and de-indent the code inside it | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-48 | Design | else desnecessário após return | `app/services/notification_service.py:88` — Unnecessary "elif" after "return", remove the leading "el" from "elif" | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 0.5 SP | Qualidade — acelera o time de 2 devs | **Baixa** |
| DT-49 | Manutenibilidade | Captura de exceção genérica demais | `app/helpers/date_helper.py:57` — Catching too general exception Exception | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-50 | Manutenibilidade | Captura de exceção genérica demais | `app/services/notification_service.py:40` — Catching too general exception Exception | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-51 | Manutenibilidade | Captura de exceção genérica demais | `app/services/notification_service.py:49` — Catching too general exception Exception | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-52 | Manutenibilidade | Exceção engolida silenciosamente | `app/services/notification_service.py:49` — Try, Except, Pass detected. | Falha silenciosa: a fatura é calculada e não é gravada, sem ninguém saber. Sem monitoramento, o erro aparece na contestação do cliente. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-53 | Manutenibilidade | Captura de exceção genérica demais | `app/services/notification_service.py:62` — Catching too general exception Exception | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-54 | Manutenibilidade | Exceção engolida silenciosamente | `app/services/notification_service.py:62` — Try, Except, Pass detected. | Falha silenciosa: a fatura é calculada e não é gravada, sem ninguém saber. Sem monitoramento, o erro aparece na contestação do cliente. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-55 | Manutenibilidade | Captura de exceção genérica demais | `app/services/notification_service.py:81` — Catching too general exception Exception | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-56 | Manutenibilidade | Exceção engolida silenciosamente | `app/services/notification_service.py:81` — Try, Except, Pass detected. | Falha silenciosa: a fatura é calculada e não é gravada, sem ninguém saber. Sem monitoramento, o erro aparece na contestação do cliente. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-57 | Manutenibilidade | Retornos inconsistentes | `app/services/notification_service.py:86` — Either all return statements in a function should return an expression, or none of them should. | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 1.0 SP | Confiabilidade — evita erro de faturamento | **Baixa** |
| DT-58 | Manutenibilidade | Função com complexidade ciclomática alta | `app/routes/report_routes.py:13` — Cyclomatic complexity for ReportController: 6 (rank B) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-59 | Manutenibilidade | Função com complexidade ciclomática alta | `app/routes/report_routes.py:14` — Cyclomatic complexity for __init__: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-60 | Manutenibilidade | Função com complexidade ciclomática alta | `app/routes/report_routes.py:17` — Cyclomatic complexity for monthly: 12 (rank C) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-61 | Manutenibilidade | Função com complexidade ciclomática alta | `app/routes/report_routes.py:82` — Cyclomatic complexity for annual: 3 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-62 | Manutenibilidade | Função com complexidade ciclomática alta | `app/routes/report_routes.py:97` — Cyclomatic complexity for export_for_accounting: 3 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-63 | Manutenibilidade | Função com complexidade ciclomática alta | `app/routes/report_routes.py:137` — Cyclomatic complexity for monthly: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-64 | Manutenibilidade | Função com complexidade ciclomática alta | `app/routes/report_routes.py:142` — Cyclomatic complexity for annual: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-65 | Manutenibilidade | Função com complexidade ciclomática alta | `app/routes/report_routes.py:147` — Cyclomatic complexity for export_for_accounting: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-66 | Manutenibilidade | Função com complexidade ciclomática alta | `app/services/billing_service.py:8` — Cyclomatic complexity for BillingService: 6 (rank B) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-67 | Manutenibilidade | Função com complexidade ciclomática alta | `app/services/billing_service.py:9` — Cyclomatic complexity for __init__: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-68 | Manutenibilidade | Função com complexidade ciclomática alta | `app/services/billing_service.py:12` — Cyclomatic complexity for calculate_invoice: 10 (rank B) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-69 | Manutenibilidade | Função com complexidade ciclomática alta | `app/services/billing_service.py:102` — Cyclomatic complexity for generate_monthly_report: 4 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-70 | Manutenibilidade | Função com complexidade ciclomática alta | `sync_data.py:18` — Cyclomatic complexity for sync_from_erp: 10 (rank B) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-71 | Manutenibilidade | Função com complexidade ciclomática alta | `sync_data.py:77` — Cyclomatic complexity for sync_from_crm: 8 (rank B) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-72 | Manutenibilidade | Excesso de pontos de retorno | `app/helpers/date_helper.py:8` — Too many return statements (25/6) | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 2.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-73 | Manutenibilidade | Excesso de pontos de retorno | `app/models/billing_category.py:19` — Too many return statements (7/6) | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 2.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-74 | Manutenibilidade | Excesso de ramificações na função | `app/helpers/date_helper.py:8` — Too many branches (29/12) | Aumenta o custo de manutenção de um time de 2 desenvolvedores com capacidade de 6 story points por semana e sem QA. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-75 | Manutenibilidade | Função com complexidade ciclomática alta | `app/helpers/date_helper.py:87` — Cyclomatic complexity for format_for_display: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-76 | Manutenibilidade | Função com complexidade ciclomática alta | `app/helpers/date_helper.py:91` — Cyclomatic complexity for is_valid: 2 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-77 | Manutenibilidade | Função com complexidade ciclomática alta | `app/models/billing_category.py:5` — Cyclomatic complexity for BillingCategory: 4 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-78 | Manutenibilidade | Função com complexidade ciclomática alta | `app/models/billing_category.py:6` — Cyclomatic complexity for __init__: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-79 | Manutenibilidade | Função com complexidade ciclomática alta | `app/models/billing_category.py:12` — Cyclomatic complexity for get_display_name: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-80 | Manutenibilidade | Função com complexidade ciclomática alta | `app/models/billing_category.py:19` — Cyclomatic complexity for get_effective_rate: 7 (rank B) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-81 | Manutenibilidade | Função com complexidade ciclomática alta | `app/models/billing_category.py:39` — Cyclomatic complexity for get_most_used: 2 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-82 | Manutenibilidade | Função com complexidade ciclomática alta | `app/models/customer.py:5` — Cyclomatic complexity for Customer: 3 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-83 | Manutenibilidade | Função com complexidade ciclomática alta | `app/models/customer.py:6` — Cyclomatic complexity for __init__: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-84 | Manutenibilidade | Função com complexidade ciclomática alta | `app/models/customer.py:12` — Cyclomatic complexity for get_display_name: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-85 | Manutenibilidade | Função com complexidade ciclomática alta | `app/models/customer.py:18` — Cyclomatic complexity for is_high_value: 3 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-86 | Manutenibilidade | Função com complexidade ciclomática alta | `app/models/customer.py:35` — Cyclomatic complexity for get_month_total: 3 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-87 | Manutenibilidade | Função com complexidade ciclomática alta | `app/services/notification_service.py:8` — Cyclomatic complexity for NotificationService: 6 (rank B) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-88 | Manutenibilidade | Função com complexidade ciclomática alta | `app/services/notification_service.py:17` — Cyclomatic complexity for __init__: 1 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-89 | Manutenibilidade | Função com complexidade ciclomática alta | `app/services/notification_service.py:20` — Cyclomatic complexity for send: 12 (rank C) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-90 | Manutenibilidade | Função com complexidade ciclomática alta | `app/services/notification_service.py:86` — Cyclomatic complexity for format_message: 5 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-91 | Manutenibilidade | Função com complexidade ciclomática alta | `app/services/notification_service.py:98` — Cyclomatic complexity for build_message: 3 (rank A) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 3.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |
| DT-92 | Manutenibilidade | Função com complexidade ciclomática alta | `app/helpers/date_helper.py:8` — Cyclomatic complexity for handle_date: 29 (rank D) | Função complexa demais para alterar com segurança. O desenvolvedor que escreveu 90% do código sai em 6 semanas, e não há testes nem staging — o conhecimento sai junto com ele. | Baixo | 8.0 SP | Manutenibilidade — reduz o risco da saída do dev em 6 semanas | **Baixa** |

## 4. Risco ativo vs. risco latente

A análise de alcançabilidade (grafo de imports a partir dos pontos de entrada) mostra que **10 de 14 arquivos não são alcançados por nenhuma execução do sistema**. Isso rebaixa 66 débitos de exposição ativa para risco latente.

Arquivos não alcançados:

- `app/helpers/__init__.py`
- `app/helpers/date_helper.py`
- `app/models/__init__.py`
- `app/models/billing_category.py`
- `app/models/customer.py`
- `app/routes/__init__.py`
- `app/routes/report_routes.py`
- `app/services/__init__.py`
- `app/services/billing_service.py`
- `app/services/notification_service.py`

> **A recomendação de maior valor deste relatório:** o blueprint de relatórios nunca é registrado na aplicação, então `/api/reports/*` retorna 404 hoje. A release v2.1 é justamente *"relatório por projeto"* — no primeiro `register_blueprint`, essas vulnerabilidades saem do estado latente de uma vez. **Corrigi-las junto com a feature custa cerca de 3 SP; depois dela, vira incidente.**

## 5. Memorial de cálculo

A conta de cada débito, passo a passo. Os pesos e a justificativa de negócio de cada um estão em `analyzer/priorizacao.py` e `analyzer/business_context.py`.

| ID | Pontuação | Conta |
|---|---:|---|
| DT-01 | 19.66 | base técnica (alto) = 7.00 x expõe dados de cliente (1.6) = 11.20 x rota pública sem auth (1.3) = 14.56 + questionário Q3, Q7 (6.0) = 20.56 + caminho da release v2.1 (1.5) = 22.06 - esforço 3.0 SP (2.40) = 19.66 |
| DT-02 | 19.66 | base técnica (alto) = 7.00 x expõe dados de cliente (1.6) = 11.20 x rota pública sem auth (1.3) = 14.56 + questionário Q1 (4.0) = 18.56 + caminho da release v2.1 (1.5) = 20.06 - esforço 0.5 SP (0.40) = 19.66 |
| DT-03 | 13.60 | base técnica (alto) = 7.00 x expõe dados de cliente (1.6) = 11.20 + questionário Q4 (4.0) = 15.20 - esforço 2.0 SP (1.60) = 13.60 |
| DT-04 | 13.00 | base técnica (alto) = 7.00 x rota pública sem auth (1.3) = 9.10 + questionário Q4 (4.0) = 13.10 + caminho da release v2.1 (1.5) = 14.60 - esforço 2.0 SP (1.60) = 13.00 |
| DT-05 | 9.02 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 x expõe dados de cliente (1.6) = 3.92 + questionário Q1 (4.0) = 7.92 + caminho da release v2.1 (1.5) = 9.42 - esforço 0.5 SP (0.40) = 9.02 |
| DT-06 | 9.02 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 x expõe dados de cliente (1.6) = 3.92 + questionário Q1 (4.0) = 7.92 + caminho da release v2.1 (1.5) = 9.42 - esforço 0.5 SP (0.40) = 9.02 |
| DT-07 | 9.02 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 x expõe dados de cliente (1.6) = 3.92 + questionário Q1 (4.0) = 7.92 + caminho da release v2.1 (1.5) = 9.42 - esforço 0.5 SP (0.40) = 9.02 |
| DT-08 | 9.02 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 x expõe dados de cliente (1.6) = 3.92 + questionário Q1 (4.0) = 7.92 + caminho da release v2.1 (1.5) = 9.42 - esforço 0.5 SP (0.40) = 9.02 |
| DT-09 | 7.82 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 x expõe dados de cliente (1.6) = 3.92 + questionário Q4 (4.0) = 7.92 + caminho da release v2.1 (1.5) = 9.42 - esforço 2.0 SP (1.60) = 7.82 |
| DT-10 | 7.52 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 x expõe dados de cliente (1.6) = 3.92 + questionário Q1 (4.0) = 7.92 - esforço 0.5 SP (0.40) = 7.52 |
| DT-11 | 6.60 | base técnica (alto) = 7.00 - esforço 0.5 SP (0.40) = 6.60 |
| DT-12 | 6.30 | base técnica (medio) = 4.00 x rota pública sem auth (1.3) = 5.20 + caminho da release v2.1 (1.5) = 6.70 - esforço 0.5 SP (0.40) = 6.30 |
| DT-13 | 4.85 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 + questionário Q4 (4.0) = 6.45 - esforço 2.0 SP (1.60) = 4.85 |
| DT-14 | 4.85 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 + questionário Q4 (4.0) = 6.45 - esforço 2.0 SP (1.60) = 4.85 |
| DT-15 | 3.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 0.5 SP (0.40) = 3.70 |
| DT-16 | 3.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 0.5 SP (0.40) = 3.70 |
| DT-17 | 3.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 0.5 SP (0.40) = 3.70 |
| DT-18 | 3.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 0.5 SP (0.40) = 3.70 |
| DT-19 | 3.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 0.5 SP (0.40) = 3.70 |
| DT-20 | 3.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 0.5 SP (0.40) = 3.70 |
| DT-21 | 3.55 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 + caminho da release v2.1 (1.5) = 3.95 - esforço 0.5 SP (0.40) = 3.55 |
| DT-22 | 2.50 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 2.0 SP (1.60) = 2.50 |
| DT-23 | 2.50 | base técnica (medio) = 4.00 x código morto (0.35) = 1.40 + caminho da release v2.1 (1.5) = 2.90 - esforço 0.5 SP (0.40) = 2.50 |
| DT-24 | 2.05 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 - esforço 0.5 SP (0.40) = 2.05 |
| DT-25 | 2.05 | base técnica (alto) = 7.00 x código morto (0.35) = 2.45 - esforço 0.5 SP (0.40) = 2.05 |
| DT-26 | 1.80 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 0.5 SP (0.40) = 1.80 |
| DT-27 | 1.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 3.0 SP (2.40) = 1.70 |
| DT-28 | 1.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 3.0 SP (2.40) = 1.70 |
| DT-29 | 1.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 3.0 SP (2.40) = 1.70 |
| DT-30 | 1.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 3.0 SP (2.40) = 1.70 |
| DT-31 | 1.70 | base técnica (baixo) = 2.00 x rota pública sem auth (1.3) = 2.60 + caminho da release v2.1 (1.5) = 4.10 - esforço 3.0 SP (2.40) = 1.70 |
| DT-32 | 1.40 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 1.0 SP (0.80) = 1.40 |
| DT-33 | 1.40 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 1.0 SP (0.80) = 1.40 |
| DT-34 | 1.40 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 1.0 SP (0.80) = 1.40 |
| DT-35 | 1.40 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 1.0 SP (0.80) = 1.40 |
| DT-36 | 1.20 | base técnica (baixo) = 2.00 - esforço 1.0 SP (0.80) = 1.20 |
| DT-37 | 1.20 | base técnica (baixo) = 2.00 - esforço 1.0 SP (0.80) = 1.20 |
| DT-38 | 1.20 | base técnica (baixo) = 2.00 - esforço 1.0 SP (0.80) = 1.20 |
| DT-39 | 1.20 | base técnica (baixo) = 2.00 - esforço 1.0 SP (0.80) = 1.20 |
| DT-40 | 1.20 | base técnica (baixo) = 2.00 - esforço 1.0 SP (0.80) = 1.20 |
| DT-41 | 1.20 | base técnica (baixo) = 2.00 - esforço 1.0 SP (0.80) = 1.20 |
| DT-42 | 0.30 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 0.5 SP (0.40) = 0.30 |
| DT-43 | 0.30 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 0.5 SP (0.40) = 0.30 |
| DT-44 | 0.30 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 0.5 SP (0.40) = 0.30 |
| DT-45 | 0.30 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 0.5 SP (0.40) = 0.30 |
| DT-46 | 0.30 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 0.5 SP (0.40) = 0.30 |
| DT-47 | 0.30 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 0.5 SP (0.40) = 0.30 |
| DT-48 | 0.30 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 0.5 SP (0.40) = 0.30 |
| DT-49 | -0.10 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 1.0 SP (0.80) = -0.10 |
| DT-50 | -0.10 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 1.0 SP (0.80) = -0.10 |
| DT-51 | -0.10 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 1.0 SP (0.80) = -0.10 |
| DT-52 | -0.10 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 1.0 SP (0.80) = -0.10 |
| DT-53 | -0.10 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 1.0 SP (0.80) = -0.10 |
| DT-54 | -0.10 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 1.0 SP (0.80) = -0.10 |
| DT-55 | -0.10 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 1.0 SP (0.80) = -0.10 |
| DT-56 | -0.10 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 1.0 SP (0.80) = -0.10 |
| DT-57 | -0.10 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 1.0 SP (0.80) = -0.10 |
| DT-58 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-59 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-60 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-61 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-62 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-63 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-64 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-65 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-66 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-67 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-68 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-69 | -0.20 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 + caminho da release v2.1 (1.5) = 2.20 - esforço 3.0 SP (2.40) = -0.20 |
| DT-70 | -0.40 | base técnica (baixo) = 2.00 - esforço 3.0 SP (2.40) = -0.40 |
| DT-71 | -0.40 | base técnica (baixo) = 2.00 - esforço 3.0 SP (2.40) = -0.40 |
| DT-72 | -0.90 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 2.0 SP (1.60) = -0.90 |
| DT-73 | -0.90 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 2.0 SP (1.60) = -0.90 |
| DT-74 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-75 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-76 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-77 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-78 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-79 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-80 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-81 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-82 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-83 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-84 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-85 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-86 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-87 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-88 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-89 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-90 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-91 | -1.70 | base técnica (baixo) = 2.00 x código morto (0.35) = 0.70 - esforço 3.0 SP (2.40) = -1.70 |
| DT-92 | -5.00 | base técnica (medio) = 4.00 x código morto (0.35) = 1.40 - esforço 8.0 SP (6.40) = -5.00 |

## 6. Falsos positivos descartados

Achados que as ferramentas reportaram, que abrimos no editor e concluímos **não** serem problema. Ficam registrados aqui em vez de sumirem em silêncio.

| Ferramenta | Local | Por que não é problema |
|---|---|---|
| bandit | `app/everything.py:205` | Apenas a ocorrência da linha 205 (rota /delete) é falso positivo: a f-string interpola TABLE_MAP[thing], dicionário fechado de 4 itens definido na própria função. O usuário controla a chave, mas o valor só pode ser um dos 4 nomes de tabela — ou KeyError. Verificado à mão. |

## 7. O que a IA sugeriu que estava errado, e por quê

| Afirmação | Origem | Por que está errado | Como verificamos |
|---|---|---|---|
| O banco database.sqlite está commitado no repositório. | IA (repetindo o business-context.md) | Falso para o repositório Python. O .gitignore ignora *.sqlite e não há nenhum arquivo .sqlite rastreado. A IA repetiu o documento de contexto em vez de olhar o repositório. | git ls-files &#124; grep -i sqlite — nenhum resultado |
| Há um arquivo .env com credenciais reais commitado. | IA (repetindo o business-context.md) | Falso. Só existe .env.example, sem valores. É a única das 7 perguntas do questionário cuja resposta honesta hoje é 'Sim'. | git ls-files &#124; grep env — apenas .env.example |
| SQL Injection crítica e explorável em /api/reports/monthly. | bandit B608 + IA | O código É vulnerável, mas o blueprint report_bp nunca é registrado na aplicação: a rota retorna 404 hoje. É risco LATENTE, não exposição ativa. A ferramenta analisa arquivo por arquivo e não enxerga o grafo de chamadas. | grep -rn 'register_blueprint' — nenhum resultado; confirmado pelo módulo reachability.py deste pipeline |
| SQL Injection na rota /delete (app/everything.py:205). | bandit B608 | A f-string interpola TABLE_MAP[thing], um dicionário fechado de 4 itens definido na própria função. O usuário controla a chave, mas o valor só pode ser um dos 4 nomes de tabela — ou KeyError. Não há vetor de injeção. Descartado do relatório. | leitura manual de app/everything.py:196-207 |
| O SELECT * do dashboard expõe a senha na resposta HTTP. | comentário no próprio código-fonte + IA | A senha é carregada em memória, mas o loop de renderização usa apenas ['name', 'email', 'address'] — ela não sai na resposta. A IA acreditou no comentário do código em vez de ler o render. É over-fetch, severidade baixa. | leitura manual de app/everything.py:132-145 |
| Os testes do pipeline provam que o scoring é determinístico. | código gerado por IA nesta sessão | Um dos testes comparava listas de IDs sequenciais (DT-01, DT-02...) que são atribuídos DEPOIS da ordenação — ele passava mesmo se o .sort() fosse removido. Teste vacuamente verdadeiro. Corrigido para comparar (arquivo, linha). | auditoria dirigida ao código gerado, antes do commit |

## 8. Plano de 6 semanas — "CTO por um dia"

Alocação derivada da pontuação, respeitando os 6 SP/semana de capacidade real. Não é opinião: é consequência aritmética do modelo — mexer num peso recalcula o plano inteiro.

**Semana 1** — 6.0 SP

- `DT-01` Hash inseguro (MD5/SHA-1) em dado sensível em `app/everything.py:168` — 3.0 SP (Crítica)
- `DT-02` SQL montado por concatenação de string em `app/everything.py:219` — 0.5 SP (Crítica)
- `DT-03` Segredo hardcoded no código-fonte em `sync_data.py:10` — 2.0 SP (Alta)
- `DT-05` SQL montado por concatenação de string em `app/routes/report_routes.py:29` — 0.5 SP (Média)

**Semana 2** — 6.0 SP

- `DT-04` Segredo hardcoded no código-fonte em `app/everything.py:6` — 2.0 SP (Alta)
- `DT-06` SQL montado por concatenação de string em `app/routes/report_routes.py:44` — 0.5 SP (Média)
- `DT-07` SQL montado por concatenação de string em `app/routes/report_routes.py:107` — 0.5 SP (Média)
- `DT-08` SQL montado por concatenação de string em `app/services/billing_service.py:27` — 0.5 SP (Média)
- `DT-09` Segredo hardcoded no código-fonte em `app/routes/report_routes.py:103` — 2.0 SP (Média)
- `DT-10` SQL montado por concatenação de string em `app/models/customer.py:38` — 0.5 SP (Média)

**Semana 3** — 6.0 SP

- `DT-11` Chamada HTTP sem timeout em `sync_data.py:71` — 0.5 SP (Média)
- `DT-12` Import não resolvido no ambiente de análise em `app/everything.py:2` — 0.5 SP (Média)
- `DT-13` Segredo hardcoded no código-fonte em `app/services/notification_service.py:10` — 2.0 SP (Baixa)
- `DT-14` Segredo hardcoded no código-fonte em `app/services/notification_service.py:15` — 2.0 SP (Baixa)
- `DT-15` Variável calculada e nunca usada em `app/everything.py:76` — 0.5 SP (Baixa)
- `DT-16` Variável calculada e nunca usada em `app/everything.py:77` — 0.5 SP (Baixa)

**Semana 4** — 6.0 SP

- `DT-17` Variável calculada e nunca usada em `app/everything.py:78` — 0.5 SP (Baixa)
- `DT-18` Variável calculada e nunca usada em `app/everything.py:79` — 0.5 SP (Baixa)
- `DT-19` TODO deixado no código em `app/everything.py:83` — 0.5 SP (Baixa)
- `DT-20` Nome sombreia um builtin do Python em `app/everything.py:196` — 0.5 SP (Baixa)
- `DT-21` Chamada HTTP sem timeout em `app/routes/report_routes.py:116` — 0.5 SP (Baixa)
- `DT-22` Excesso de variáveis locais em `app/everything.py:40` — 2.0 SP (Baixa)
- `DT-23` Import não resolvido no ambiente de análise em `app/routes/report_routes.py:5` — 0.5 SP (Baixa)
- `DT-24` Chamada HTTP sem timeout em `app/services/notification_service.py:44` — 0.5 SP (Baixa)
- `DT-25` Chamada HTTP sem timeout em `app/services/notification_service.py:53` — 0.5 SP (Baixa)

**Semana 5** — 6.0 SP

- `DT-26` else desnecessário após return em `app/routes/report_routes.py:60` — 0.5 SP (Baixa)
- `DT-27` Função com complexidade ciclomática alta em `app/everything.py:31` — 3.0 SP (Baixa)
- `DT-32` Captura de exceção genérica demais em `app/routes/report_routes.py:127` — 1.0 SP (Baixa)
- `DT-33` Exceção engolida silenciosamente em `app/routes/report_routes.py:127` — 1.0 SP (Baixa)
- `DT-42` else desnecessário após return em `app/helpers/date_helper.py:15` — 0.5 SP (Baixa)

**Semana 6** — 6.0 SP

- `DT-28` Função com complexidade ciclomática alta em `app/everything.py:40` — 3.0 SP (Baixa)
- `DT-29` Função com complexidade ciclomática alta em `app/everything.py:153` — 3.0 SP (Baixa)

### O que fica para depois — 60 débitos, 134.0 SP

Não cabem nas 6 semanas antes da saída do desenvolvedor que escreveu 90% do código. Ficam explicitamente adiados, não esquecidos:

- `DT-30` Função com complexidade ciclomática alta em `app/everything.py:196` — 3.0 SP, prioridade Baixa
- `DT-31` Função com complexidade ciclomática alta em `app/everything.py:211` — 3.0 SP, prioridade Baixa
- `DT-34` Captura de exceção genérica demais em `app/services/billing_service.py:77` — 1.0 SP, prioridade Baixa
- `DT-35` Exceção engolida silenciosamente em `app/services/billing_service.py:77` — 1.0 SP, prioridade Baixa
- `DT-36` Redefining name 'dry_run' from outer scope (line 108) em `sync_data.py:18` — 1.0 SP, prioridade Baixa
- `DT-37` Captura de exceção genérica demais em `sync_data.py:25` — 1.0 SP, prioridade Baixa
- `DT-38` Captura de exceção genérica demais em `sync_data.py:72` — 1.0 SP, prioridade Baixa
- `DT-39` Exceção engolida silenciosamente em `sync_data.py:72` — 1.0 SP, prioridade Baixa
- `DT-40` Redefining name 'dry_run' from outer scope (line 108) em `sync_data.py:77` — 1.0 SP, prioridade Baixa
- `DT-41` Captura de exceção genérica demais em `sync_data.py:85` — 1.0 SP, prioridade Baixa
- `DT-43` else desnecessário após return em `app/helpers/date_helper.py:65` — 0.5 SP, prioridade Baixa
- `DT-44` else desnecessário após return em `app/helpers/date_helper.py:68` — 0.5 SP, prioridade Baixa
- `DT-45` else desnecessário após return em `app/helpers/date_helper.py:74` — 0.5 SP, prioridade Baixa
- `DT-46` else desnecessário após return em `app/models/billing_category.py:22` — 0.5 SP, prioridade Baixa
- `DT-47` else desnecessário após return em `app/models/billing_category.py:29` — 0.5 SP, prioridade Baixa
- _(+45 débitos de prioridade menor)_

