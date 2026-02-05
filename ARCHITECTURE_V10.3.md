# 1CRYPTEN SPACE - Blueprint & System Architecture (V10.3 ATR Edition) 🎯🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE V10.3. O sistema evoluiu para uma infraestrutura mais robusta, consolidando a **ATR Edition** com melhorias críticas em observabilidade e acessibilidade.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`). Interface otimizada para o **Journey Radar V4.0**, agora com **BTC Display On** por padrão para feedback imediato e integração com o **BTC Command Center**.
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência. Versão consolidada **V10.3**, padronizada na porta **8080**.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real via Radar Elite (88 pares monitorados).

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Super Captain (`captain.py`)**: Único orquestrador tático. Escaneia sinais da Radar Intelligence, verifica protocolos de risco (Cycle Diversification) e executa ordens Sniper.
- **Signal Generator (`signal_generator.py`)**: O motor de inteligência. Integra **Radar Intelligence V10.0** com lógica refinada de RSI, CVD e análise de tendência 1H para entradas de alta probabilidade.
- **AI Service (`ai_service.py`)**: Gerencia o contexto e a personalidade do Capitão, gerando relatórios de raciocínio crítico para cada trade.

### 🔌 Services (services/)
- **BybitREST (V4.3.1)**: Motor de papel (Paper Execution) com **Blindagem de Execução**. Implementa o filtro **Elite 50x+** (88 ativos atuais).
- **BybitWS (V7.2)**: Monitoramento de ultra-velocidade para CVD (Gás), ROI e telemetria. Fornece o cache de **ATR (Average True Range)** para gestão de risco.
- **FirebaseService**: Persistência de logs e histórico. Gerencia o estado dos slots e do Radar via Firestore e RTDB (Pulse).
- **BankrollManager**: Gestor de banca com **Strict Single Sniper Rule** e **Stop-Loss Dinâmico baseado em ATR**.
- **VaultService**: Orquestrador de ciclos de 10 trades com auto-compound e bloqueio de ativos por ciclo.

---

## 3. Protocolo V10.3 ATR Edition 💎

### 🩹 INFRASTRUCTURE & ACCESSIBILITY
- **Standardized Port (8080)**: Unificação total do ecossistema na porta 8080 para evitar conflitos e simplificar o acesso via `127.0.0.1:8080`.
- **SPA Deep Linking**: Implementação de redirecionamentos inteligentes no backend para as rotas hash (`/radar`, `/vault`, `/logs`).
- **Radar Default Visibility**: Ativação automática de sinais BTC no Radar para garantir que a interface nunca pareça inativa durante períodos de baixa volatilidade em altcoins.

### 🛡️ DYNAMIC RISK MANAGEMENT (ATR-Aware)
- **ATR Initial Stop-Loss**: Stop-loss dinâmico calculado como `1.5 * ATR`, com limites seguros entre 0.7% e 2.0%.
- **Relaxed Trailing Ladder**: Escada de proteção otimizada para capturar movimentos maiores (Fôlego Sniper):
    - **Entry Stop**: -20% ROI aos 30% de lucro.
    - **Risk-Zero Shield**: +10% ROI travado aos 50% de lucro.
    - **Mega-Pulse**: Trailing de 20% após 100% de lucro.

### 🎯 ADVANCED PATTERN DETECTION
- **Whale Flow Detection**: Monitoramento persistente de baleias (Fluxos > $250k).
- **CVD Momentum (Gás)**: Visualização em tempo real da "força do motor" do mercado.

---

## 4. Fluxos de Dados e Execução 🔄

### A. Geração de Radar
`BybitWS` ➡️ `SignalGenerator` ➡️ `RTDB` (Radar Pulse) ➡️ `UI` (Journey Radar View - Hash: `/#/radar`)

### B. Execução Sniper ATR
1. `SignalGenerator` detecta sinal Elite (Score >= 90).
2. `Captain` valida entrada via `VaultService` (Check de Ciclo).
3. `Bankroll` consulta **ATR** e define Stop-Loss ideal.
4. Ordem aberta via `BybitREST` (Paper V4.3.1).
5. `ExecutionProtocol` aplica Blindagem Dinâmica.

---
*Versão do Documento: 10.3 | Port 8080 Unification & Sniper Governance*
