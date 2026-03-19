# Niklaus — Detecção de Plágio em Código

Sistema avançado de detecção de plágio para trabalhos de programação. Combina análise estática, comparação estrutural (AST), métricas de complexidade e IA (Maritaca Sabiazinho-4) para identificar e classificar similaridades entre arquivos de código-fonte.

---

## Funcionalidades

| Recurso | Descrição |
|---|---|
| Detecção automática | Compara todos os pares de arquivos em paralelo |
| Multi-linguagem | Python, C, C++, Java, JavaScript, TypeScript, Go, Rust, Kotlin |
| Análise AST | Similaridade estrutural (Python nativo; fingerprint para demais) |
| Métricas de código | LOC, complexidade ciclomática, contagem de funções, MI, Halstead |
| Classificação de plágio | 8 tipos com confidence score |
| IA por par suspeito | Análise textual via Maritaca Sabiazinho-4 |
| Visualizações | Heatmap, histograma, grafo interativo de similaridade, radar chart |
| Clustering | Detecção hierárquica de grupos de plágio com badge de severidade |
| Histórico | Submissões por usuário com filtros SQL, paginação e ações em lote |
| Exportação | CSV (pares + métricas) e JSON completos para download |
| Autenticação OAuth | Google, GitHub e Microsoft |
| Cancelamento | Análise cancelável pelo usuário a qualquer momento |

---

## Pré-requisitos

