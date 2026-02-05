# 1CRYPTEN SPACE - V10.3 (ATR Edition) 💎🛰️

Sistema de Trading Autônomo com **Protocolo ATR Extreme**, focado em detecção institucional, gestão de risco dinâmica e estabilidade V10.3.

---

## 🆕 Novidades V10.3 - ATR Edition (Current)
- **ATR Dynamic Stop-Loss**: Gestão de risco baseada na volatilidade (`1.5 * ATR`), eliminando stops fixos ineficientes.
- **Port 8080 Standardization**: Unificação total da infraestrutura na porta 8080 para acesso local simplificado.
- **Radar Visibility Boost**: BTC Signals ativados por padrão no Radar para feedback visual instantâneo.
- **SPA Deep Linking**: Redirecionamentos inteligentes no backend para as rotas `/radar`, `/logs` e `/vault`.
- **Elite 88 Scan**: Expansão do monitoramento para 88 pares de alta alavancagem com precisão Sniper.

## 🆕 Novidades V10.1 - Pulse Edition
- **Unified Versioning**: Sincronização total de versão (V10.1) entre Backend (`main.py`) e Inteligência (`captain.py`).
- **Stability Protocol**: Correção crítica de `UnboundLocalError` (Bankroll) e Limpeza Automática de Porta 8080 no startup.

## 🆕 Novidades V10.0 - Radar Intelligence
- **Advanced Pattern Detection**: Detecção de padrões institucionais: **Whale Activity**, **Bull/Bear Traps** e **Accumulation Box Exits**.
- **BTC Drag Mode**: Monitoramento de fluxo do BTC que ajusta a agressividade do Sniper.
- **V9.0 Cycle Diversification**: Gestão de ciclos de 10 trades obrigatoriamente diversificados.

---

## 🏦 Lógica de Operação V10.3

| Tipo | Slots | Alocação | Protocolo |
|------|-------|-------------|-----------|
| **SNIPER ATR** | 1 | 20% | Sequential ATR-Aware |

---

## 📊 Gerenciamento de Risco
- **ATR Initial Stop**: Calculado via volatilidade (0.7% a 2.0%).
- **Relaxed Trailing**: Proteção de lucro aprimorada (Risk-Zero Shield aos 50% ROI).
- **Single Position Limit**: Máximo de 01 ordem aberta globalmente.
- **Master Toggle**: Controle total via Vault UI.

---

## Como Iniciar

```powershell
cd 1CRYPTEN_SPACE_V4.0/backend
python main.py
```

Acesse `http://localhost:8080` (Standard V10.3 Port)

---

**Operação: 10D - ATR Governance - V10.3**
