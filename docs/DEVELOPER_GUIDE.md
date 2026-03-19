# Guia do Desenvolvedor — Niklaus

Referência técnica para quem trabalha no código do Niklaus: arquitetura, APIs internas, padrões de código e práticas de desenvolvimento.

---

## Arquitetura

```
┌──────────────────────────────────────────────────────────┐
│                   Interface (Streamlit)                    │
│  app.py — OAuth callback, roteamento de abas, análise     │
│  ui/tabs/*.py — upload, results, stats, advanced, graph,  │
│                 history                                   │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│                   Lógica de negócio                       │
│  core/pipeline.py  — coordenação, cache, cancelamento     │
│  core/analyzer.py  — execução paralela das etapas         │
│  auth/             — OAuth, sessão, repositórios           │
│  export/service.py — exportação CSV/JSON                  │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│                   Primitivos                              │
│  analyzer/*.py — AST, métricas, clustering, padrões       │
│  core/comparison.py — similaridade textual                │
│  core/llm_client.py — Maritaca API                        │
└──────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────┐
│                   Persistência                            │
│  auth/database.py — SQLAlchemy (SQLite / PostgreSQL)      │
│  core/persistence.py — cache JSON em disco                │
│  utils/db_cache.py — QueryCache + SubmissionCache         │
└──────────────────────────────────────────────────────────┘
```

---

## Pipeline de análise

```python
from core.pipeline import AnalysisPipeline

pipeline = AnalysisPipeline(
    language='python',
    api_key='sua_chave_maritaca',   # None desativa IA
    max_workers=4,
    use_cache=True
)

def is_cancelled() -> bool:
    return st.session_state.get('cancel_analysis', False)

def on_progress(stage: str, current: int, total: int):
    print(f"{stage}: {current}/{total}")

results = pipeline.run_full_analysis(
    files=['a.py', 'b.py'],
    contents=[code_a, code_b],
    threshold=0.7,
    enable_ai=True,
    progress_callback=on_progress,
    cancel_check=is_cancelled
)
```

O resultado contém:
- `files`, `language`, `threshold`, `analysis_time`
- `textual_similarities` — lista de `(file1, file2, score)`
- `ast_similarities` — lista de `(file1, file2, score)`
- `metrics` — lista de dicts por arquivo
- `similarity_matrix` — ndarray NxN
- `cluster_data` — hierarquia + comunidades
- `patterns` — dict `"f1_f2"` → análise de padrão
- `pairwise_results` — todos os pares com scores consolidados
- `suspicious_pairs` — pares acima do threshold
- `ai_analyses` — análise textual IA por par suspeito (se habilitado)

### Cancelamento cooperativo

O cancelamento é implementado via `AnalysisCancelledError`. Qualquer ponto interno que chame `raise_if_cancelled(cancel_check)` pode interromper o fluxo.

```python
from utils.exceptions import raise_if_cancelled, AnalysisCancelledError

def raise_if_cancelled(cancel_check) -> None:
    """Lança AnalysisCancelledError se cancel_check() retornar True."""
    if cancel_check is not None and cancel_check():
        raise AnalysisCancelledError("Analysis cancelled by user")
```

Chame `raise_if_cancelled` em loops longas ou entre etapas. Capture `AnalysisCancelledError` no nível superior.

### Análise apenas textual (sem AST/métricas/IA)

```python
results = pipeline.run_textual_only(
    files=['a.py', 'b.py'],
    contents=[code_a, code_b],
    threshold=0.7
)
```

Ou use os métodos públicos do analisador diretamente:

```python
analyzer = pipeline.analyzer
sims   = analyzer.calculate_textual_similarities(files, contents)
matrix = analyzer.build_matrix(files, sims)
pairs  = analyzer.get_suspicious_pairs(sims, threshold=0.7)
```

---

## Cache em disco (`core/persistence.py`)

```python
from core.persistence import AnalysisCache

cache = AnalysisCache(cache_dir='.niklaus_cache')

# Salvar
cache.save(files, threshold, results, contents=contents, language='python')

# Carregar (None se não encontrado ou expirado)
data = cache.load(files, threshold, contents=contents, language='python')

# max_age_hours=0 → bypass (útil em testes)
data = cache.load(files, threshold, max_age_hours=0)

# Limpeza
removed = cache.clear_old_cache(max_age_days=7)
removed = cache.clear_all_cache()

# Estatísticas (sem abrir arquivos)
stats = cache.get_cache_stats()
# {'file_count': N, 'active_count': N, 'expired_count': N, ...}
```

O formato é JSON (não pickle). O timestamp de expiração é codificado no nome do arquivo:
```
analysis_{content_sig}_{threshold:.2f}_{expire_ts}.json
```

`clear_old_cache()` filtra por nome de arquivo — sem I/O desnecessário.

---

