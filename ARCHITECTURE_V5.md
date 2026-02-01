# 1CRYPTEN SPACE - Blueprint & System Architecture (V5.4.0) 🛰️

Este documento descreve o funcionamento interno, fluxos de dados e protocolos do sistema 1CRYPTEN SPACE. Utilize este contexto para planejar melhorias em lógica de IA, otimização de execução e interface.

---

## 1. Arquitetura de Alto Nível 🏛️

O sistema opera de forma assíncrona com três camadas integradas:

- **Frontend (UI)**: React/Tailwind em arquivo único (`code.html`), com suporte a múltiplos temas (Modo Gemini).
- **Backend (API)**: FastAPI (`main.py`) orquestrando sessões Bybit, IAs e persistência.
- **Agents (Background)**: Loops `asyncio` que executam monitoramento e decisões em tempo real.

---

## 2. Dicionário de Componentes ⚙️

### 🛡️ Agents (services/agents/)
- **Captain (`captain.py`)**: Orquestrador tático. Escaneia sinais, verifica protocolos de risco (Bankroll) e cooldowns. Único agente autorizado a abrir ordens.
- **Guardian (`guardian.py`)**: Zelador das posições (Reaper). Monitora lucros em tempo real, move o Stop Loss e gerencia o fechamento. (V5.3.4: Sincronizado com o Escudo de Idempotência).
- **Signal Generator (`signal_generator.py`)**: Analisador de mercado. Transforma dados brutos de CVD em scores de oportunidade.
- **AI Service (`ai_service.py`)**: Ponte para modelos LLM. Gerencia o contexto e a personalidade do Capitão.

### 🔌 Services (services/)
- **BybitREST**: V5.3.4: **Idempotent Execution Shield**. Implementa travas atômicas e sets de fechamento pendente para evitar execuções duplicadas e registros de histórico em dobro.
- **BybitWS**: Gerencia conexões WebSocket para Tickers e Klines, alimentando o radar de CVD.
- **FirebaseService**: V5.3.4: Inclui verificação de estado dinâmico (`get_slot`) em resets de slot para garantir atomicidade.
- **BankrollManager**: Gestor de banca e risco. Garante limite de slots e gerencia os 10 "Squadron Slots".
- **VaultService**: Gestor do Ciclo Sniper de 20 trades. Calcula PnL acumulado e gerencia retiradas.

---

## 3. Visual Engine & Temas (V5.4.0) 🎨

O sistema agora utiliza um motor de temas baseado em variáveis CSS (`:root`), permitindo personalização profunda da UI sem alteração de lógica.

- **Classic Dark**: O tema original baseado em preto absoluto e dourado.
- **Modo Gemini**: Interface inspirada no Google Gemini, utilizando cinza profundo (`#131314`), bordas suaves e design minimalista.
- **Persistência**: O estado do tema é gerenciado no componente `App` e persistido via `localStorage`.

---

## 4. Fluxos de Dados Críticos 🔄

### A. Geração de Sinais
`BybitWS` (Fluxo Ordens) ➡️ `SignalGenerator` (Cálculo CVD) ➡️ `Firestore` (journey_signals)

### B. Ciclo de Vida do Trade (Idempotente)
1. `Captain` detecta sinal ➡️ `Bankroll` valida slots ➡️ `BybitREST` envia Ordem.
2. `Guardian` ou `BybitREST` detectam condição de fechamento.
3. **Escudo V5.3.4**: Uma trava (`closure_lock`) é ativada. Se uma tentativa de fechamento já estiver em curso, a segunda é descartada.
4. Registro único no Histórico e limpeza do Slot no Firebase.

---

## 5. Protocolos Estratégicos (V5.3 - V5.4) 📜

### 🎯 SNIPER OVERDRIVE
- **Floor Protection**: Lucro 100% garantido após atingido.
- **Chase Logic**: Perseguição de topo com distância de 20%.

### 🏄 SURF Trailing
- Trailing em escada de 8 níveis. Risk Zero automático em 50% ROI.

### ⏱️ Cooldown Persistente (V5.3.4)
- Bloqueio de símbolos em nível de Firebase para garantir que a pausa técnica persista mesmo após reinicializações do servidor.

---
*Versão do Documento: 5.4.0 | Contexto para Gemini AI*
