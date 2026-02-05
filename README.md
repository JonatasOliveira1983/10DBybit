# 1CRYPTEN SPACE - V10.4 (Dual Slot Edition) 💎🛰️

Sistema de Trading Autônomo Multitarefa com **Protocolo Dual Sniper**, focado em escala de capital, gestão de risco dinâmica e estabilidade V10.4.

---

## 🆕 Novidades V10.4 - Dual Slot Edition (Current)
- **Dual Sniper Slots**: Permite a abertura de um segundo trade simultâneo assim que o primeiro atinge o estado de **Risk-Zero**.
- **Tabbed Dashboard**: Interface multi-aba para monitoramento de ambos os slots de forma independente e intuitiva.
- **Multitasking Risk Protocol**: Gestão de exposição dinâmica permitindo até 40% da banca ativa (20% por slot).
- **Compass Mode Evolution**: O sistema foca no BTC/USDT em slots vazios para manter a prontidão do Radar.

## 🆕 Novidades V10.3 - ATR Edition
- **ATR Dynamic Stop-Loss**: Gestão de risco baseada na volatilidade (`1.5 * ATR`), eliminando stops fixos ineficientes.
- **Port 8080 Standardization**: Unificação total da infraestrutura na porta 8080 para acesso local simplificado.

## 🆕 Novidades V10.1 - Pulse Edition
- **Unified Versioning**: Sincronização total de versão (V10.1) entre Backend (`main.py`) e Inteligência (`captain.py`).
- **Stability Protocol**: Correção crítica de `UnboundLocalError`.

---

## 🏦 Lógica de Operação V10.4

| Tipo | Slots | Alocação Máxima | Protocolo |
|------|-------|-------------|-----------|
| **DUAL SNIPER** | 2 | 40% (20% x2) | Multitasking ATR-Aware |

---

## 📊 Gerenciamento de Risco
- **Risk-Zero Trigger**: Slot 2 desbloqueado apenas após Slot 1 estar com Stop no Break-even.
- **Independent Trailing**: Cada slot possui sua própria escada de proteção e trailing profit.
- **Exposure Cap**: Limite rígido de 2 ordens para evitar overtrading e preservar a banca.
- **Master Toggle**: Controle total via Vault UI.

---

## Como Iniciar

```powershell
cd 1CRYPTEN_SPACE_V4.0/backend
python main.py
```

Acesse `http://localhost:8080` (Standard V10.4 Port)

---

**Operação: 10D - Dual Slot Governance - V10.4**