## Repositórios (`auth/repository.py`)

Use o padrão Repository para acesso a dados. Sempre envolva `get_session()` em um context manager:

```python
from auth.database import get_session, session_scope
from auth.repository import UserRepository, SubmissionRepository
from contextlib import closing

# Leitura simples
with closing(get_session()) as db:
    user_repo = UserRepository(db)
    user = user_repo.find_by_email('alice@example.com')

# Escrita com rollback automático
with session_scope() as db:
    submission_repo = SubmissionRepository(db)
    sub = submission_repo.create(
        user_id=user.id,
        filename='turma.zip',
        language='python',
        threshold=0.7,
        files_count=20,
        suspicious_pairs_count=3,
        status='completed',
    )
```

### Filtros SQL no histórico

`find_by_user()` aceita filtros que são aplicados no banco (não em Python):

```python
from datetime import datetime

subs = submission_repo.find_by_user(
    user_id=42,
    limit=50,
    offset=0,
    status='completed',
    date_start=datetime(2025, 1, 1),
    date_end=datetime(2025, 12, 31),
    min_similarity=0.5,
    max_similarity=1.0,
    use_cache=False,
)
```

### Bulk delete

```python
count = submission_repo.delete_all_by_user(user_id=42)
# DELETE FROM submissions WHERE user_id = 42
```

### Contadores de usuário

`SubmissionRepository.create()` incrementa automaticamente:
- `User.submissions_count`
- `User.total_analyses`
- `User.total_suspicious_pairs`
- `User.last_submission_at`

---

## Exportação (`export/service.py`)

```python
from export.service import ExportService

# JSON completo — bytes UTF-8
json_bytes = ExportService.to_json(results)

# CSV de pares suspeitos — bytes UTF-8 BOM (Excel compatível)
csv_bytes = ExportService.to_csv(results)

# CSV de métricas por arquivo
summary_bytes = ExportService.to_summary_csv(results)

# Uso no Streamlit
st.download_button("Download JSON", data=json_bytes, file_name="niklaus.json", mime="application/json")
st.download_button("Download CSV", data=csv_bytes, file_name="niklaus.csv", mime="text/csv")
```

---

## Autenticação OAuth

### Fluxo completo

```
Usuário → "Login com Google"
    ↓
app.py: _start_oauth_login('google')
    ↓ cria state = OAuthHandler.create_state('google')   # provider:nonce:hmac
    ↓ salva em st.session_state['oauth_provider'] e ['oauth_state']
    ↓ redireciona via <meta http-equiv="refresh">
    ↓
Google → http://localhost:8501?code=XYZ&state=provider:nonce:sig
    ↓
app.py: _handle_oauth_callback()
    ↓ OAuthHandler.verify_state_signature(state)   # valida HMAC
    ↓ OAuthHandler(provider).handle_callback(code, state)
    ↓   troca code por access_token
    ↓   obtém perfil do usuário
    ↓   encrypt_token(access_token)  # Fernet/AES-128
    ↓   create_user_from_oauth(...)  # upsert no DB
    ↓
SessionManager.login(user_dict)
    ↓
st.rerun() → app principal
```

### API OAuth

```python
from auth.oauth import OAuthHandler
from auth.config import OAuthConfig, encrypt_token, decrypt_token

# Criar estado assinado (provider + nonce + hmac)
state = OAuthHandler.create_state('google')

# Validar estado recebido no callback
is_valid = OAuthHandler.verify_state_signature(state)

# Extrair provider do estado (antes de verificar o HMAC)
provider = OAuthHandler.extract_provider_from_state(state)

# Obter URL de autorização (sem side effects em session_state)
handler = OAuthHandler('google')
url = handler.get_authorization_url(state=state)

# Processar callback (retorna objeto User ou None)
user_obj = handler.handle_callback(code, state, expected_state=state)

# Criptografia de tokens
ciphertext = encrypt_token("ya29.access-token")
plaintext  = decrypt_token(ciphertext)
```

### Chave secreta

A `NIKLAUS_SECRET_KEY` em `.streamlit/secrets.toml` serve para:
1. Assinar o estado OAuth com HMAC-SHA256 (proteção contra CSRF).
2. Derivar a chave Fernet para criptografar tokens OAuth no banco.

Se ausente, um aviso é emitido e um fallback fraco baseado nos secrets OAuth é usado.

---

## Exceções

```python
from utils.exceptions import (
    NiklausError,           # base
    FileValidationError,    # ZIP/arquivo inválido
    ZipExtractionError,     # falha na extração
    LanguageDetectionError, # extensão não suportada
    MaritacaAPIError,       # falha na API Maritaca
    RateLimitError,         # rate limit excedido
    AnalysisError,          # falha na análise
    AnalysisCancelledError, # cancelado pelo usuário
    CacheError,             # falha no cache
    ConfigurationError,     # configuração inválida
    ParallelProcessingError,# falha no pool de threads
    raise_if_cancelled,     # helper de cancelamento
)
```

