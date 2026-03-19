# Changelog

Todas as mudanças notáveis do projeto são documentadas aqui.  
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Unreleased]

Sem mudanças pendentes no momento.

---

## [2.0.0] — 2026-03-19

Versão de hardening completo: correções de corretude, segurança, estabilidade, escalabilidade, qualidade de código, cobertura de testes e débito técnico.

### Adicionado

- **Exportação CSV e JSON** via `ExportService` em `export/service.py`:
  - `to_csv()` — tabela de pares com similaridade, tipo de plágio e confidence
  - `to_json()` — resultado completo serializado
  - `to_summary_csv()` — métricas por arquivo

- **Criptografia de tokens OAuth em repouso** com Fernet/AES-128 (`auth/config.py: encrypt_token / decrypt_token`)

- **`NIKLAUS_SECRET_KEY`** como chave dedicada para HMAC do estado OAuth e derivação da chave Fernet; aviso explícito quando ausente

- **`raise_if_cancelled()`** em `utils/exceptions.py` — função compartilhada de cancelamento cooperativo; eliminada duplicação entre `pipeline.py` e `analyzer.py`

- **Métodos públicos** em `PlagiarismAnalyzer`:
  - `calculate_textual_similarities()` — alias público de `_calculate_textual_similarities()`
  - `build_matrix()` — alias público de `_build_matrix()`

- **`delete_all_by_user()`** em `SubmissionRepository` — DELETE bulk em uma query SQL

- **Filtros SQL** em `SubmissionRepository.find_by_user()`: `date_start`, `date_end`, `min_similarity`, `max_similarity`; filtragem aplicada no banco, não em Python

- **Contadores denormalizados** do usuário (`submissions_count`, `total_analyses`, `total_suspicious_pairs`) agora incrementados em `SubmissionRepository.create()`

- **`DiskSessionManager`** em `core/persistence.py` — renomeado de `SessionManager` para evitar colisão de nomes com `auth/session.py:SessionManager`; alias `SessionManager` mantido para compatibilidade

- **`pytest.ini`** com marcador `@pytest.mark.slow` para deselecionar testes com sleep

- **Novos testes** em `tests/test_new_coverage.py`:
  - `TestTokenEncryption` — roundtrip Fernet, None, fallback
  - `TestSessionManager` — login, logout, autenticação, expiração
  - `TestSubmissionRepository` — CRUD, filtros, bulk delete, contadores
  - `TestNormalizeSubmissionAnalysis` — normalização de schema
  - `TestMaritacaClient` — prompt building, mocked API, tratamento de erro

- **`tests/test_oauth.py` refatorado** — funções de script convertidas para pytest puro; removida dependência de secrets ao vivo

### Corrigido

- **`hash()` não-determinístico** em fingerprints de AST (`analyzer/ast_parser.py`) → substituído por SHA-256
- **Bug de precedência** em `detect_language()`: `or ... and` → `or (... and ...)`
- **`n1` de Halstead constante** (`analyzer/metrics.py`) → agora conta operadores presentes no código, não o tamanho do set de referência (era sempre 42)
- **Falsos positivos** em `detect_variable_renaming()` (`analyzer/patterns.py`):
  - Guards estruturais: sobreposição de nomes, assinaturas de funções, pares efetivamente distintos
  - `_extract_all_names()` agora inclui parâmetros de função (`ast.arg`), não apenas atribuições
  - Confidence reduzida de 0.85 para 0.75
- **Chave de cancelamento duplicada** em `app.py`: `'cancel': False` removido; unificado para `'cancel_analysis'`
- **`st.stop()` como tratamento de erros** em `app.py` e `ui/tabs/upload.py` → substituído por `st.error() + return`
- **Vazamentos de sessão de banco** em `auth/session.py` e `auth/oauth.py` → `get_session()` envolvido em `contextlib.closing` ou `try/finally`
- **Double-clear no logout** (`auth/session.py`) → removido loop manual; mantido apenas `st.session_state.clear()`
- **Side effect em `get_authorization_url()`** (`auth/oauth.py`) → método removido de `st.session_state`; responsabilidade movida para o chamador
- **`Base` duplicado** em `auth/database.py` → declaração local removida; usado apenas `auth.models.Base`
- **Cache pickle substituído por JSON** (`core/persistence.py`) → elimina risco de RCE por desserialização
- **Timestamp no filename do cache** → `clear_old_cache()` filtra por nome de arquivo sem abrir nenhum arquivo
- **Métricas recalculadas redundantemente** em `_detect_patterns()` → métricas pré-calculadas são repassadas como `precomputed_metrics`
- **Exception chaining** em `core/pipeline.py` → `raise NiklausError(...) from e`
- **Contadores de usuário sempre zero** → `SubmissionRepository.create()` os incrementa
- **Histórico carregando 10.000 registros** em Python → filtragem e paginação movidas para SQL

### Segurança

- Tokens OAuth (access + refresh) criptografados com Fernet antes de persistir no banco
- Estado OAuth assinado com HMAC-SHA256 usando `NIKLAUS_SECRET_KEY`
- Cache de disco migrado de pickle para JSON (sem desserialização insegura)
- `niklaus.db` adicionado ao `.gitignore` e removido do tracking git

### Testes

- Suite de **102 testes** (era 81 antes desta versão)
- `test_detect_code_reordering` agora tem assertions completas
- `test_rate_limiter_basic` marcado com `@pytest.mark.slow`
- Testes de script OAuth convertidos para funções pytest puras

---

## [1.x] — Fases anteriores

### Fase 5 — Autenticação e Histórico

- Login OAuth (Google, GitHub, Microsoft) via `auth/`
- Banco de dados SQLite com SQLAlchemy
- Histórico de submissões com `SubmissionRepository`
- Estado OAuth assinado com HMAC (provider embedido)
- Pipeline de análise unificado (`core/pipeline.py`)
- Cancelamento cooperativo via `AnalysisCancelledError`
- Cache baseado em conteúdo (SHA-256 dos arquivos)

### Fase 2 — Visualizações e Clustering

- Grafo de similaridade interativo (NetworkX + Plotly)
- Clustering hierárquico + detecção de comunidades
- Diff visual (side-by-side e unified diff)
- 5 abas (era 4)

### Fase 1 — Análise Avançada

- Módulo `analyzer/` com AST, métricas, clustering, padrões
- 8 tipos de plágio com confidence score
- Radar chart de métricas de complexidade
- Análise paralela com `ThreadPoolExecutor`

### Fase inicial — MVP

- Análise textual multi-linguagem (9 idiomas)
- Interface Streamlit com upload de ZIP
- Integração com Maritaca Sabiazinho-4
- Heatmap e histograma de similaridade
- Exportação básica CSV/JSON

---

[Unreleased]: https://github.com/walternagai/niklaus-plagiarism/compare/main...HEAD
[2.0.0]: https://github.com/walternagai/niklaus-plagiarism/commits/main
