# 1CRYPTEN SPACE - Blueprint & System Architecture (V10.5 Concurrent Dual Slot Edition) 🎯🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE V10.5. O sistema introduz a evolução para o **Concurrent Dual Sniper**, otimizando a agilidade operacional.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`). Interface **V10.5 Elite** com proteção contra falhas (Defensive UI) e sincronização RTDB otimizada.
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência. Versão **V10.5 (Concurrent Edition)**, operando na porta **8080**.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real via Radar Elite (85-88 pares monitorados).

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Captain Agent (`captain.py`)**: Orquestrador tático de rota dupla. Gerencia a abertura de até dois trades simultâneos, cada um utilizando 10% da banca.
- **Signal Generator (`signal_generator.py`)**: Motor de inteligência V10.0. Utiliza RSI, CVD e tendência 1H para gerar sinais de alta precisão.
- **AI Service (`ai_service.py`)**: Gera raciocínio crítico individualizado para cada slot ativo.

### 🔌 Services (services/)
- **BybitREST (V4.3.1)**: Motor de execução com suporte a múltiplas ordens simultâneas.
- **BybitWS (V7.2)**: Telemetria de ultra-velocidade para múltiplos ativos.
- **FirebaseService**: Gerencia o estado persistente de `slots_ativos` (Documentos individuais por ID de slot).
- **BankrollManager**: Gestor de banca com **Concurrent Dual Slot Rule** (10% + 10% = 20% de exposição máxima total).
- **VaultService**: Orquestrador de ciclos. Registra o resultado de ambos os slots para o contador de 0 a 10 e recálculo de banca.

---

## 3. Protocolo V10.5 Concurrent Dual Slot 💎

### 🚀 PARALLEL EXECUTION EVOLUTION
- **Full Availability**: Diferente da V10.4, o **Slot 2 não exige mais que o Slot 1 esteja em Risk-Zero**. Ambos os slots ficam liberados para o Capitão preencher sempre que estiverem vazios.
- **Optimized Exposure**: Cada slot utiliza **10% da banca**. A exposição máxima total simultânea é de 20%, protegendo o capital enquanto aumenta as chances de captura de sinais.
- **Unified Cycle Counting**: Os resultados de ambos os slots contribuem para o ciclo de 10 disparos. O sistema recalcula o valor da entrada após a conclusão do ciclo.

### 🛡️ DYNAMIC RISK MANAGEMENT
- **ATR Initial Stop-Loss**: Mantido o protocolo de Stop dinâmico baseado na volatilidade real do ativo.
- **Independent SL/TP**: Toda a lógica de Stop Loss e Take Profit desenvolvida anteriormente permanece ativa e independente para cada slot.
- **Master Authorization**: Os slots só podem ser preenchidos se o Capitão (Master Toggle/Vault) estiver liberado para operar.

---

## 4. Estabilidade e Robustez (V10.5 Elite) 🛡️

### 🧊 Defensive Frontend Logic
- **String Blindage**: Implementação de conversão forçada `String()` em todas as operações de formatação (`.replace()`, `.includes()`) para evitar falhas de `TypeError` na UI.
- **Array Validation**: Verificação rigorosa de integridade de dados (`Array.isArray`) antes do processamento de sinais e pares elite.

### 🎨 Unified Branding & Assets
- **Zero Versioning**: Remoção completa de strings de versão internas (v4.x, v10.x) da interface visual para uma experiência "Elite" limpa.
- **Standardized Assets**: Centralização do `logo10D.png` com caminhos relativos para garantir carregamento consistente via PWA/Service Worker.

---

## 4. Fluxos de Dados e Execução 🔄

### A. Geração de Radar
`BybitWS` ➡️ `SignalGenerator` ➡️ `RTDB` (Radar Pulse) ➡️ `UI` (Radar V10.5)

### B. Execução Dual Sniper (Concurrent)
1. `SignalGenerator` detecta sinal Elite (Score > 90).
2. `Captain` verifica slots disponíveis (`bankroll.can_open_new_slot`).
3. Se `Slot 1` OU `Slot 2` estiver vazio, a execução é autorizada.
4. `Bankroll` aloca margem de 10% baseada na banca do ciclo ou balance real.
5. `ExecutionProtocol` gerencia SL/TP de ambos de forma isolada.

---
*Versão do Documento: 10.5.1 | Elite Branding & UI Stability Update*
