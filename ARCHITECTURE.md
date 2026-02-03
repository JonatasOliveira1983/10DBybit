# 🦅 1CRYPTEN V7.2: Sniper Pulse Elite Architecture

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

### 1. **BTC Pulse & Market Context (V7.2)**
- **Sincronização**: Atualização a cada 60 segundos (Sniper Pulse Sync).
- **Drag Mode**: Ativado quando a variação do BTC em 1h ultrapassa 1.2% ou o CVD extrapola $2.5M.
- **Dynamic Exhaustion**: Nível de exaustão calculado progressivamente.

### 2. **Signal Generator V7.2 (Multi-Indicator Radar)**
- **Event-Driven**: Monitoramento "Zero Latency" com fila de eventos.
- **Elite Filter**: 
    - **CVD Weight (70%)**: Fluxo financeiro real.
    - **RSI Alignment (30%)**: Filtro de reversão/exaustão local.
- **RSI Block**: Bloqueio de sinais Long se RSI > 80 e Short se RSI < 20.

### 3. **Captain Agent (The Sniper)**
- **Event-Driven Execution**: O Capitão não faz polling. Ele reage a eventos da fila `signal_queue`, eliminando atrasos de ~3s.
- **One Shot, One Opportunity**: O sistema gerencia apenas um slot ativo por vez.
- **Sequential Execution**: Reentrada imediata (<1s) após fechamento de ordem.

### 4. **Execution Protocol (Mega Pulse)**
- **Single Slot Sniper**: Alocação de 20% da banca.
- **Sniper Trailing Target (Profit Maximizer)**: 
    - Ao atingir 100% ROI, a ordem **NÃO** fecha.
    - Ativa modo **MEGA PULSE**: Trava 80% e busca alvos maiores (150%, 200%...).
    - Stop Loss Adaptativo segue o preço com gap de 20% ROI.

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
*V7.2 Architecture - Optimized for JonatasOliveira1983/10DBybit*
