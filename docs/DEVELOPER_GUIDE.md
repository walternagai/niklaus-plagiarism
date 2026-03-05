# Guia do Desenvolvedor - Niklaus Plagiarism Detector

## Arquitetura do Sistema

### Visão Geral

O Niklaus é um detector de plágio modular com as seguintes camadas:

```
┌─────────────────────────────────────────┐
│         Interface (UI/Streamlit)         │
│   - app.py (Main Application)            │
│   - ui/ (Componentes)                     │
│   - tabs/ (Abas)                          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Lógica de Negócio                │
│   - core/ (Analise)                       │
│   - auth/ (Autenticação)                 │
│   - utils/ (Utilitários)                 │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Persistência                     │
│   - Database (SQLAlchemy)                │
│   - Cache (Disk + Query Cache)          │
└─────────────────────────────────────────┘
```

## Estrutura de Diretórios

```
niklaus-plagiarism/
├── app.py                    # Aplicação principal
├── core/                     # Motor de análise
│   ├── analyzer.py          # Analisador principal
│   ├── pipeline.py          # Pipeline de análise
│   ├── file_handler.py      # Manipulação de arquivos
│   ├── llm_client.py        # Cliente Maritaca AI
│   ├── comparison.py        # Comparação textual
│   └── persistence.py       # Cache em disco
├── auth/                     # Sistema de autenticação
│   ├── models.py            # Modelos SQLAlchemy
│   ├── database.py          # Gerenciador DB
│   ├── repository.py        # Repositórios
│   ├── oauth.py             # Handler OAuth
│   ├── config.py            # Configuração OAuth
│   ├── session.py           # Gerenciador de sessão
│   └── decorators.py        # Decorators de auth
├── ui/                       # Interface do usuário
│   ├── sidebar.py           # Sidebar
│   ├── tutorial.py          # Tutorial interativo
│   ├── tooltips.py          # Tooltips e ajuda
│   ├── auth/                # UI de autenticação
│   ├── components/          # Componentes reutilizáveis
│   └── tabs/                # Abas da aplicação
│       ├── upload.py
│       ├── results.py
│       ├── statistics.py
│       ├── advanced.py
│       ├── graph.py
│       ├── history.py
│       └── performance.py   # Dashboard de performance
├── utils/                    # Utilitários
│   ├── config.py            # Configurações globais
│   ├── logger.py            # Logging
│   ├── exceptions.py        # Exceções customizadas
│   ├── error_handling.py    # Tratamento de erros
│   ├── lazy_loader.py       # Lazy loading
│   ├── db_cache.py          # Cache de queries
│   └── performance.py       # Métricas de performance
├── tests/                    # Testes automatizados
└── scripts/                  # Scripts utilitários
```

## Componentes Principais

### 1. Pipeline de Análise (`core/pipeline.py`)

O pipeline coordena todas as etapas de análise:

```python
from core.pipeline import AnalysisPipeline

pipeline = AnalysisPipeline(
    language='Python',
    api_key='your_api_key',
    max_workers=4,
    use_cache=True
)

results = pipeline.run_full_analysis(
    files=file_list,
    contents=content_list,
    threshold=0.7,
    enable_ai=True,
    progress_callback=callback
)
```

**Etapas do Pipeline:**
1. Análise Textual (similaridade de código)
2. Análise AST (árvore sintática)
3. Métricas de Código (complexidade, estilo)
4. Clustering (agrupamento)
5. Análise IA (opcional, via Maritaca)

### 2. Sistema de Cache (`utils/db_cache.py`)

Cache de queries com TTL (Time-To-Live):

```python
from utils.db_cache import cached_query, get_query_cache

@cached_query(ttl=300, key_prefix='submissions_')
def get_user_submissions(user_id: int):
    # Query cached por 5 minutos
    return db.query(Submission).filter(...).all()

# Estatísticas do cache
stats = get_query_cache().get_stats()
print(f"Hit rate: {stats['hit_rate']:.2f}%")
```

