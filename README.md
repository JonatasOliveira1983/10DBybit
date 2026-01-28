# 1CRYPTEN Space V4.1: Master System Report 🚀

Este relatório detalha a arquitetura, a lógica operacional e o estado atual da Nave 1CRYPTEN, consolidando o conceito Sniper estabelecido e as atualizações de soberania com o OpenRouter e resiliência Dual Heartbeat.

---

## 1. Conceito e Visão 🎯
O 1CRYPTEN foi concebido como um Agente de Trading Autônomo e Inteligente. Diferente de bots tradicionais baseados apenas em indicadores matemáticos (RSI, MACD), o 1CRYPTEN utiliza uma **Hierarquia de IA (DeepSeek, GLM, Gemini)** para validar o contexto do mercado antes de cada disparo.

**Missão:** Identificar picos de volume e anomalias de fluxo (CVD) nos ativos de maior liquidez e executar trades curtos e precisos, protegendo o capital através de uma gestão de risco progressiva.

---

## 2. Arquitetura do "Nerve Center" 🧠
O sistema opera como um ecossistema de micro-agentes especializados:

- **Captain Agent:** O comandante. Responsável por monitorar os sinais do Radar e tomar a decisão final de compra ou venda. Ele coordena o tamanho da mão e a entrada na Bybit.
- **Guardian Agent:** O escudo. Monitora a saúde da API e a latência. Sua função crítica é o **Breakeven Automático**: assim que um trade atinge o lucro alvo inicial, ele move o Stop Loss para o preço de entrada, garantindo o "Risco Zero".
- **Signal Generator (Radar):** O olheiro. Escaneia constantemente os ativos da Bybit (otimizado para Top 30), filtrando os melhores candidatos baseados em algoritmos proprietários de CVD (Cumulative Volume Delta).
- **AI Service:** O cérebro analítico. Orquestra a comunicação com modelos de linguagem de ponta via OpenRouter (DeepSeek V3).
- **Bankroll Manager:** O tesoureiro. Controla a exposição máxima (20% da banca) e o limite de slots (4 iniciais, expansíveis até 10 conforme os trades ficam em Risco Zero).

---

## 3. Integração Bybit & Estabilidade v4.1 🛰️

A Nave passou por uma reengenharia de estabilidade para suportar alta volatilidade:

- **Liquid-Proof Safety:** Implementação de ordens atômicas com Stop-Loss (SL) físico obrigatório na exchange. Se o sistema falhar, o SL de 2% (segurança) já está na Bybit.
- **Dual Heartbeat Resilience (v4.1.4):** 
    - **Canal Primário:** Firebase RTDB (Baixa latência).
    - **Canal Secundário:** REST API Telemetry. A interface agora usa chamadas bem-sucedidas de dados como prova de vida, eliminando avisos falsos de "Offline" durante instabilidade de rede.
- **WebSocket Slicing:** Monitoramento focado nos 30 pares de maior liquidez para evitar congestionamento e `ping/pong timeouts`.

---

## 4. Estado Atual (Snapshot V4.1 ready) ✅

- **Motor AI:** Integrado OpenRouter com DeepSeek V3 (Soberano).
- **Resiliência:** Sistema de retries e timeouts em todas as operações críticas de banco de dados.
- **UI Premium:** Interface com três níveis de conectividade: **ONLINE** (Verde), **LAG** (Amarelo - REST Only) e **OFFLINE** (Vermelho - Total).
- **Sincronização:** Sincronia automática de slots com a exchange no boot, recuperando posições após reinícios.

---

## 5. Sugestões de Evolução (Roadmap) 🚀

- **A. Refinamento de ML:** Backtesting vivo estuda trades fechados e ajusta pesos de sinais.
- **B. NewsHunter:** Scanner de menções em redes sociais para validar sinais de volume com notícias em tempo real.
- **C. App/Push:** Notificações via Telegram para cada "Risco Zero" atingido pelo Guardian.
- **D. Arbitragem:** Expansão para Binance/OKX utilizando o mesmo motor de decisão.

---

## Como Iniciar 🛠️

1. **Pré-requisitos:** Python 3.10+, `serviceAccountKey.json` e `.env` configurado.
2. **Boot:** 
   ```powershell
   cd 1CRYPTEN_SPACE_V4.0/backend
   python main.py
   ```
3. **Interface:** Acesse `http://localhost:5001` no seu navegador.

---
**Operação: 10D - Deep Space - V4.1.4 Calibrated.**