Sempre use `raise ... from e` ao encadear exceções:

```python
try:
    result = do_something()
except SomeError as e:
    raise NiklausError("contexto") from e
```

---

## Performance monitoring

```python
from utils.performance import track_performance, PerformanceContext, get_performance_metrics

@track_performance('my.operation')
def my_function():
    ...

with PerformanceContext('file.upload'):
    process_files(files)

metrics = get_performance_metrics()
dashboard = get_performance_dashboard()
```

---

## Configuração global

```python
from utils.config import config

config.MARITACA_MODEL      # 'sabiazinho-4'
config.MARITACA_TIMEOUT    # 30
config.MAX_ZIP_SIZE_MB     # 50
config.PARALLEL_WORKERS    # 4
config.DEFAULT_THRESHOLD   # 0.7
config.CACHE_EXPIRY_HOURS  # 24
config.LANGUAGE_EXTENSIONS # {'Python': 'py', 'Java': 'java', ...}
```

Override via variável de ambiente:
```bash
PARALLEL_WORKERS=8 streamlit run app.py
```

---

## Lazy loading

Módulos pesados (Plotly, NetworkX, scipy) são carregados sob demanda:

```python
from utils.lazy_loader import LazyModule

plotly = LazyModule('plotly.graph_objects')
nx     = LazyModule('networkx')

# O import real acontece aqui
fig = plotly.Figure()
```

---

## Banco de dados

### Schema atual

**users**
- `id`, `email` (unique), `name`, `role` (user/admin)
- `oauth_provider`, `oauth_id`
- `oauth_access_token`, `oauth_refresh_token` — **criptografados com Fernet**
- `oauth_token_expires_at`
- `avatar_url`, `locale`, `timezone`
- `is_active`, `is_verified`
- `settings` (JSON)
- `submissions_count`, `total_analyses`, `total_suspicious_pairs` — contadores denormalizados
- `created_at`, `updated_at`, `last_login_at`, `last_submission_at`

**submissions**
- `id`, `user_id` (FK cascade delete)
- `filename`, `language`, `threshold`, `max_workers`, `enable_ai`, `use_cache`
- `files_count`, `suspicious_pairs_count`, `average_similarity`, `max_similarity`, `analysis_time_seconds`
- `status` (pending/processing/completed/error), `error_message`
- `analysis_data` (JSON — schema v2)
- `created_at`, `processed_at`

**analysis_cache**, **audit_log** — consulte `auth/models.py`

### Session scope

```python
from auth.database import session_scope

with session_scope() as db:
    # commit automático no final; rollback em exceção
    db.add(SomeModel(...))
```

### Inicializar banco

```bash
python scripts/init_db.py
python scripts/create_admin.py   # cria admin via prompt
```

---

## Deploy

### Desenvolvimento

```bash
streamlit run app.py
```

### Produção (exemplo)

```bash
# Variáveis de ambiente
export DATABASE_URL="postgresql://user:pass@host:5432/niklaus"
export NIKLAUS_SECRET_KEY="chave-aleatoria-longa"
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0

streamlit run app.py
```

Requisitos adicionais para produção:
- HTTPS (configurar via proxy reverso: nginx, Caddy)
- PostgreSQL em vez de SQLite
- Backup automático do banco
- Rotação periódica de `NIKLAUS_SECRET_KEY` (invalida tokens criptografados — usuários precisam fazer login novamente)

---

## FAQ

**Como adicionar um novo provedor OAuth?**
1. Adicione campos em `auth/config.py` (`_load` no `__init__`).
2. Implemente `get_authorization_url`, `_exchange_code_for_token` e `_get_user_profile` para o provider em `auth/oauth.py`.
3. Adicione o provider em `OAuthHandler.__init__` e `self.providers`.
4. Exiba o botão de login em `app.py: _render_auth_page()`.

**Como criar uma nova aba?**
1. Crie `ui/tabs/minha_aba.py` com `def render_minha_aba(results, settings): ...`
2. Importe e registre em `app.py: _render_authenticated_app()`.

**Como desabilitar o cache em testes?**
```python
pipeline = AnalysisPipeline(language='python', use_cache=False)
# ou
cache.load(files, threshold, max_age_hours=0)  # sempre retorna None
```

**Como limpar o cache em disco?**
```python
from core.persistence import AnalysisCache
AnalysisCache().clear_all_cache()
```

**Como rodar apenas testes rápidos?**
```bash
pytest tests/ -k "not slow"
```

---

## Contato

- Issues: [GitHub Issues](https://github.com/walternagai/niklaus-plagiarism/issues)
- E-mail: [walternagai@unifei.edu.br](mailto:walternagai@unifei.edu.br)
