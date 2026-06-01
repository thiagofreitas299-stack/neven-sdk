# NEVEN — MONETIZATION STRATEGY
> Como faturar desde o Dia 0

## ANÁLISE: Open Source + Comercial (Open Core)

### Por que Open Core é o modelo certo para NEVEN

| Modelo | Prós | Contras |
|--------|------|---------|
| 100% proprietário | Controle total | Ninguém adota, sem comunidade |
| 100% open source | Máxima adoção | Difícil monetizar |
| **Open Core** ← NEVEN | Adoção ampla + receita | Requer separação clara |

Referências de sucesso:
- HashiCorp: Terraform open source → Vault comercial → $6.9B aquisição
- Elastic: Open source → Elastic Cloud → $14B
- Grafana: Open source → Grafana Cloud → $6B

---

## ESTRUTURA DE TIERS — IMEDIATA

### Tier 1: NEVEN SDK Free (Open Source, MIT)
**Já publicado em:** github.com/thiagofreitas299-stack/neven-sdk

O que está incluso:
- SDK Python completo
- Mock server para desenvolvimento
- KAIS identity (local)
- DSE engine (local)
- CLI básico
- 3 exemplos funcionais
- skill.md para integração com agentes

**Objetivo:** Construir comunidade, credibilidade técnica, leads

---

### Tier 2: NEVEN Starter — $99/mês
**Para:** Startups e desenvolvedores individuais

O que adiciona sobre Free:
- API key para até 5 dispositivos físicos reais
- Dashboard web de monitoramento
- Suporte via Discord (resposta em 48h)
- KAIS cloud (identidade persistente na nuvem)
- Analytics básico de uso

**Ativar agora:** Stripe Checkout simples

---

### Tier 3: NEVEN Business — $499/mês
**Para:** Empresas com 5-50 dispositivos

O que adiciona:
- Até 50 dispositivos físicos
- SLA 99.9%
- Suporte dedicado (resposta em 4h)
- Compliance reports (LGPD/GDPR)
- White-label dashboard
- Integração com câmeras SenseTime/ONVIF
- Webhook de eventos em tempo real

---

### Tier 4: NEVEN Enterprise — Negociado ($5k-$50k/mês)
**Para:** Shoppings, aeroportos, prefeituras, redes de varejo

O que adiciona:
- Dispositivos ilimitados
- SLA 99.99% com suporte 24/7
- Deploy on-premise (dentro da infra do cliente)
- Auditoria de compliance completa
- Treinamento da equipe
- Customização de regras DSE
- Integração com sistemas legados

---

## COMO FATURAR HOJE — AÇÕES IMEDIATAS

### Ação 1: Stripe — 2 horas para ter link de pagamento

Já temos credenciais Stripe (.secrets/stripe-api.json).

Produtos a criar:
1. `NEVEN Starter` — $99/mês recorrente
2. `NEVEN Business` — $499/mês recorrente
3. `NEVEN Enterprise` — One-time $500 (depósito de negociação)

Link direto: stripe.com/dashboard → Products → Add product

### Ação 2: neventech.com — Landing com botão de pagamento

Página mínima viável (pode fazer hoje):
- Headline: "The OS for Autonomous Agents in the Physical World"
- 3 bullets de valor
- Pricing table com 3 tiers
- Botão "Start Free" → GitHub
- Botão "Start $99/mo" → Stripe Checkout
- Formulário "Enterprise" → email

### Ação 3: Moltbook — Registrar JARVIS agora

Moltbook é rede social de agentes. Registrar JARVIS lá = primeiros usuários potenciais do NEVEN.
Comando: curl -X POST https://www.moltbook.com/api/v1/agents/register

### Ação 4: Product Hunt — Lançar esta semana

Product Hunt gera 500-2.000 visitantes no dia de lançamento.
Estratégia: "Show PH: NEVEN — Physical Intelligence as a Service"
Melhor dia: Terça ou Quarta
Precisa: conta PH + texto de 200 palavras + screenshot do demo

### Ação 5: HackerNews — "Show HN" esta semana

HN tem os developers que vão usar o SDK.
Título: "Show HN: NEVEN – An open-source runtime that connects AI agents to the physical world"
Precisa: conta HN + post de 3 parágrafos

---

## ANÁLISE ISP — QUAL CANAL MONETIZA MAIS RÁPIDO

| Canal | Tempo até $1 | Esforço | Prioridade |
|-------|-------------|---------|------------|
| Stripe link direto (LinkedIn/email) | 24h | Baixo | 🔴 #1 |
| Product Hunt | 48h | Médio | 🔴 #2 |
| HackerNews | 48h | Baixo | 🔴 #3 |
| Shopping piloto (B2B) | 30 dias | Alto | 🟡 #4 |
| SenseTime parceria | 60+ dias | Alto | 🟡 #5 |

**Conclusão: O caminho mais rápido para o primeiro $99 é Stripe + LinkedIn hoje.**

---

## PITCH B2B PARA PRIMEIROS CLIENTES (shoppings)

Email template para CTOs de shopping:

```
Assunto: Como o Carnaval 2026 nos ensinou a fazer qualquer câmera pensar

Olá [Nome],

No Carnaval 2026, nosso sistema processou 16.5 milhões de pessoas em 
tempo real — sem hardware proprietário, apenas com câmeras existentes.

Hoje lançamos o NEVEN SDK: instale em qualquer câmera ou totem do seu 
shopping e conecte um agente de IA em menos de 10 minutos.

✓ Sem trocar hardware
✓ Segurança determinística (DSE) — nenhum agente "alucina" para abrir porta
✓ Compliance LGPD embutido
✓ Demo gratuita: github.com/thiagofreitas299-stack/neven-sdk

Posso mostrar um piloto de 30 dias gratuito?

Thiago Freitas
Founder, NEVEN
```

---

## PRÓXIMAS 48 HORAS — SEQUÊNCIA EXECUTÁVEL

```
HOJE (Seg 01/06):
□ Thiago: criar produtos no Stripe ($99, $499, enterprise)
□ Jarvis: registrar NEVEN/JARVIS no Moltbook
□ Jarvis: preparar post HackerNews
□ Thiago: aprovar texto HackerNews

AMANHÃ (Ter 02/06):
□ Jarvis: publicar no HackerNews
□ Jarvis: preparar landing page neventech.com
□ Thiago: aprovar landing page
□ Thiago: enviar 5 cold emails para CTOs de shopping

ESSA SEMANA:
□ Product Hunt launch
□ LinkedIn post com demo GIF
□ Primeiro piloto pagante (meta: $99)
```

---

*"Faturar desde o Dia 0 não significa cobrar por tudo. Significa ter um produto pelo qual alguém pagaria hoje."*
*NEVEN tem esse produto. Agora é execução.*
