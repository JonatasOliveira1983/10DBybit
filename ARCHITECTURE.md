# 🦅 1CRYPTEN V7.1: Sniper Pulse Architecture

Esta arquitetura define o protocolo de **Alta Precisão e Execução Sequencial** para o 1CRYPTEN Sniper. O sistema foi projetado para operar como um "Atirador de Elite", focando em um único alvo por vez com máxima letalidade.

---

## 🏗️ Core Architecture Components

```mermaid
graph TD
    A[Market Data (Bybit)] --> B{BybitWS Service}
    B -->|Real-time CVD / Prices| C[Signal Generator]
    B -->|BTC Pulse Data| D[BTC Command Center]
    
    C -->|Elite Signals Score > 90| E[Captain Agent]
    D -->|Drag Mode & Exhaustion| E
    
    E -->|Single Slot Rule| F[Bankroll Manager]
    F -->|Paper/Real Execute| G[Exchange Interface]
    
    G -->|Trade Result| H[Vault Service]
    H -->|Cycle Reset / History| I[Firebase / UI]
```

### 1. **BTC Pulse & Market Context**
- **Sincronização**: Atualização a cada 60 segundos (V7.1 Sniper Pulse).
- **Drag Mode**: Ativado quando a variação do BTC em 1h ultrapassa 1.2% ou o CVD extrapola $2.5M.
- **Dynamic Exhaustion**: Nível de exaustão calculado progressivamente baseado no fluxo de ordens (BTC CVD) e volatilidade. $5M CVD = 100% Exaustão.

### 2. **Signal Generator (The Radar)**
- **Scanning**: Monitoramento constante de 200 pares a cada 5 segundos.
- **Elite Filter**: Apenas sinais com Score real (baseado em CVD, Momentum e ATR) acima de 90 são encaminhados ao Capitão.
- **Single Slot Logic**: Se já existe uma operação aberta, o gerador entra em modo "Standby" para economizar latência.

### 3. **Captain Agent (The Sniper)**
- **One Shot, One Opportunity**: O sistema gerencia apenas um slot ativo por vez.
- **Sequential Execution**: Assim que uma ordem é fechada (TP/SL), o Capitão reavalia o "Best of the Best" no radar em menos de 3 segundos para reentrada imediata.
- **Decision Engine**: Cruzamento de dados macro (BTC Pulse) com sinais locais para evitar entradas durante exaustão extrema de mercado.

### 4. **Execution Protocol**
- **Single Slot Sniper**: Alocação de 20% da banca por trade.
- **Targets**: Foco em ROI de 100% (Sniper Hit).
- **Risk Control**: Stop Loss dinâmico gerenciado pelo protocolo de proteção Guardian.

---

## 🔄 Lifecycle of a Sniper Pulse Trade

1.  **Radar Phase**: Signal Generator identifica um ativo com Score > 90.
2.  **Context Check**: Capitão valida se o BTC não está em exaustão (>80%) ou contra a tendência.
3.  **Deployment**: Posição aberta com alavancagem 50x (Sniper Shot).
4.  **Monitoring**: Guardian Agent ajusta o SL em tempo real no Dashboard.
5.  **Hit/Reset**: Ordem fechada. Lucro enviado ao Vault.
6.  **Quick Pulse**: O ciclo reinicia instantaneamente, buscando o próximo alvo no radar.

---

## 🛠️ Tech Stack
- **Backend**: FastAPI (Python 3.10+)
- **Database**: Firebase Firestore (History) & RTDB (Real-time Telemetry)
- **Exchange**: Bybit V5 API (Websockets + REST)
- **Frontend**: React (Mobile-First Responsiveness)
- **AI Engine**: Gemini 2.0 Flash (Command & Reasoning)

---
*V7.1 Architecture - Developed for JonatasOliveira1983/10DBybit*
