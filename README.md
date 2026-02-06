# 1CRYPTEN SPACE - V10.6.3 (Autonomous Edition) 💎🛰️

Sistema de Trading Autônomo Multitarefa com **Protocolo Concurrent Dual Sniper**, focado em escala de capital, gestão de risco dinâmica e autonomia total V10.6.3.

---

## 🆕 Novidades V10.6.3 - Autonomous Edition (Current)
- **Autonomous Captain Mode**: Remoção de controles manuais em favor de uma IA 100% autônoma. O sistema monitora e executa sem interrupções humanas.
- **Micro-Margin Accessibility**: Piso de margem reduzido para **$1.0** (anteriormente $4.0), permitindo que bancas pequenas operem fielmente com a regra de 10%.
- **Seamless Vault Sync**: Sincronização global de trade history e progresso de ciclos (1/10) entre todos os componentes da UI.
- **Hybrid Multi-Mode Sync**: Implementação de redundância RTDB + REST para status do sistema e gerenciamento de slots ativos.
- **Fixed Pagination History**: Recuperação otimizada do histórico de trades com tratamento de tipos (Timestamp Float) para scroll infinito.

## 🆕 Novidades V10.4 - Dual Slot Edition
- **Dual Sniper Slots**: Permite a abertura de um segundo trade simultâneo assim que o primeiro atinge o estado de **Risk-Zero**.
- **Tabbed Dashboard**: Interface multi-aba para monitoramento de ambos os slots de forma independente e intuitiva.
- **Multitasking Risk Protocol**: Gestão de exposição dinâmica permitindo até 40% da banca ativa (20% por slot).

## 🆕 Novidades V10.3 - ATR Edition
- **ATR Dynamic Stop-Loss**: Gestão de risco baseada na volatilidade (`1.5 * ATR`), eliminando stops fixos ineficientes.
- **Port 8080 Standardization**: Unificação total da infraestrutura na porta 8080 para acesso local simplificado.

## 🆕 Novidades V10.1 - Pulse Edition
- **Unified Versioning**: Sincronização total de versão (V10.1) entre Backend (`main.py`) e Inteligência (`captain.py`).
- **Stability Protocol**: Correção crítica de `UnboundLocalError`.

---

## 🏦 Lógica de Operação V10.5

| Tipo | Slots | Alocação Máxima | Protocolo |
|------|-------|-------------|-----------|
| **CONCURRENT DUAL** | 2 | 20% (10% x2) | Concurrent ATR-Aware |

---

## 📊 Gerenciamento de Risco
- **Independent Execution**: Ambos os slots operam de forma independente, sem necessidade de Risk-Zero para ativação do segundo slot.
- **Autonomous SL/TP**: Gestão de saída via stop-loss dinâmico (ATR) e take-profit automático configurado na exchange.
- **Exposure Cap**: Limite balanceado de 2 slots ativos (20% exposição total) para proteção contra cisnes negros.
- **Guardian Protocol**: Loop de monitoramento que garante a consistência entre o estado da Exchange e o Firestore (Persistence Shield).

---

## Como Iniciar

```powershell
cd 1CRYPTEN_SPACE_V4.0/backend
python main.py
```

Acesse `http://localhost:8080` (Standard V10.4 Port)

---

**Operação: 10D - Concurrent Dual Governance - V10.5 Elite**
