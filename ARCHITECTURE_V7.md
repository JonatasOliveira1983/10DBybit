# 1CRYPTEN SPACE - Blueprint & System Architecture (V7.0 Sniper Evolution) 🎯🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE V7.0. O sistema foi simplificado para o protocolo de **Ordem Única Sniper**, otimizando a captura de lucros exponenciais.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`). Layout otimizado para o "Mega Card Sniper" que ocupa todo o espaço lateral e destaca execução em tempo real.
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real.

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Super Captain (`captain.py`)**: Único orquestrador tático. Escaneia sinais, verifica protocolos de risco e executa ordens. No V7.0, ele é responsável por gerenciar a **Regra de Ordem Única**.
- **Signal Generator (`signal_generator.py`)**: Analisador de mercado focado no Radar Elite V7.0, priorizando ativos com momentum extremo de CVD.
- **AI Service (`ai_service.py`)**: Gerencia o contexto e a personalidade do Capitão, agora com integração aprimorada para o acompanhamento dos lucros MEGA_PULSE.

### 🔌 Services (services/)
- **BybitREST**: Implementa o filtro **Elite 50x+** (83+ ativos). Gerencia a execução em modo PAPER ou LIVE e garante a integridade das ordens.
- **BybitWS**: Monitoramento de alta velocidade para cálculo de ROI e PnL dinâmico.
- **FirebaseService**: Persistência em Firestore (Histórico) e RTDB (Pulso). Gerencia o estado dos slots.
- **BankrollManager**: Gestor de banca. Implementa a **Strict Single Sniper Rule** (Apenas 1 trade global por vez).
- **ExecutionProtocol**: O coração da estratégia. Contém o motor de fechamento de ordens e a lógica de **Trailing Profit**.

---

## 3. Protocolo V7.0 Sniper Evolution 💎

### 🎯 SINGLE TRADE PROTOCOL
- **Limite Estrito**: O sistema permite apenas **01 (uma)** posição aberta no total de todos os slots.
- **Foco de Margem**: Concentração total de recursos e atenção do Capitão em uma única oportunidade de alta convicção.
- **Bloqueio de Sinais**: Enquanto houver um trade aberto, o gerador de sinais e o capitão ignoram novas entradas.

### 💎 MEGA_PULSE (Trailing Profit)
- **Ativação**: Iniciado quando o ROI atinge **100%**.
- **Piso de Lucro**: O Stop Loss é movido para **80% de ROI**, garantindo a meta inicial.
- **Perseguição Progressiva**: O SL segue o preço mantendo um "respiro" de **20% de ROI**.
- **Exponencialidade**: Permite que trades vencedores cheguem a 200%, 300% ou mais, fechando apenas quando o momentum reverte e toca o SL móvel.

### 🛡️ BLINDAGEM DE STOP LOSS
- **Check Universal**: Validação em tempo real do preço atual contra o `current_stop` em cada loop de execução.
- **Fechamento Atômico**: Garante que o lucro seja travado no milissegundo em que o Stop (seja ele fixo ou MEGA_PULSE) é atingido.

---

## 4. Fluxos de Dados 🔄

### A. Geração de Sinais
`BybitWS` ➡️ `SignalGenerator` (CVD Elite) ➡️ `RTDB` (Radar) ➡️ `Captain` (Avaliação Convicta)

### B. Gestão da Ordem Única
1. `Captain` recebe sinal ➡️ `Bankroll` verifica se existem `active_positions`.
2. Se `positions == 0`: Abre Sniper.
3. Se `positions > 0`: Descarta sinal.
4. `ExecutionProtocol` monitora posição ➡️ Aplica escada de SL ou MEGA_PULSE.

---
*Versão do Documento: 7.0 | Protocolo de Elite para Captura de Grandes Movimentos*
