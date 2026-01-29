# 1CRYPTEN Space V4.8.0: Total Stability & Reset 🛡️🚀

Este relatório detalha a arquitetura, a lógica operacional e o estado atual da Nave 1CRYPTEN, consolidando o upgrade de **Estabilidade e Reset de Sistema v4.8.0**.

---

## 1. Conceito e Visão 🎯

O 1CRYPTEN é um Agente de Trading Autônomo que combina análise técnica de volume (CVD) com inteligência linguística superior.

**Versão 4.8.0 (Stability & Reset):** Esta versão foca na robustez operacional do backend, eliminando travamentos de inicialização e corrigindo inconsistências críticas no modo Paper Trading. Além disso, introduz uma infraestrutura de reset completo para reinicialização limpa do sistema.

---

## 2. Estabilidade do Backend 🛡️

### Chamadas de IA Assíncronas
- **Protocolo Anti-Congelamento:** Refatoração do `ai_service.py` para garantir que falhas ou lentidões em provedores de IA (OpenRouter/GLM/Gemini) não bloqueiem o loop de eventos principal.
- **Fallback Inteligente:** Transição suave entre modelos sem impactar a execução das ordens ou o monitoramento do mercado.

### Gestão de Processos
- **Prevenção de Conflitos:** Implementação de verificações de porta (5001) para evitar falhas de inicialização causadas por instâncias zumbis do Python.

---

## 3. Paper Trading 2.0 📑

### Normalização de Símbolos
- **Consistência Total:** Correção do mapeamento de símbolos Perpetuais (`.P`). O sistema agora normaliza os pares internamente, eliminando o erro `10001 (Position not found)` que ocorria na gestão de STOP LOSS pelo Guardian Agent.
- **Sincronização de Fidelidade:** Melhora na detecção de posições simuladas, garantindo que o Status de Risco reflita exatamente a realidade do simulador.

---

## 4. Reset Abrangente do Sistema 🔥

Recentemente adicionado o script `reset_system_v2.py`, permitindo uma limpeza profunda:

| Componente | Ação |
|------------|------|
| **Sinais** | Exclusão total do histórico de sinais gerados |
| **Slots** | Limpeza de todos os slots ativos e reinicialização para estado "LIVRE" |
| **Finanças** | Reset da banca simulada para $100.00 e limpeza do histórico de PNL |
| **Logs** | Limpeza de todos os registros de eventos do sistema |

---

## 5. Changelog v4.8.0

- ✅ **Async AI Wrapper:** Chamadas de backup de IA agora são não-bloqueantes.
- ✅ **Symbol Normalization:** Fim dos erros de `Position not found` no Paper Trading.
- ✅ **Comprehensive Reset:** Novo utilitário para limpeza total do Firebase (v2).
- ✅ **Port Conflict Fix:** Estabilidade na inicialização e reinício do backend.
- ✅ **Log Sanity:** Limpeza de ruídos e logs duplicados durante a fase de boot.

---

## Como Iniciar 🛠️

1. **Pré-requisitos:** Python 3.10+, `serviceAccountKey.json` e `.env` configurado.
2. **Reset (Opcional):** Para começar do zero:
   ```powershell
   python reset_system_v2.py
   ```
3. **Boot:** 
   ```powershell
   cd 1CRYPTEN_SPACE_V4.0/backend
   python main.py
   ```
4. **Interface:** Acesse `http://localhost:5001`

---

**Operação: 10D - Deep Space - V4.8.0 Stability Gold.**
