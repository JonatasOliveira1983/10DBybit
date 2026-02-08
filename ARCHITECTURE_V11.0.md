# 1CRYPTEN SPACE - Blueprint & System Architecture (V11.0 Smart Stop-Loss Edition) 🎯🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE V11.0. O sistema evolui para o **Smart Stop-Loss Protocol** com gestão dinâmica de risco em 4 fases.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`). Interface **V11.0** com badges de fase SL e trackers de mega ciclo.
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência. Versão **V11.0**, operando na porta **8080**.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real via Radar Elite (88 pares monitorados).

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Captain Agent (`captain.py`)**: Orquestrador tático 100% autônomo. Gerencia até dois trades simultâneos (10% + 10%).
- **Signal Generator (`signal_generator.py`)**: Motor de inteligência V10.0. Utiliza RSI, CVD e tendência 1H para gerar sinais de alta precisão.

### 🔌 Services (services/)
- **BybitREST (V5.0)**: Motor de execução com suporte a múltiplas ordens e processamento de PnL fechado.
- **FirebaseService**: Gerencia o estado persistente de `slots_ativos` e o histórico de trades.
- **BankrollManager**: Gestor de banca com **Micro-Margin Accessibility** (Piso mínimo de $1.0 para margem).
- **VaultService**: Orquestrador de ciclos de 10 trades + **Mega Ciclo** de 100 trades.
- **ExecutionProtocol (V11.0)**: **Smart Stop-Loss Protocol** com 4 fases de proteção dinâmica.

---

## 3. Smart Stop-Loss Protocol V11.0 💎

### 🎯 4 FASES DE PROTEÇÃO

| Fase | Gatilho | Stop-Loss | Ícone |
|------|---------|-----------|-------|
| **SAFE** | ROI < 30% | -50% ROI (entrada) | 🔴 |
| **RISK_ZERO** | ROI ≥ 30% | 0% ROI (entry price) | 🛡️ |
| **PROFIT_LOCK** | ROI ≥ 100% + Gás CONTRA | 80% do lucro | 🟡 |
| **MEGA_PULSE** | ROI ≥ 100% + Gás OK | Trailing (ROI - 20%) | 💎 |

### 🏎️ VERIFICAÇÃO DE GÁS (CVD)
- **Long**: CVD > 5000 = Gás favorável → MEGA_PULSE ativo
- **Short**: CVD < -5000 = Gás favorável → MEGA_PULSE ativo
- Gás desfavorável → Trava lucro em 80% (PROFIT_LOCK)

---

## 4. Sistema de Contadores 📊

### 📈 CICLO 1/10 (WIN_ROI_THRESHOLD)
- Apenas trades com **ROI ≥ 100%** contam como vitória
- Reset automático de ativos bloqueados a cada 10 vitórias
- Recalibração de margem (Compound) ao completar

### 💎 MEGA CICLO 1/100
- Contador acumulativo de trades com ROI ≥ 100%
- Tracker visual nas páginas RADAR e VAULT
- Barra de progresso roxa com gradiente

---

## 5. Fluxos de Dados e Execução 🔄

### A. Geração de Radar
`BybitWS` ➡️ `SignalGenerator` ➡️ `RTDB` ➡️ `UI`

### B. Execução Autônoma (Step-by-Step)
1. `SignalGenerator` detecta sinal Elite (Score > 90).
2. `Captain` verifica slots disponíveis (`bankroll.can_open_new_slot`).
3. `Bankroll` aloca margem (10% do total, min $1.0).
4. `ExecutionProtocol` envia ordens com SL (-50% ROI) e TP (100% ROI).
5. Smart SL monitora ROI e ajusta SL dinamicamente conforme as fases.
6. `VaultService` registra o trade nos ciclos 1/10 e 1/100.

### C. Smart SL Lifecycle
```
[ENTRY] → SAFE (SL=-50%) → RISK_ZERO (SL=0%) → PROFIT_LOCK/MEGA_PULSE (SL=80%+)
                ↓                 ↓                        ↓
            ROI<30%          ROI≥30%                  ROI≥100%
```

---

## 6. Configuração Inicial 💰

| Parâmetro | Valor |
|-----------|-------|
| Banca Inicial | $20.00 |
| Margem por Slot | 10% = $2.00 |
| Slots Máximos | 2 |
| WIN_ROI_THRESHOLD | 100.0% |
| Alavancagem | 50x |

---
*Versão do Documento: 11.0 | Smart Stop-Loss Protocol*
