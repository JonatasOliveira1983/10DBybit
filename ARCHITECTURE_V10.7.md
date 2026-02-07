# 1CRYPTEN SPACE - Blueprint & System Architecture (V10.7 Synchronized Edition) 🎯🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE V10.7. O sistema evolui com **Full Firebase Synchronization** entre Firestore e Realtime Database.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`). Interface **V10.7** com sincronização híbrida (RTDB + Firestore + REST Fallback).
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência. Versão **V10.7**, operando na porta **8080**.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real via Radar Elite (85-88 pares monitorados).

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Captain Agent (`captain.py`)**: Orquestrador tático 100% autônomo. Gerencia a abertura de até dois trades simultâneos (10% + 10%) sem Master Toggle.
- **Signal Generator (`signal_generator.py`)**: Motor de inteligência V10.0. Utiliza RSI, CVD e tendência 1H para gerar sinais de alta precisão.

### 🔌 Services (services/)
- **BybitREST (V5.0)**: Motor de execução com suporte a múltiplas ordens e processamento de PnL fechado.
- **FirebaseService (V10.6.6)**: Gerencia o estado persistente com **Resilience Features**:
  - Exponential Backoff (15s → 30s → 60s) para reconexões
  - Health Check automático após 5 falhas consecutivas
  - Contador de falhas com reset automático
- **BankrollManager**: Gestor de banca com **Micro-Margin Accessibility** (Piso mínimo de $1.0 para margem).
- **VaultService**: Orquestrador de ciclos de 10 trades com compounding automático.

---

## 3. Configuração de Banca 💰

| Parâmetro | Valor |
|-----------|-------|
| **Banca Inicial** | $20.00 |
| **Margem por Slot** | 10% = $2.00 |
| **Slots Disponíveis** | 2 (simultâneos) |
| **Ciclo** | 10 trades |
| **Piso Mínimo** | $1.00 |

---

## 4. Protocolo V10.7 Full Sync 🔄

### 🔥 REALTIME DATABASE (RTDB)
Nós sincronizados em tempo real:
```
├── banca_status      # Saldo, slots, ciclo
├── slots             # Status dos 2 slots
├── live_slots        # Espelho para UI
├── system_state      # Estado atual (SCANNING/TRADING)
├── system_pulse      # Heartbeat do sistema
├── btc_command_center # BTC Drag Mode
├── ws_command_tower  # Latência WebSocket
├── market_radar      # Sinais do Radar
├── system_cooldowns  # Cooldowns de símbolos
└── chat_history      # Histórico do Captain AI
```

### ☁️ FIRESTORE
Coleções persistentes:
```
├── banca_status      # Documento de status único
├── slots_ativos      # 2 documentos (slot 1 e 2)
├── vault_management  # current_cycle
├── journey_signals   # Histórico de sinais
└── trade_history     # Histórico de trades
```

### 🤖 AUTONOMIA TOTAL
- **No Master Toggle**: Controle operacional contínuo sem intervenção humana.
- **Auto-Recalibration**: Compound e reset de ativos a cada 10 trades.

---

## 5. Fluxos de Dados e Execução 🔄

### A. Geração de Radar
`BybitWS` ➡️ `SignalGenerator` ➡️ `RTDB.market_radar` ➡️ `UI`

### B. Execução Autônoma (Step-by-Step)
1. `SignalGenerator` detecta sinal Elite (Score > 90).
2. `Captain` verifica slots disponíveis (`bankroll.can_open_new_slot`).
3. `Bankroll` aloca margem (10% do total, min $1.0).
4. `ExecutionProtocol` envia ordens com SL/TP à exchange.
5. `VaultService` registra o trade e dispara recalibragem se trade_count % 10 == 0.

### C. Sincronização de Estado
`Backend` ➡️ `Firestore` + `RTDB` ➡️ `UI (todas as 3 páginas)`

---

## 6. Script de Limpeza V10.7 🧹

O script `force_clear_all.py` sincroniza completamente o sistema:

```bash
python force_clear_all.py
```

**Ações executadas:**
- Reset de slots (1-2) → LIVRE
- Reset de Vault → Ciclo 1 (0/10)
- Banca → $20.00
- Limpa sinais e histórico
- Sincroniza **todos** os nós do RTDB
- Reset do paper_storage.json local

---

## 7. Variáveis de Ambiente (Produção) 🔐

| Variável | Descrição |
|----------|-----------|
| `FIREBASE_CREDENTIALS` | JSON completo da service account |
| `FIREBASE_DATABASE_URL` | `https://projeto-teste-firestore-3b00e-default-rtdb.europe-west1.firebasedatabase.app/` |
| `BYBIT_API_KEY` | Chave da API Bybit |
| `BYBIT_API_SECRET` | Secret da API Bybit |

---

*Versão do Documento: 10.7 | Full Firebase Synchronization Edition*
