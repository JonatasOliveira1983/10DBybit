# 10D-Bybit Trading System v4.0 (1CRYPTEN SPACE)

## Visão Geral
Sistema de trading automatizado v4.0 "Deep Space", integrado com Bybit (Testnet) e Firebase.
O sistema opera em uma arquitetura unificada onde o Backend serve o Frontend, eliminando problemas de CORS e simplificando o deploy.

## Arquitetura Unificada
- **Porta Única:** 5001 (Backend + Frontend)
- **Frontend:** React (SPA) servido estaticamente pelo FastAPI. Conecta diretamente ao Firestore para dados em tempo real.
- **Backend:** FastAPI (Python) responsável por:
    - Gerenciar agentes (Captain, Guardian, Gemini, SignalGenerator).
    - Executar trades na Bybit via API.
    - Alimentar o Firebase com dados para o frontend.

---

## Como Iniciar

### 1. Pré-requisitos
- Python 3.10+
- Chave `serviceAccountKey.json` na pasta `backend/`.
- Arquivo `.env` configurado com credenciais da Bybit Testnet.

### 2. Comando de Inicialização
Abra o terminal na raiz do projeto e execute:

```powershell
# Iniciar todo o sistema (Backend + Agentes + Frontend)
cd 1CRYPTEN_SPACE_V4.0/backend
.\.venv\Scripts\python.exe main.py
```

### 3. Acessar
Abra no navegador: **[http://localhost:5001](http://localhost:5001)**

---

## Funcionalidades (v4.0)

### 1. Dashboard (BANCA)
- Monitoramento de Saldo e Risco em tempo real.
- Gráfico TradingView (Lightweight) com plotagem de *Entries* e *Stops*.
- **Cálculo de Risco:** 20% de Cap Máximo, com liberação dinâmica para trades "Risk Free" (Stop no lucro).

### 2. Journey Radar
- Scanner de sinais de alta probabilidade.
- Filtro de Sinais "Elite" (Score > 90).

### 3. Synergy Logs
- Logs detalhados das decisões dos agentes.
- **Captain:** Executa trades.
- **Guardian:** Monitora latência e saúde do sistema (Auto-Pause se latência > 1000ms).
- **Gemini:** Analisa sentimento de mercado (IA).

---

## Solução de Problemas
- **Erro 404 em `/api/...`**: Pode ser ignorado. O frontend v4.0 usa Firebase direto; chamadas antigas de API podem aparecer nos logs se houver abas antigas abertas.
- **Guardian "SYSTEM UNHEALTHY"**: Indica latência alta na Testnet. O sistema continua rodando mas pode pausar novas entradas por segurança.
