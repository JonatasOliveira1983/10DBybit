# 1CRYPTEN SPACE - Blueprint & System Architecture (V6.0 Elite) 🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE. Utilize este contexto para planejar melhorias em lógica de IA, otimização de execução e interface.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`), com suporte a múltiplos temas (Modo Gemini). Acessível via porta **8080**.
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real.

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Super Captain (`captain.py`)**: Único orquestrador tático. Absorveu totalmente o Guardian Agent. Escaneia sinais, verifica protocolos de risco, executa ordens e gerencia posições em um loop centralizado com **Overclock Adaptativo**.
- **Signal Generator (`signal_generator.py`)**: Analisador de mercado. Transforma dados brutos de CVD em scores de oportunidade. Calibrado para o Radar Elite V6.0.
- **AI Service (`ai_service.py`)**: Ponte para modelos LLM. Gerencia o contexto e a personalidade do Capitão.

### 🔌 Services (services/)
- **BybitREST**: Implementa o filtro **Elite 85** (apenas pares com 50x+ leverage). Gerencia o Escudo de Idempotência e registros atômicos.
- **BybitWS**: Monitoramento massivo de 83+ ativos em tempo real para cálculo de CVD e Latência.
- **FirebaseService**: Persistência dupla (Firestore para histórico/logs e RTDB para pulso em tempo real e Radar).
- **BankrollManager**: Gestor de banca. Implementa a regra mandatória de **5% de Risco Fixo** por trade ($5 por slot em banca de $100) e trava de risco global.
- **VaultService**: Gestor de Ciclo V6.0. Agora suporta registro de trades SURF e SNIPER separadamente no vault.
- **V6.0 Blindagem Engine**: Módulo integrado ao BybitREST que executa a normalização de símbolos (`normalize_symbol`) e validação de correspondência exata para evitar precificação errônea (ex: colisão KAS/KSM).

---

## 3. Visual Engine & Temas 🎨

### [V6.0 Elite] - 2026-02-02 (Centralized Command) 🚀
*   **Agent Merger**: Guardian Agent removido; lógica de gestão consolidada no Capitão para evitar conflitos de sincronização.
*   **Elite 85 Scan**: Filtro nativo na Bybit para focar apenas em ativos de alta alavancagem.
*   **Breathing Protocol**: Novo protocolo de respiro para trades SURF (Risk Zero apenas após 30% ROI).
*   **Command Tower UI**: Visualização em tempo real da saúde do WebSocket e latência na ponte de comando.
*   **Total Purge (Phase 2)**: Reset absoluto de Firebase (Signals, Slots, History) + Engine local para boot 100% limpo em novos ciclos.
*   **PnL USD Real-Time Sync**: Sincronização forçada de PnL em dólar no loop do Guardian, garantindo paridade total entre ROI % e saldo visual.
*   **Robust Ticker Mapping (Armor V6.0)**: Validação de precificação por correspondência exata (Exact Match) que previne anomalias de ROI em moedas com nomes similares.
*   **ROI Sanity Guard**: Trava de segurança que limita qualquer variação de ROI a ±5000%, protegendo a UI e os logs de valores espúrios.

---

## 4. Fluxos de Dados Críticos 🔄

### A. Geração de Sinais
`BybitWS` (Fluxo Ordens) ➡️ `SignalGenerator` (Cálculo CVD) ➡️ `RTDB` (market_radar) ➡️ `Firestore` (journey_signals)

### B. Gestão Centralizada (V6.0)
1. `Captain` detecta sinal ➡️ `Bankroll` valida slots e risco ➡️ Executa Ordem.
2. `Captain` monitora ROI em tempo real ➡️ Aplica `ExecutionProtocol` (Adaptive SL).
3. Registro único no Histórico via `Bankroll.sync_slots_with_exchange`.

---

## 5. Protocolos Estratégicos (V6.0) 📜

### 🎯 SNIPER OVERDRIVE 2.0
- **Adaptive Trailing**: SL move-se dinamicamente antes de 100% ROI para proteger ganhos parciais.
- **Chase Logic**: Após 100% ROI, o SL "trava o lucro" e persegue o preço com respiro baseado em ATR.

### 🏄 SURF SHIELD (Breathing)
- **Breathing Zone**: Entre 10-30% ROI, o trade usa um SL largo (3.5x ATR) em vez de travar no breakeven, evitando expulsão prematura por wicks.

### ☢️ TOTAL PURGE SHIELD
- Reset total que elimina arquivos JSON locais e documentos Firebase, prevenindo "Zombie Positions" em novos ciclos.

---
*Versão do Documento: 6.0.0 | Contexto para Almirante & Gemini AI*
