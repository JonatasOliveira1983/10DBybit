# 1CRYPTEN SPACE - Blueprint & System Architecture (V10.4 Dual Slot Edition) 🎯🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE V10.4. O sistema evoluiu para uma infraestrutura multitarefa, introduzindo o sistema de **Dual Sniper Slots**.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`). Interface **V10.4** com sistema de abas para gestão de múltiplos slots ativos simultaneamente.
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência. Versão **V10.4 (Dual Slot Edition)**, operando na porta **8080**.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real via Radar Elite (88 pares monitorados).

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Super Captain (`captain.py`)**: Orquestrador tático multitarefa. Gerencia a abertura de novos trades mesmo com posições existentes, desde que os protocolos de segurança (Risk-Zero) sejam atendidos.
- **Signal Generator (`signal_generator.py`)**: Motor de inteligência V10.0. Utiliza RSI, CVD e tendência 1H para gerar sinais de alta precisão.
- **AI Service (`ai_service.py`)**: Gera raciocínio crítico individualizado para cada slot ativo.

### 🔌 Services (services/)
- **BybitREST (V4.3.1)**: Motor de execução com suporte a múltiplas ordens simultâneas.
- **BybitWS (V7.2)**: Telemetria de ultra-velocidade para múltiplos ativos.
- **FirebaseService**: Gerencia o estado persistente de `slots_ativos` (Documentos individuais por ID de slot).
- **BankrollManager**: Gestor de banca com **Dual Slot Rule** (20% + 20% = 40% de exposição máxima).
- **VaultService**: Orquestrador de ciclos integrado com gestão de slots.

---

## 3. Protocolo V10.4 Dual Slot 💎

### 🚀 MULTITASKING EVOLUTION
- **Risk-Zero Trigger**: O Slot 2 é liberado automaticamente assim que o Slot 1 atinge o estado de **Risk-Zero** (Stop Loss >= Preço de Entrada).
- **Dual Exposure**: Permite exposição de até 40% da banca configurada (20% por slot), otimizando o uso do capital em mercados de alta volatilidade.
- **Tabbed Dashboard**: Interface intuitiva que permite alternar entre os slots ativos preservando o contexto do gráfico e telemetria.

### 🛡️ DYNAMIC RISK MANAGEMENT
- **ATR Initial Stop-Loss**: Mantido o protocolo de Stop dinâmico (`1.5 * ATR`).
- **Independent Trailing**: Cada slot possui sua própria escada de proteção e trailing profit independente.
- **Safety Lock**: O sistema impede a abertura de um terceiro slot, mantendo o foco em qualidade e preservação de capital.

---

## 4. Fluxos de Dados e Execução 🔄

### A. Geração de Radar
`BybitWS` ➡️ `SignalGenerator` ➡️ `RTDB` (Radar Pulse) ➡️ `UI` (Radar V10.4)

### B. Execução Dual Sniper
1. `SignalGenerator` detecta sinal Elite.
2. `Captain` verifica slots disponíveis.
3. Se `Slot 1` ativo E `Risk-Zero` == True, permite `Slot 2`.
4. `Bankroll` aloca margem específica para o slot selecionado.
5. `ExecutionProtocol` monitora ambos os slots de forma independente.

### ⚡ Stability & Result Persistence (V10.4.1)
- **Result Fix**: Resolved variable name collision in `VaultService` preventing trade registration.
- **History Sync**: Enabled full trade data persistence for both PAPER and REAL modes.
- **Robust SL**: Added enhanced telemetry and error handling for exchange-side Stop Loss updates.

---
*Versão do Documento: 10.4.1 | Dual Slot Stability & Persistence Update*
