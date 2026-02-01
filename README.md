# 1CRYPTEN SPACE - V5.2.4 (Full Market Scan & CVD Sync) 🛡️🚀

Sistema de Trading Autônomo com **Protocolo Adaptive Stop Loss V5.0**, Gerenciamento Dinâmico de Risco e Proteção Anti-Whipsaw.

---

## 🆕 Novidades V5.0 - Adaptive Stop Loss

### 🎯 SNIPER Adaptive SL (Novo!)
- **Stop Loss Dinâmico**: O SL do SNIPER agora move automaticamente conforme o lucro aumenta
- **Escada de Proteção SNIPER**:
  | ROI Atingido | Novo Stop Loss |
  |--------------|----------------|
  | 70%+ | +30% ROI (protege lucro) |
  | 50%+ | +10% ROI (lucro garantido) |
  | 30%+ | -10% ROI (reduz perda) |
  | 15%+ | -30% ROI (de -50% original) |
- **Take Profit**: Mantém 100% ROI (2% movimento @ 50x)

### 🏄 SURF Enhanced Ladder
- **8 Níveis de Proteção** (era 6): Escada mais granular
- **Breakeven Antecipado**: Ativa em ROI 10% (era 5%)
- **Mega Surf**: Novo nível 200% ROI com proteção em 170%

### ⏱️ Cooldown Anti-Whipsaw (Novo!)
- **5 Minutos de Bloqueio**: Após fechamento por SL, par fica em cooldown
- **Evita Reentradas Ruins**: Protege contra whipsaws consecutivos
- **Registro Automático**: Guardian notifica Captain após cada SL

### 🛡️ Guardian V5.2.4
- **Full Market Monitoring (83 Symbols)**: Corrigido timeout de scan e compatibilidade Python 3.10.
- **CVD Symbol Sync**: Sincronização de nomenclatura para detecção de sinais em tempo real.
- **Move SL de SNIPER**: Agora atualiza Stop Loss via `set_trading_stop`
- **Overclock Mode**: 200ms polling em Flash Zone (80%+ ROI)
- **Status Visual TRAILING**: Novo estado para indicar SL em movimento
- **Sync & Persistence Elite**: 
  - **PWA Instant-Load**: Cache local (`localStorage`) para carregamento instantâneo de slots e banca.
  - **Stream-First Feed**: Priorização de WebSocket Bybit sobre polling para delay < 100ms.
  - **Bybit Precision Engine**: Arredondamento cirúrgico baseado em `tickSize` (evita erro 10001).
  - Sincronização automática de Vault e Banca na inicialização.
  - Motor PAPER totalmente integrado ao Vault (resultados refletem no dashboard).
  - Escudo de Persistência 2.0: Previne re-adoção de trades encerrados.

---

## 🏦 Slot Squadron Logic

| Tipo | Slots | Take Profit | Stop Loss |
|------|-------|-------------|-----------|
| **SNIPER** | 1-5 | 100% ROI fixo | Adaptativo (-50% → +30%) |
| **SURF** | 6-10 | Sem limite (trailing) | Escada 8 níveis |

---

## 📊 Gerenciamento de Risco Elite
- **Protocolo 4-Slots Máximo:** Limite de 4 ordens em risco (20% da banca)
- **Expansão Inteligente:** Novos slots liberados quando existentes atingem Risk-Zero
- **Cooldown por Símbolo:** 5 minutos após SL para evitar overtrading

---

## Como Iniciar

```powershell
cd 1CRYPTEN_SPACE_V4.0/backend
python main.py
```

Acesse `http://localhost:5001`

---

**Operação: 10D - Full Market & CVD Sync - V5.2.4**
