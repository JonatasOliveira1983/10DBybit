# 1CRYPTEN SPACE - V8.0 (Sequential Diversification) 💎🛰️

Sistema de Trading Autônomo com **Protocolo de Diversificação Sequencial V8.0**, focado em rotação de ativos e precisão Sniper.

---

## 🆕 Novidades V8.0 - Sequential Diversification
- **V8.0 Sequential Diversification**: Garante a rotação de ativos após cada trade. O sistema registra o último par operado e busca obrigatoriamente um novo símbolo, maximizando a diversificação e evitando "oversitting" no mesmo par.
- **Single Sniper Rule**: Protocolo de trade único. Apenas 1 posição aberta por vez no Slot 1. Total remoção de lógicas de "Surf" para foco em precisão máxima.
- **MEGA_PULSE (Trailing Profit)**: Motor de lucro aprimorado. Quando atinge 100% de ROI, trava o lucro em 80% e segue o preço com respiro de 20%, permitindo capturar swings exponenciais (200%, 500%+).
- **Elite 50x+ Asset Rotation**: Filtro dinâmico para os ativos mais voláteis e líquidos da Bybit (83+ pares), priorizando momentum extremo de CVD.
- **20% Margin Strategy**: Alocação de 20% da banca configurada por operação Sniper, otimizando o poder de compra para um único trade de alta convicção.

---

## 🆕 Novidades V6.0 - Elite Armor & PnL Sync
- **V6.0 Robust mapping**: Blindagem total de precificação via correspondência exata (Exact Match). 
- **PnL USD Real-Time Sync**: Sincronização forçada do lucro em dólar no Firebase.

---

## 🆕 Histórico de Evolução
- **V5.4.5 Gemini Defense**: Porta 8080 Standard e Scorched Earth Reset.
- **V5.0 Adaptive Stop Loss**: Escada de proteção dinâmica (Breakeven e Proteção de Lucro).

---

## 🏦 Lógica de Operação V8.0

| Tipo | Slots | Alocação | Protocolo |
|------|-------|-------------|-----------|
| **SNIPER** | 1 | 20% | Sequential Diversification |

---

## 📊 Gerenciamento de Risco
- **Single Position Limit**: Máximo de 01 ordem aberta globalmente.
- **Symbol Cooldown**: Bloqueio temporário do último par operado para forçar rotação.
- **Master Toggle**: Controle total via Vault UI para pausar/iniciar novas operações.

---

## Como Iniciar

```powershell
cd 1CRYPTEN_SPACE_V4.0/backend
python main.py
```

Acesse `http://localhost:8080` (Standard V8.0 Port)

---

**Operação: 10D - Sequential Diversification - V8.0**