### 3. Performance Monitoring (`utils/performance.py`)

Decorações para rastreamento de performance:

```python
from utils.performance import track_performance, PerformanceContext

@track_performance('database.query')
def expensive_query():
    # Automaticamente rastreia tempo de execução
    return db.query(...)

with PerformanceContext('file.upload'):
    # Rastreia tempo de execução do bloco
    process_files(files)
```

### 4. Lazy Loading (`utils/lazy_loader.py`)

Carregamento sob demanda de componentes:

```python
from utils.lazy_loader import LazyModule, LazyTabLoader

# Lazy import de módulos pesados
plotly = LazyModule('plotly.graph_objects')
networkx = LazyModule('networkx')

# Lazy loading de abas
loader = LazyTabLoader()
if loader.is_tab_loaded('results'):
    # Aba já carregada
    data = loader.get_tab_data('results')
```

### 5. Tutorial Interativo (`ui/tutorial.py`)

Sistema de onboarding guiado:

```python
from ui.tutorial import start_tutorial, render_tutorial_step

# Iniciar tutorial
start_tutorial('getting_started')

# Renderizar passo atual
render_tutorial_step('getting_started')
```

## Banco de Dados

### Modelos

**User:**
```python
class User(Base):
    id: int
    email: str
    name: str
    role: str  # 'user', 'admin'
    is_active: bool
    oauth_provider: str
    oauth_id: str
    created_at: datetime
    last_login_at: datetime
```

**Submission:**
```python
class Submission(Base):
    id: int
    user_id: int
    filename: str
    language: str
    status: str  # 'pending', 'processing', 'completed', 'error'
    files_count: int
    suspicious_pairs_count: int
    average_similarity: float
    max_similarity: float
    analysis_data: dict
    created_at: datetime
    processed_at: datetime
```

### Repositórios

Use o padrão Repository para acesso a dados:

```python
from auth.repository import UserRepository, SubmissionRepository
from auth.database import get_session

db = get_session()
user_repo = UserRepository(db)
submission_repo = SubmissionRepository(db)

# Criar usuário
user = user_repo.create(
    email='user@example.com',
    name='User Name',
    oauth_provider='google',
    oauth_id='123456'
)

# Buscar submissões com cache
submissions = submission_repo.find_by_user(
    user_id=user.id,
    limit=50,
    offset=0,
    use_cache=True
)
```

## Configuração

### Variáveis de Ambiente

Crie `.streamlit/secrets.toml`:

```toml
[google]
client_id = "your_google_client_id"
client_secret = "your_google_client_secret"
redirect_uri = "http://localhost:8501"

[github]
client_id = "your_github_client_id"
client_secret = "your_github_client_secret"

[microsoft]
client_id = "your_microsoft_client_id"
client_secret = "your_microsoft_client_secret"

[maritaca]
MARITACA_API_KEY = "your_maritaca_api_key"
MARITACA_MODEL = "sabiazinho-4"

ADMIN_EMAILS = "admin1@example.com,admin2@example.com"
```

### Configuração Global (`utils/config.py`)

```python
from utils.config import config

# Acessar configurações
default_threshold = config.DEFAULT_THRESHOLD  # 0.7
max_workers = config.PARALLEL_WORKERS  # 4
language_extensions = config.LANGUAGE_EXTENSIONS  # {'Python': 'py', ...}
```

## Autenticação OAuth

### Fluxo de Autenticação

1. Usuário clica em "Login com Google/GitHub/Microsoft"
2. Sistema gera URL de autorização OAuth
3. Usuário é redirecionado para o provider
4. Provider redireciona de volta com `code` e `state`
5. Sistema troca `code` por token de acesso
6. Sistema obtém dados do usuário
7. Sistema cria/atualiza usuário no banco
8. Sistema cria sessão

### Implementação

