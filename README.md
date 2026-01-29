# 1CRYPTEN Space V4.3.1 DEEP SPACE 🦅🚀

Sistema de Trading Autônomo com Escalabilidade Geométrica, Vault Management e Interface de Voz.

---

## Novidades V4.3.1

### Execução Serial de Ordens
- **Anti-Race Condition:** Cada ordem é processada e persistida antes da próxima
- **Delay 0.5s:** Entre ordens para garantir persistência no Firebase

### Guarda de Duplicação Absoluta
- **Símbolo Normalizado:** ONDOUSDT = ONDOUSDT.P (sem duplicatas)
- **Bloqueio Global:** Nenhum símbolo em 2 slots simultâneos

### Sistema de Promoção Automática
- **SNIPER → SURF:** Quando ROI > 30%, slot é promovido automaticamente
- **Remove TP Fixo:** Passa a usar Trailing Stop do Guardian

### Detector de Tipo de Sinal
- **SURF:** Score >= 82 + CVD >= 30,000
- **SNIPER:** Demais sinais

---

## Slot Squadron Logic V4.3
- **Sniper (Slots 1-5):** Alvo fixo +2% preço = 100% ROI @ 50x alavancagem
- **Surf (Slots 6-10):** Sem alvo, trailing stop dinâmico pelo Guardian
- **Inicialização:** 2 SNIPER + 2 SURF (expansão via RiskFree)

---

## Endpoints V4.2

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/vault/status` | GET | Status do ciclo e vault |
| `/api/vault/history` | GET | Histórico de retiradas |
| `/api/vault/withdraw` | POST | Registrar retirada |
| `/api/vault/new-cycle` | POST | Iniciar novo ciclo |
| `/api/system/cautious-mode` | POST | Toggle modo cautela |
| `/api/system/admiral-rest` | POST | Toggle Admiral's Rest |
| `/panic` | POST | Kill switch (fechar tudo) |

---

## Frontend V4.2

- **Vault Page:** `/vault_v4.0/code.html` - Ciclo, retiradas, controles
- **Voice Interaction:** Ícone de microfone no Banca Command Center
- **Quick Commands:** Botões de atalho para Status, Cautela, Ciclo
- **Navegação:** Links funcionais entre todas as páginas

---

## Como Iniciar

```powershell
cd 1CRYPTEN_SPACE_V4.0/backend
python main.py
```

Acesse `http://localhost:5001`

---

**Operação: 10D - Deep Space - V4.2 Almirante Edition.**
