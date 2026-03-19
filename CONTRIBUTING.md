# Contribuindo com o Niklaus

Contribuições são bem-vindas — bugs, features, testes, documentação. Qualquer ajuda é apreciada.

## Contato

- Issues: [GitHub Issues](https://github.com/walternagai/niklaus-plagiarism/issues)
- E-mail: [walternagai@unifei.edu.br](mailto:walternagai@unifei.edu.br)

---

## Reportando problemas

Antes de abrir uma issue, verifique se ela já não foi relatada. Ao criar:

1. Descreva o problema claramente.
2. Liste os passos para reproduzir.
3. Indique o comportamento esperado vs. o observado.
4. Inclua versão do Python, sistema operacional e saída de erro completa.

---

## Pull Requests

1. Faça fork do repositório.
2. Crie uma branch descritiva: `git checkout -b fix/oauth-state-validation`
3. Faça as alterações seguindo os padrões abaixo.
4. Execute a suite de testes (veja seção **Testes**).
5. Commit com mensagem clara no formato convencional: `fix(oauth): corrige validação de estado`
6. Abra o Pull Request com descrição do que foi feito e por quê.

---

## Setup de desenvolvimento

```bash
# Clone o fork
git clone https://github.com/SEU_USUARIO/niklaus-plagiarism.git
cd niklaus-plagiarism

# Ambiente virtual
python -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate       # Windows

# Dependências
pip install -r requirements.txt

# Banco de dados local
python scripts/init_db.py

# Secrets (copie e edite)
cp secrets.toml.example .streamlit/secrets.toml
# Configure NIKLAUS_SECRET_KEY e ao menos um provedor OAuth

# Executar
streamlit run app.py
```

---

## Testes

```bash
# Suite rápida (padrão — exclui testes com sleep)
pytest tests/ -k "not slow"

# Suite completa
pytest tests/

# Com cobertura
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

A suite contém **102 testes** cobrindo: AST, métricas, padrões, pipeline, cache, OAuth, repositório, exportação e histórico. Toda nova feature deve ter testes correspondentes.

---

## Padrões de código

- Siga **PEP 8** (máx. 120 colunas).
- Escreva **docstrings** em funções públicas.
- **Type hints** em funções novas.
- Prefira editar arquivos existentes a criar novos.
- Não commite secrets, `.env`, `niklaus.db` ou arquivos temporários.
- Antes de commitar: `pytest tests/ -k "not slow"` deve passar.

---

## Estrutura do projeto

```
niklaus-plagiarism/
├── app.py                    # Entrypoint Streamlit (OAuth callback + renderização)
├── core/
│   ├── analyzer.py           # Orquestrador paralelo (textual, AST, métricas, padrões)
│   ├── pipeline.py           # Pipeline de análise com cache, progresso e cancelamento
│   ├── file_handler.py       # Extração ZIP com validação de path traversal
│   ├── comparison.py         # Comparação textual (difflib SequenceMatcher)
│   ├── llm_client.py         # Cliente Maritaca AI (rate limiting, retry)
│   └── persistence.py        # Cache JSON em disco com TTL no filename
├── auth/
│   ├── models.py             # Modelos SQLAlchemy (User, Submission, AuditLog, Cache)
│   ├── database.py           # DatabaseManager + session_scope() context manager
│   ├── repository.py         # Repositórios com filtros SQL, bulk delete e contadores
│   ├── oauth.py              # OAuthHandler (HMAC estado, tokens Fernet)
│   ├── config.py             # OAuthConfig + encrypt_token / decrypt_token
│   ├── session.py            # SessionManager (Streamlit session state)
│   └── decorators.py         # @require_auth, @require_admin
├── analyzer/
│   ├── ast_parser.py         # ASTParser (SHA-256 fingerprint, detecção de idioma)
│   ├── metrics.py            # CodeMetrics (Halstead correto, MI, CC, LOC)
│   ├── clustering.py         # ClusterDetector (hierárquico + comunidades NetworkX)
│   └── patterns.py           # PlagiarismPatternDetector (8 tipos, guards estruturais)
├── export/
│   └── service.py            # ExportService.to_csv() / to_json() / to_summary_csv()
├── ui/
│   ├── sidebar.py            # Painel lateral com configurações
│   ├── tooltips.py
│   ├── tutorial.py
│   ├── auth/                 # Páginas de autenticação (login, dashboard, perfil, admin)
│   ├── components/           # Componentes reutilizáveis
│   └── tabs/
│       ├── upload.py         # Upload + trigger de análise
│       ├── results.py        # Resultados + diff visual + exportação
│       ├── statistics.py     # Heatmap + histograma + preview
│       ├── advanced.py       # AST + métricas + radar chart + padrões
│       ├── graph.py          # Grafo interativo NetworkX
│       ├── history.py        # Histórico com filtros SQL, paginação, bulk delete
│       ├── monitoring.py
│       └── performance.py    # Dashboard de performance
├── utils/
│   ├── config.py             # Config dataclass com defaults e env overrides
│   ├── exceptions.py         # Hierarquia de exceções + raise_if_cancelled()
│   ├── db_cache.py           # QueryCache + SubmissionCache (LRU + TTL)
│   ├── performance.py        # @track_performance decorator e métricas
│   ├── lazy_loader.py        # Importação lazy de módulos pesados
│   ├── logger.py             # Logger configurado
│   ├── error_handling.py     # Helpers de exibição de erros na UI
│   ├── parallel.py           # ParallelComparator (ThreadPoolExecutor)
│   ├── distributed_cache.py  # Cache distribuído (InMemory + Redis opcional)
│   └── alerts.py
├── tests/                    # pytest — 102 testes
├── scripts/                  # init_db.py, create_admin.py, test_oauth_*
├── docs/                     # Documentação técnica
├── migrations/               # Migrações de banco de dados
├── pytest.ini                # Marcadores pytest (slow)
├── requirements.txt          # Dependências fixadas
└── secrets.toml.example      # Template de configuração
```

---

## Status de funcionalidades

| Funcionalidade | Status | Notas |
|---|---|---|
| Detecção textual de similaridade | Implementado | SequenceMatcher, paralelo |
| Multi-linguagem (9 idiomas) | Implementado | Ver tabela de extensões no README |
| Fingerprint Winnowing determinístico | Implementado | SHA-256, estável entre processos |
| AST Python nativo | Implementado | Funções, classes, imports, loops |
| AST outros idiomas (fingerprint) | Implementado | Comparação por Winnowing |
| Métricas Halstead corretas | Implementado | n1 conta operadores presentes no código |
| Classificação em 8 tipos de plágio | Implementado | Guards estruturais no detector |
| IA por par suspeito (Maritaca) | Implementado | Rate limiting + retry |
| Cancelamento cooperativo | Implementado | `AnalysisCancelledError` propagado |
| Cache JSON em disco | Implementado | TTL no filename, sem pickle |
| Visualizações interativas | Implementado | Plotly: heatmap, radar, grafo |
| Clustering hierárquico | Implementado | SciPy + NetworkX communities |
| Diff visual | Implementado | Side-by-side + unified diff |
| Exportação CSV + JSON | Implementado | `ExportService` em `export/service.py` |
| Autenticação OAuth 3 providers | Implementado | Google, GitHub, Microsoft |
| Tokens OAuth criptografados | Implementado | Fernet/AES-128 em repouso |
| Estado OAuth assinado HMAC | Implementado | `NIKLAUS_SECRET_KEY` |
| Histórico com filtros SQL | Implementado | Paginação server-side |
| Contadores de usuário | Implementado | Incrementados no `create()` |
| 102 testes pytest | Implementado | auth, repo, pipeline, AST, export… |
| Export PDF | Planejado | `export/` pronto para receber formatador |
| Integração LMS (Canvas, Moodle) | Planejado | — |
| Processamento em lote (multi-ZIP) | Planejado | — |

---

## Perguntas frequentes

**Como adicionar um novo provedor OAuth?**
Adicione a configuração em `auth/config.py` e implemente `get_authorization_url`, `_exchange_code_for_token` e `_get_user_profile` em `auth/oauth.py` para o novo provider.

**Como adicionar uma nova aba?**
Crie `ui/tabs/minha_aba.py` com uma função `render_minha_aba(results, settings)` e importe-a em `app.py` dentro de `_render_authenticated_app`.

**Como exportar resultados programaticamente?**
```python
from export.service import ExportService
csv_bytes = ExportService.to_csv(results)
json_bytes = ExportService.to_json(results)
```

**Como desabilitar o cache em desenvolvimento?**
Passe `use_cache=False` ao criar o `AnalysisPipeline`, ou defina `max_age_hours=0` ao chamar `AnalysisCache.load()`.
