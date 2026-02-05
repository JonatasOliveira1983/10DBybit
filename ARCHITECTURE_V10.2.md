# 1CRYPTEN SPACE - Blueprint & System Architecture (V10.2 ATR Edition) 🎯🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE V10.2. O sistema evoluiu para a **ATR Edition**, introduzindo gestão de risco dinâmica adaptada à volatilidade do mercado.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`). Interface otimizada para o **Journey Radar V4.0**, com visualização de gatilhos institucionais e o widget **BTC Command Center**.
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência. Versão unificada **V10.2**.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real via Radar Elite.

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Super Captain (`captain.py`)**: Único orquestrador tático. Escaneia sinais da Radar Intelligence, verifica protocolos de risco (Cycle Diversification) e executa ordens. **Versão V10.2 Unificada**.
- **Signal Generator (`signal_generator.py`)**: O motor de inteligência. Integra **Radar Intelligence V10.0** com lógica refinada de RSI e análise de tendência 1H para entradas precisas.
- **AI Service (`ai_service.py`)**: Gerencia o contexto e a personalidade do Capitão, traduzindo dados complexos de CVD e padrões em insights compreensíveis ("Raciocínio").

### 🔌 Services (services/)
- **BybitREST**: Implementa o filtro **Elite 50x+** (85+ ativos). Gerencia a execução e integridade das ordens.
- **BybitWS**: Monitoramento de alta velocidade para cálculo de CVD (Gás), ROI e telemetria de gráfico 1H. Fornece o cache de **ATR (Average True Range)** para a gestão de stop-loss.
- **FirebaseService**: Persistência em Firestore (Histórico) e RTDB (Pulso). Gerencia o estado dos slots e do Radar.
- **BankrollManager**: Gestor de banca. Implementa a **Strict Single Sniper Rule** com margem de 20% e agora o **Stop-Loss Dinâmico baseado em ATR**.
- **VaultService**: Orquestrador de ciclos de 10 trades com diversificação obrigatória e compound automático por ciclo.

---

## 3. Protocolo V10.2 ATR Edition 💎

### 🩹 STABILITY & INFRASTRUCTURE
- **Protocolo Scorched Earth**: Script de purificação do sistema (`scorch_earth_v8.py`) que limpa histórico de sinais e trades para novos ciclos de teste.
- **Unified Version Tagging**: Todo o ecossistema (Logs, API, Agentes) opera sob a tag `V10.2`.

### 🛡️ DYNAMIC RISK MANAGEMENT (ATR-Aware)
- **ATR Initial Stop-Loss**: O stop-loss inicial não é mais fixo em 1%. O sistema calcula o stop baseado na volatilidade média do ativo (`1.5 * ATR`), respeitando um piso de 0.7% e um teto de 2.0%. Isso protege contra "wicks" de sniper em ativos voláteis.
- **Relaxed Trailing Ladder**: A escada de proteção foi relaxada para dar "fôlego" ao trade:
    - O trailing só inicia aos **30% de ROI** (movendo stop para -20%).
    - **Risk-Zero Shield** ativa aos **50% de ROI** (travando +10%).
    - **Mega-Pulse Trailing** ativa após os **100% de ROI**, seguindo o preço com gap de 20% de ROI.

### 🎯 ADVANCED PATTERN DETECTION (V10 Core)
- **Whale Activity (🐋)**: Identifica fluxos de CVD superiores a $250k USD.
- **Bull/Bear Traps**: Detecta varreduras de liquidez contra a tendência.
- **Accumulation Box Exit**: Monitora rompimentos de consolidações 1H.

---

## 4. Fluxos de Dados e Execução 🔄

### A. Geração de Radar
`BybitWS` ➡️ `SignalGenerator` ➡️ `RTDB` (Radar Pulse) ➡️ `UI` (Journey Radar View)

### B. Execução Sniper ATR
1. `SignalGenerator` detecta sinal Elite (Score >= 90).
2. `Captain` recebe sinal e valida via `VaultService` (Diversificação).
3. `Bankroll` valida saldo e consulta `BybitWS` para obter o **ATR** do símbolo.
4. Calcula o **Stop Dinâmico** e abre a ordem Sniper.
5. `ExecutionProtocol` monitora e aplica a **Escada Relaxada** de proteção.

---
*Versão do Documento: 10.2 | ATR Edition & Dynamic Risk Governance*
