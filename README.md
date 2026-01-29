# 1CRYPTEN Space V4.3.2 DEEP SPACE 🦅🚀

Sistema de Trading Autônomo com Escalabilidade Geométrica, Vault Management e Interface de Voz Premium.

---

## 🆕 Novidades V4.3.2 - Voice Edition

### Voz Premium do Captain (Edge-TTS)
- **Voz Antonio:** Voz neural masculina PT-BR de alta qualidade
- **100% Gratuito:** Usa Edge-TTS (Microsoft) sem custo
- **Fallback:** Web Speech API se offline
- **Endpoint:** `POST /api/tts` retorna áudio MP3 base64

### UI Legibilidade Melhorada
- Fontes mínimas aumentadas de 8-10px para 12-14px
- Ícones aumentados para 24px
- Inputs 16px (previne zoom iOS)
- Melhor espaçamento para touch

---

## V4.3.1 - Blindagem de Execução

### Protocolo de Execução Blindada
- **Loop de 1 segundo:** Captura rápida de 100% ROI em SNIPER
- **SNIPER Hard Close:** Fecha automaticamente em ROI >= 100% (2% movimento @ 50x)
- **SURF Trailing Ladder:** Escada de proteção progressiva:
  - ROI 1% → Stop em Breakeven (0%)
  - ROI 3% → Stop em +1.5%
  - ROI 5% → Stop em +3%
  - ROI 10% → Stop em +7%

### Reset Atômico de Slots
- **`hard_reset_slot`:** Limpa slot instantaneamente após fechamento
- **Firebase Sync:** Atualiza banca e histórico automaticamente

---

## Slot Squadron Logic V4.3

| Tipo | Slots | Comportamento |
|------|-------|---------------|
| **SNIPER** | 1-5 | Alvo fixo +2% preço = 100% ROI @ 50x |
| **SURF** | 6-10 | Trailing stop dinâmico (escada) |

### Sistema de Promoção Automática
- **SNIPER → SURF:** Quando ROI > 30%, slot promovido automaticamente

---

## Arquivos Principais

| Arquivo | Descrição |
|---------|-----------|
| `main.py` | Endpoint `/api/tts` com Edge-TTS |
| `services/execution_protocol.py` | Lógica ROI-based para SNIPER/SURF |
| `services/bybit_rest.py` | Paper Execution Engine com loop 1s |
| `services/firebase_service.py` | Método `hard_reset_slot` |
| `frontend/code.html` | TTS Premium + UI legibilidade |

---

## Como Iniciar

```powershell
cd 1CRYPTEN_SPACE_V4.0/backend
python main.py
```

Acesse `http://localhost:5001`

---

## Endpoints V4.3.2

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/tts` | POST | **NOVO** - Text-to-Speech premium |
| `/api/tts/voices` | GET | Lista vozes disponíveis |
| `/api/chat` | POST | Chat com Captain |
| `/api/vault/status` | GET | Status do ciclo e vault |
| `/panic` | POST | Kill switch (fechar tudo) |

---

## Vozes Disponíveis (Edge-TTS)

| Voz | Idioma | Gênero |
|-----|--------|--------|
| `pt-BR-AntonioNeural` | PT-BR | **Masculino** (Captain) |
| `pt-BR-FranciscaNeural` | PT-BR | Feminino |
| `en-US-GuyNeural` | EN-US | Masculino |
| `en-US-JennyNeural` | EN-US | Feminino |

---

**Operação: 10D - Deep Space - V4.3.2 Voice Edition.**