```python
from auth import OAuthHandler, SessionManager

# Iniciar login
handler = OAuthHandler('google')
auth_url = handler.get_authorization_url()

# Callback após autenticação
user_info = handler.handle_callback(code, state)
session_manager = SessionManager()
session_manager.login(user_info)
```

### Decorators

```python
from auth.decorators import require_auth, require_admin

@require_auth
def protected_view():
    # Apenas usuários autenticados
    pass

@require_admin
def admin_view():
    # Apenas administradores
    pass
```

## Testes

### Executar Testes

```bash
# Todos os testes
pytest tests/

# Testes específicos
pytest tests/test_pipeline.py

# Com cobertura
pytest tests/ --cov=. --cov-report=html
```

### Estrutura de Testes

```python
import pytest
from core.pipeline import AnalysisPipeline

def test_pipeline_initialization():
    pipeline = AnalysisPipeline(language='Python')
    assert pipeline.language == 'Python'
    assert pipeline.max_workers == 4

def test_textual_analysis():
    pipeline = AnalysisPipeline(language='Python')
    results = pipeline.run_textual_analysis(
        files=['file1.py', 'file2.py'],
        contents=['print("hello")', 'print("world")']
    )
    assert 'similarity_matrix' in results
```

## Performance

### Otimizações Implementadas

1. **Lazy Loading**: Módulos pesados carregados sob demanda
2. **Query Cache**: Resultados de DB cacheados com TTL
3. **Performance Tracking**: Métricas de tempo de execução
4. **Parallel Processing**: Análise paralela com ThreadPoolExecutor
5. **Memory Optimization**: Limpeza de cache automática

### Monitorar Performance

```python
from utils.performance import get_performance_dashboard

# Dashboard completo
dashboard = get_performance_dashboard()
print(f"Total calls: {dashboard['summary']['total_calls']}")
print(f"Success rate: {dashboard['summary']['overall_success_rate']:.1f}%")

# Top operações lentas
for op in dashboard['top_slow']:
    print(f"{op['name']}: {op['avg_time']:.4f}s")
```

### Cache Stats

```python
from utils.db_cache import get_cache_stats

stats = get_cache_stats()
print(f"Cache hits: {stats['query_cache']['hits']}")
print(f"Hit rate: {stats['query_cache']['hit_rate']:.1f}%")
```

## Debugging

### Logs

```python
from utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Message")
logger.warning("Warning")
logger.error("Error", exc_info=True)
```

### Desabilitar Cache (Desenvolvimento)

```python
# Na sessão Streamlit
st.session_state['query_cache_enabled'] = False
```

## Deploy

### Requisitos

- Python 3.9+
- SQLite ou PostgreSQL
- Streamlit Cloud, heroku, ou servidor próprio

### Passos

1. Configure secrets
2. Instale dependências: `pip install -r requirements.txt`
3. Inicialize DB: `python scripts/init_db.py`
4. Execute: `streamlit run app.py`

### Variáveis de Produção

```bash
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
DATABASE_URL=postgresql://...
```

## Contribuindo

1. Fork o repositório
2. Crie branch: `git checkout -b feature/nova-feature`
3. Commit: `git commit -m 'Adiciona nova feature'`
4. Push: `git push origin feature/nova-feature`
5. Abra Pull Request

### Padrões de Código

- Siga PEP 8
- Escreva docstrings
- Adicione testes
- Atualize documentação

## FAQ

**Q: Como adicionar novo provider OAuth?**

A: Crie handler em `auth/oauth.py` e adicione configuração em `auth/config.py`.

**Q: Como criar nova aba?**

A: Crie arquivo em `ui/tabs/` e importe em `app.py`.

**Q: Como otimizar queries lentas?**

A: Use `@cached_query` decorator ou implemente cache específico.

**Q: Como limpar cache?**

A: Use `clear_all_caches()` de `utils.db_cache`.

## Contato

- Issues: [GitHub Issues](https://github.com/walternagai/niklaus-plagiarism/issues)
- Email: dev@example.com