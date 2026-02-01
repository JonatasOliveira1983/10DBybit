# 1CRYPTEN SPACE - V5.3.4 (Idempotent Shield & Captain's Voice) 🛡️🚀

Sistema de Trading Autônomo com **Protocolo Adaptive Stop Loss V5.0**, Gerenciamento Dinâmico de Risco e Proteção Anti-Whipsaw.

---

## 🆕 Novidades V5.3.4 - Escudo de Idempotência
- **Idempotência de Histórico**: Trava atômica que evita lançamentos duplicados no histórico de trades, mesmo com múltiplos processos de monitoramento redundante.
- **Validação de Reset**: Double-check de estado do Firebase antes de qualquer registro de fechamento.

## 🆕 Novidades V5.3.3 - Captain's Voice Shield
- **Voz do Capitão Mobile**: Otimização Premium para PWA e dispositivos mobile, priorizando vozes masculinas (Daniel/Antonio).
- **Auto-unlock de Áudio**: Mecanismo para contornar restrições de auto-play em navegadores móveis.
- **Manual Speak**: Botão de reprodução manual nas mensagens do Capitão.

## 🆕 Novidades V5.3.2 - Redundant SL Shield
- **Persistent SL Cooldown**: Bloqueio de símbolos após Stop Loss agora persistente no Firebase (sobrevive a reinicializações do backend).
- **Paper Protection**: Blindagem total contra reabertura imediata de ordens após Stop Loss em modo Simulação.

---

## 🆕 Novidades V5.0 - Adaptive Stop Loss

### 🎯 SNIPER Adaptive SL
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
- **8 Níveis de Proteção**: Escada mais granular para maximizar lucros.
- **Breakeven Antecipado**: Ativa em ROI 10%.
- **Mega Surf**: Novo nível 200% ROI com proteção em 170%.

### ⏱️ Cooldown Anti-Whipsaw
- **Bloqueio de Par**: Após fechamento por SL, o par entra em cooldown para evitar reentradas em volatilidade.
- **Registro Automático**: Sincronizado entre Guardian e Captain.

### 🛡️ Guardian & Sync Elite
- **Full Market Monitoring**: Monitoramento simultâneo de todos os pares USDT.
- **CVD Symbol Sync**: Detecção de sinais baseada em fluxo de ordens.
- **PWA Instant-Load**: Cache local para carregamento instantâneo.
- **Bybit Precision Engine**: Normalização de preços e quantidades.

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
- **Cooldown Persistente:** Proteção que sobrevive a reinícios do sistema.

---

## Como Iniciar

```powershell
cd 1CRYPTEN_SPACE_V4.0/backend
python main.py
```

Acesse `http://localhost:5001`

---

**Operação: 10D - Idempotent Shield & Captain's Voice - V5.3.4**
