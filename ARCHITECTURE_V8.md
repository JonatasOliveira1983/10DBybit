# 1CRYPTEN SPACE - Blueprint & System Architecture (V9.0 Cycle Compound) 🎯🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE V9.0. O sistema foi evoluído para o protocolo de **Cycle Diversification & Compound**, com ciclos de 10 trades obrigatoriamente diversificados e recálculo automático de banca.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`). Layout otimizado para o "Mega Card Sniper" com a nova **Visual Precision Engine** para posicionamento dinâmico de SL/TP no gráfico.
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real.

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Super Captain (`captain.py`)**: Único orquestrador tático. Escaneia sinais, verifica protocolos de risco e executa ordens. No V8.0, ele gerencia a **Regra de Diversificação Sequencial**.
- **Signal Generator (`signal_generator.py`)**: Analisador de mercado focado no Radar Elite V7.0, priorizando ativos com momentum extremo de CVD. V8.0: Filtra último par operado.
- **AI Service (`ai_service.py`)**: Gerencia o contexto e a personalidade do Capitão, agora com integração aprimorada para o acompanhamento dos lucros MEGA_PULSE.

### 🔌 Services (services/)
- **BybitREST**: Implementa o filtro **Elite 50x+** (83+ ativos). Gerencia a execução em modo PAPER ou LIVE e garante a integridade das ordens.
- **BybitWS**: Monitoramento de alta velocidade para cálculo de ROI e PnL dinâmico.
- **FirebaseService**: Persistência em Firestore (Histórico) e RTDB (Pulso). Gerencia o estado dos slots.
- **BankrollManager**: Gestor de banca. Implementa a **Strict Single Sniper Rule** (Apenas 1 trade global por vez) com margem de 20%.
- **ExecutionProtocol**: O coração da estratégia. Contém o motor de fechamento de ordens e a lógica de **Trailing Profit**.

---

## 3. Protocolo V8.0 Sequential Diversification 💎

### 🎯 SINGLE TRADE PROTOCOL (Evolution V8.0)
- **Limite Absoluto**: O sistema opera estritamente com **01 (uma)** posição aberta por vez no **Slot 1**.
- **Remoção do SURF**: Todas as lógicas de "Surf" foram eliminadas em favor da precisão máxima do modo Sniper.
- **Foco de Margem**: 20% da banca alocada em cada trade Sniper.
- **Autorização de Voo**: O Capitão busca e executa ordens continuamente enquanto o `Master Toggle` estiver ATIVADO. Se desativado, o sistema entra em standby após o fechamento da posição atual.

### 💎 MEGA_PULSE (Trailing Profit)
- **Ativação**: Iniciado quando o ROI atinge **100%**.
- **Piso de Lucro**: O Stop Loss é movido para **80% de ROI**, garantindo a meta inicial.
- **Perseguição Progressiva**: O SL segue o preço mantendo um "respiro" de **20% de ROI**.
- **Exponencialidade**: Permite que trades vencedores cheguem a 200%, 300% ou mais.

### 🛡️ BLINDAGEM DE STOP LOSS
- **Check Universal**: Validação em tempo real do preço atual contra o `current_stop` em cada loop de execução.
- **Fechamento Atômico**: Garante que o lucro seja travado no milissegundo em que o Stop é atingido.

---

## 4. Fluxos de Dados 🔄

### A. Geração de Sinais
`BybitWS` ➡️ `SignalGenerator` (CVD Elite + Filtro V8.0) ➡️ `RTDB` (Radar) ➡️ `Captain` (Avaliação Convicta)

### B. Gestão da Ordem Única + Diversificação
1. `Captain` recebe sinal ➡️ `Bankroll` verifica se existem `active_positions`.
2. Se `positions == 0`: Verifica se `sinal.symbol != last_traded_symbol`.
3. Se diferente: Abre Sniper. Se igual: Descarta e busca outro par.
4. Se `positions > 0`: Descarta sinal.
5. `ExecutionProtocol` monitora posição ➡️ Aplica escada de SL ou MEGA_PULSE.
6. Ao fechar: Registra `symbol` em `last_traded_symbol`.

---
*Versão do Documento: 8.1 | Protocolo de Precisão Visual e Diversificação Sequencial*
