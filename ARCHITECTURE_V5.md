# 1CRYPTEN SPACE - Blueprint & System Architecture (V5.2.4) 🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE. Utilize este contexto para planejar melhorias em lógica de IA, otimização de execução e interface.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`), focado em baixa latência e visualização premium.
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real.

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Captain (`captain.py`)**: Orquestrador tático. Escaneia sinais, verifica protocolos de risco (Bankroll) e cooldowns. Único agente autorizado a abrir ordens.
- **Guardian (`guardian.py`)**: Zelador das posições. Monitora lucros em tempo real, move o Stop Loss (Adaptive SL) e executa o fechamento forçado em Flash Zone.
- **Signal Generator (`signal_generator.py`)**: Analisador de mercado. Transforma dados brutos de CVD (Cumulative Volume Delta) em scores de oportunidade (75-99).
- **AI Service (`ai_service.py`)**: Ponte para modelos LLM (Gemini 1.5 Pro/Flash, OpenAI, OpenRouter). Gerencia o contexto e a personalidade do Capitão.

### 🔌 Services (services/)
- **BybitREST**: Abstração da API Bybit. Inclui o **Motor de Simulação (PAPER)** que replica o comportamento da exchange sem risco real.
- **BybitWS**: Gerencia conexões WebSocket para Tickers e Klines, alimentando o radar de CVD.
- **FirebaseService**: CRUD unificado para Firestore (Histórico, Slots) e RTDB (Pulso de Mercado).
- **BankrollManager**: Gestor de banca e risco. Garante limite de slots (máx 4 ativos) e gerencia os 10 "Squadron Slots".
- **VaultService**: Gestor do Ciclo Sniper de 20 trades. Calcula PnL acumulado e gerencia retiradas.
- **ExecutionProtocol**: O motor matemático. Define as regras de trailing, alvos de ROI e distâncias de SL/TP por slot.

---

## 3. Fluxos de Dados Críticos 🔄

### A. Geração de Sinais
`BybitWS` (Fluxo Ordens) ➡️ `SignalGenerator` (Cálculo CVD) ➡️ `Firestore` (journey_signals)

### B. Ciclo de Vida do Trade (Sniper/Surf)
1. `Captain` detecta sinal ➡️ `Bankroll` valida slots ➡️ `BybitREST` envia Ordem.
2. `Firestore` grava Slot Ativo ➡️ `Guardian` inicia monitoramento.
3. `Guardian` avalia ROI ➡️ `ExecutionProtocol` solicita novo SL ➡️ `BybitREST` atualiza Exchange.

### C. Sincronização e Vault
1. Ordem fechada (TP/SL/Manual) ➡️ `BybitREST` limpa cache ➡️ `Firestore` registra no Histórico.
2. `VaultService` detecta fechamento ➡️ Valida ROI >= 80% ➡️ Incrementa contador de Wins e Lucro do Ciclo.
3. `Initial Sync` (Startup): O sistema varre o histórico do dia ao iniciar para corrigir qualquer discrepância de valores.

---

## 4. Estrutura de Páginas (Frontend) 🖥️

- **Dashboard**: "Torre de Controle" com lucro total, status dos agentes e pulso de mercado.
- **Slots**: Interface tática visualizando ROI dinâmico e botões de pânico por par.
- **Radar**: Lista de sinais detectados.
- **History**: Registro forense de todos os trades realizados.
- **Vault**: Dashboard do progresso para o saque de 20 trades.
- **Settings**: Painel de controle de chaves, modo de operação e status técnico.

---

## 5. Protocolos Estratégicos 📜

### 🎯 SNIPER Adaptive SL
- Alvo: 100% ROI.
- Trailing: SL sobe em ROI 15%, 30%, 50% e 70%.
- **Flash Zone**: Ao atingir 80% ROI, o modo Overclock (200ms) trava o lucro para garantir o win.

### 🏄 SURF Trailing
- Alvo: Infinito.
- Trailing: Escada de 8 níveis baseada em máximas atingidas.
- **Risk Zero**: Ativado automaticamente ao atingir 10% ROI.

### ⏱️ Cooldown Anti-Whipsaw
- Pausa técnica de 5 minutos após qualquer trade fechado por Stop Loss para evitar overtrading em mercados sem tendência.

---
*Versão do Documento: 5.2.3 | Contexto para Gemini AI*