- Python 3.9+
- Chave de API Maritaca (obtenha em [maritaca.ai](https://maritaca.ai))
- Conta OAuth em pelo menos um dos provedores suportados (Google, GitHub, Microsoft)

---

## Instalação

```bash
git clone https://github.com/walternagai/niklaus-plagiarism.git
cd niklaus-plagiarism
pip install -r requirements.txt
python scripts/init_db.py
```

---

## Configuração

Crie `.streamlit/secrets.toml` baseando-se no exemplo:

```bash
cp secrets.toml.example .streamlit/secrets.toml
```

Edite o arquivo com suas credenciais:

```toml
# Chave da aplicação — obrigatória para segurança do estado OAuth e criptografia de tokens
NIKLAUS_SECRET_KEY = "sua-chave-secreta-longa-e-aleatoria"

# Admin emails (opcional — separados por vírgula)
ADMIN_EMAILS = "voce@exemplo.com"

# Maritaca AI
[maritaca]
MARITACA_API_KEY  = "sua-chave-maritaca"
MARITACA_MODEL    = "sabiazinho-4"

# OAuth — configure ao menos um provedor
[google]
client_id      = "seu-google-client-id"
client_secret  = "seu-google-client-secret"
redirect_uri   = "http://localhost:8501"

[github]
client_id      = "seu-github-client-id"
client_secret  = "seu-github-client-secret"
redirect_uri   = "http://localhost:8501"

[microsoft]
client_id      = "seu-microsoft-client-id"
client_secret  = "seu-microsoft-client-secret"
tenant_id      = "common"
redirect_uri   = "http://localhost:8501"
```

> **Nota de segurança:** `NIKLAUS_SECRET_KEY` é usada para assinar o estado OAuth (proteção contra CSRF) e para criptografar tokens de acesso armazenados no banco de dados com Fernet/AES-128. Configure-a com um valor aleatório longo. Se ausente, um aviso é emitido e um fallback fraco é usado.

---

## Execução

```bash
streamlit run app.py
```

Acesse `http://localhost:8501` e faça login com um dos provedores OAuth configurados.

---

## Como usar

1. **Faça login** via Google, GitHub ou Microsoft.
2. Na aba **Upload & Análise**:
   - Selecione a linguagem dos arquivos.
   - Ajuste o threshold de similaridade (padrão: 70%).
   - Configure workers paralelos e ative/desative IA.
   - Envie um arquivo **ZIP** contendo os códigos a comparar.
   - Clique em **Analisar Arquivos**.
3. Acompanhe o progresso — é possível **cancelar** a análise a qualquer momento.
4. Explore os resultados nas abas:

| Aba | Conteúdo |
|---|---|
| **Resultados** | Tabela de similaridade, análise IA, diff visual lado a lado |
| **Estatísticas** | Heatmap, histograma por faixa, preview de arquivos |
| **Análise Avançada** | AST, métricas de complexidade, radar chart, padrões de plágio |
| **Grafo de Similaridade** | Rede interativa, clusters, comunidades |
| **Histórico** | Submissões anteriores com filtros, carregamento e exclusão em lote |

5. **Exporte** resultados em CSV ou JSON pela aba Resultados.

---

## Linguagens suportadas

| Linguagem | Extensão | AST detalhado | Fingerprint Winnowing |
|---|---|---|---|
| Python | `.py` | Sim (AST nativo) | Sim |
| Java | `.java` | — | Sim |
| C | `.c` | — | Sim |
| C++ | `.cpp, .cc, .cxx` | — | Sim |
| JavaScript | `.js` | — | Sim |
| TypeScript | `.ts, .tsx` | — | Sim |
| Go | `.go` | — | Sim |
| Rust | `.rs` | — | Sim |
| Kotlin | `.kt, .kts` | — | Sim |

> Fingerprints usam SHA-256 para resultados determinísticos entre processos e reinicializações.

---

## Tipos de plágio detectados

| Tipo | Descrição |
|---|---|
| `COPIA_DIRETA` | Similaridade textual e estrutural > 95% |
| `RENOMEACAO_VARIAVEIS` | Estrutura idêntica, variáveis/parâmetros renomeados |
| `REORDENACAO_CODIGO` | Blocos reorganizados com conteúdo equivalente |
| `INSERCAO_CODIGO_MORTO` | Código morto ou comentários excessivos inseridos |
| `REFATORACAO_LEVE` | Pequenas modificações estruturais |
| `REFATORACAO_PESADA` | Refatoração significativa mantendo funcionalidade |
| `SIMILARIDADE_BAIXA` | Código provavelmente original |
| `REUSO_LEGITIMO` | Reutilização de bibliotecas ou padrões comuns |

---

## Arquitetura

```
niklaus-plagiarism/
├── app.py                    # Entrypoint Streamlit + fluxo OAuth
├── core/
│   ├── pipeline.py           # Pipeline de análise (coordenação)
│   ├── analyzer.py           # Orquestrador paralelo (textual, AST, métricas, padrões)
│   ├── file_handler.py       # Extração ZIP com validação de path traversal
│   ├── comparison.py         # Comparação textual (SequenceMatcher)
│   ├── llm_client.py         # Cliente Maritaca (rate limiting, retry)
│   └── persistence.py        # Cache JSON em disco (Winnowing, TTL no filename)
├── auth/
│   ├── models.py             # Modelos SQLAlchemy (User, Submission, AuditLog)
│   ├── database.py           # DatabaseManager + session_scope()
│   ├── repository.py         # Repositórios com filtros SQL e bulk delete
│   ├── oauth.py              # OAuthHandler (estado assinado HMAC, tokens Fernet)
│   ├── config.py             # OAuthConfig + encrypt_token / decrypt_token
│   └── session.py            # SessionManager (Streamlit session state)
├── analyzer/
│   ├── ast_parser.py         # ASTParser (SHA-256 fingerprint, detecção de linguagem)
│   ├── metrics.py            # CodeMetrics (Halstead corrigido, MI, CC)
│   ├── clustering.py         # ClusterDetector (hierárquico + comunidades)
│   └── patterns.py           # PlagiarismPatternDetector (8 tipos, guards estruturais)
├── export/
│   └── service.py            # ExportService (to_csv, to_json, to_summary_csv)
├── ui/
│   ├── sidebar.py
│   └── tabs/
│       ├── upload.py         # Upload + início de análise
│       ├── results.py        # Resultados + diff visual + exportação
│       ├── statistics.py     # Heatmap + histograma
│       ├── advanced.py       # AST + métricas + padrões
│       ├── graph.py          # Grafo interativo
│       └── history.py        # Histórico com SQL filtering + bulk delete
├── utils/
│   ├── config.py             # Configurações globais
│   ├── exceptions.py         # Hierarquia de exceções + raise_if_cancelled()
│   ├── db_cache.py           # QueryCache + SubmissionCache (LRU+TTL)
│   └── performance.py        # @track_performance decorator
├── tests/                    # 102 testes pytest
├── scripts/                  # Utilitários (init_db, create_admin, test_oauth_*)
└── docs/                     # Documentação técnica
```

---

## Stack tecnológica

| Camada | Tecnologia |
|---|---|
| Interface | Streamlit |
| Análise IA | Maritaca Sabiazinho-4 (via OpenAI SDK) |
| Banco de dados | SQLite (dev) / PostgreSQL (prod) via SQLAlchemy |
| Criptografia | `cryptography` (Fernet/AES-128 para tokens OAuth) |
| Visualização | Plotly |
| Grafo | NetworkX |
| Clustering | SciPy |
| Exportação | CSV nativo Python + JSON |

---

## Testes

```bash
# Suite completa (exceto testes lentos)
pytest tests/ -k "not slow"

# Incluindo o teste de rate limiter (~1s extra)
pytest tests/

# Com cobertura
pytest tests/ --cov=. --cov-report=html
```

A suite conta com **102 testes** cobrindo: análise de AST, métricas, padrões, pipeline, comparação, cache, OAuth, repositório, exportação e normalização de histórico.

---

## Segurança

- Tokens OAuth (access + refresh) criptografados em repouso com **Fernet/AES-128** antes de persistir no banco.
- Estado OAuth assinado com **HMAC-SHA256** usando `NIKLAUS_SECRET_KEY`, prevenindo CSRF e adulteração.
- Cache de disco em **JSON** (não pickle) — elimina risco de execução remota de código via cache adulterado.
- Validação de **path traversal** no upload de ZIP.
- `niklaus.db` adicionado ao `.gitignore` — nunca versionado.
- Sessões expiram após 24 horas.

---

## Contribuindo

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes de setup, padrões de código e fluxo de PR.

## Licença

CC0 1.0 Universal — veja [LICENSE](LICENSE).
