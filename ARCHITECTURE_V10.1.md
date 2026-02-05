# 1CRYPTEN SPACE - Blueprint & System Architecture (V10.1 Pulse Edition) 🎯🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE V10.1. O sistema evoluiu para a **Pulse Edition**, unificando estabilidade de infraestrutura com a inteligência do Radar V10.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`). Interface otimizada para o **Journey Radar V4.0**, com visualização de gatilhos institucionais e o widget **BTC Command Center**.
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência. Versão unificada **V10.1**.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real via Radar Elite.

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Super Captain (`captain.py`)**: Único orquestrador tático. Escaneia sinais da Radar Intelligence, verifica protocolos de risco (Cycle Diversification) e executa ordens. **Versão V10.1 Unificada**.
- **Signal Generator (`signal_generator.py`)**: O motor de inteligência. Integra **Radar Intelligence V10.0** com lógica refinada de RSI V10.1 para entradas mais precisas.
- **AI Service (`ai_service.py`)**: Gerencia o contexto e a personalidade do Capitão, traduzindo dados complexos de CVD e padrões em insights compreensíveis ("Raciocínio").

### 🔌 Services (services/)
- **BybitREST**: Implementa o filtro **Elite 50x+** (85+ ativos). Gerencia a execução e integridade das ordens. Inclui correção de `UnboundLocalError` no Bankroll.
- **BybitWS**: Monitoramento de alta velocidade para cálculo de CVD (Gás), ROI e telemetria de gráfico 1H.
- **FirebaseService**: Persistência em Firestore (Histórico) e RTDB (Pulso). Gerencia o estado dos slots e do Radar.
- **BankrollManager**: Gestor de banca. Implementa a **Strict Single Sniper Rule** com margem de 20% e compound por ciclo.
- **VaultService**: Orquestrador de ciclos de 10 trades com diversificação obrigatória (não repete par no mesmo ciclo).

---

## 3. Protocolo V10.1 Pulse Edition 💎

### 🩹 STABILITY & INFRASTRUCTURE
- **Port Auto-Clean**: Script de inicialização (`kill_and_run.bat`) agora limpa agressivamente a porta 8080 para evitar conflitos de bind.
- **Error Shielding**: Tratamento robusto de erros de importação e inicialização de serviços críticos (Bankroll fallback).
- **Unified Version Tagging**: Todo o ecossistema (Logs, API, Agentes) opera sob a tag `V10.1` para consistência de telemetria.

### 🎯 ADVANCED PATTERN DETECTION (V10 Core)
- **Whale Activity (🐋)**: Identifica fluxos de CVD superiores a $250k USD, sinalizando entrada de grandes players.
- **Bull/Bear Traps**: Detecta varreduras de liquidez (sweeps) contra a tendência de 1H, antecipando reversões institucionais.
- **Accumulation Box Exit**: Monitora consolidações e identifica o rompimento preciso para entrada em momentum.

### 🦅 BTC DRAG MODE & EXHAUSTION
- **Drag Boost**: Agressividade ajustada automaticamente se o BTC apresentar variação > 1.2% ou CVD extremo.
- **Exhaustion Engine**: Calcula o nível de exaustão do mercado baseado no volume do BTC, reduzindo o risco em topos/fundos esticados.

### 🛡️ BLINDAGEM E MEGA_PULSE
- **Risk-Zero Shield**: Movimentação automática do Stop Loss para o breakeven e proteção de lucro.
- **MEGA_PULSE (Trailing Profit)**: Persegue o preço após 100% de ROI com um respiro dinâmico, permitindo capturar swings exponenciais.

---

## 4. Fluxos de Dados e Execução 🔄

### A. Geração de Radar
`BybitWS` ➡️ `SignalGenerator` (V10.1 RSI Logic) ➡️ `RTDB` (Radar Pulse) ➡️ `UI` (Journey Radar View)

### B. Execução Sniper Pulse
1. `SignalGenerator` detecta sinal Elite (Score >= 90) validado por **RSI V10.1**.
2. `Captain` recebe sinal ➡️ Verifica se o `Master Toggle` está Ativo.
3. Verifica `VaultService` para garantir que o símbolo não foi operado no ciclo atual.
4. `Bankroll` valida saldo ➡️ Abre ordem Sniper.
5. `ExecutionProtocol` monitora ➡️ Aplica Trailing Profit / Stop Loss.

---
*Versão do Documento: 10.1 | Pulse Edition & Infrastructure Stability*
