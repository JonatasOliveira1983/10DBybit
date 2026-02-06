# 1CRYPTEN SPACE - Blueprint & System Architecture (V10.6.3 Autonomous Edition) 🎯🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE V10.6.3. O sistema evolui para o **Autonomous Dual Sniper**, eliminando a necessidade de intervenção manual.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`). Interface **V10.6.3 Autonomous** com sincronização híbrida (RTDB + REST Fallback).
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência. Versão **V10.6.3**, operando na porta **8080**.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real via Radar Elite (85-88 pares monitorados).

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Captain Agent (`captain.py`)**: Orquestrador tático 100% autônomo. Gerencia a abertura de até dois trades simultâneos (10% + 10%) sem Master Toggle.
- **Signal Generator (`signal_generator.py`)**: Motor de inteligência V10.0. Utiliza RSI, CVD e tendência 1H para gerar sinais de alta precisão.

### 🔌 Services (services/)
- **BybitREST (V5.0)**: Motor de execução com suporte a múltiplas ordens e processamento de PnL fechado.
- **FirebaseService**: Gerencia o estado persistente de `slots_ativos` e o histórico de trades com paginação otimizada para Floats.
- **BankrollManager**: Gestor de banca com **Micro-Margin Accessibility** (Piso mínimo de $1.0 para margem, permitindo bancas de $20 obedecerem a regra de 10%).
- **VaultService**: Orquestrador de ciclos de 10 trades. Automatiza o Compound e o reset de ativos após a conclusão de cada ciclo.

---

## 3. Protocolo V10.6 Autonomous Dual Slot 💎

### 🤖 TOTAL AUTONOMY
- **No Master Toggle**: O sistema assume o controle operacional contínuo. Não há mais botão de Pausa/Liberação na UI, garantindo que boas oportunidades não sejam perdidas por latência humana.
- **Automatic Recalibration**: O sistema recalcula o valor das entradas (Compound) e limpa a lista de exclusão de ativos automaticamente a cada 10 trades concluídos.

### 📈 MARGIN ACCESSIBILITY
- **Low-Balance Scaling**: O piso de margem operacional foi reduzido de $4.0 para **$1.0**. Isso permite que o sistema escale bancas pequenas com precisão matemática (ex: $2.0 para uma banca de $20).

### 🔄 HYBRID SYNCHRONIZATION
- **Redundancy**: O sistema utiliza RTDB para atualizações de milissegundos e REST API como fallback para garantir que o Dashboard e o Vault mostrem sempre a mesma verdade.
- **Unified Progress Source**: A fonte da verdade para o progresso do ciclo (ex: 2/10) é exclusivamente a lista `used_symbols_in_cycle` no Firestore.

---

## 4. Fluxos de Dados e Execução 🔄

### A. Geração de Radar
`BybitWS` ➡️ `SignalGenerator` ➡️ `RTDB` ➡️ `UI`

### B. Execução Autônoma (Step-by-Step)
1. `SignalGenerator` detecta sinal Elite (Score > 90).
2. `Captain` verifica slots disponíveis (`bankroll.can_open_new_slot`).
3. `Bankroll` aloca margem (10% do total ou banca configurada, min $1.0).
4. `ExecutionProtocol` envia ordens com SL (1.5 * ATR) e TP fixo à exchange.
5. `VaultService` registra o trade no ciclo e dispara recalibragem se trade_count % 10 == 0.

---
*Versão do Documento: 10.6.3 | Autonomous & Margin Accessibility Update*
