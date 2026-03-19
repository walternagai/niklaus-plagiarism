# Guia de Autenticação

Referência para configurar e operar o sistema de autenticação OAuth do Niklaus.

---

## Pré-requisitos

1. Python 3.9+ e dependências instaladas: `pip install -r requirements.txt`
2. Banco de dados inicializado: `python scripts/init_db.py`
3. Pelo menos um provedor OAuth configurado (Google, GitHub ou Microsoft)

---

## Configuração rápida

```bash
cp secrets.toml.example .streamlit/secrets.toml
# Edite .streamlit/secrets.toml com suas credenciais
streamlit run app.py
```

---

## Arquivo `.streamlit/secrets.toml`

```toml
# ─── Chave de segurança da aplicação (OBRIGATÓRIO) ───────────────────────────
# Usada para:
#   1. Assinar o estado OAuth com HMAC-SHA256 (proteção CSRF)
#   2. Derivar a chave Fernet para criptografar tokens OAuth no banco
# Gere com: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
NIKLAUS_SECRET_KEY = "sua-chave-aleatoria-longa"

# ─── Admins ──────────────────────────────────────────────────────────────────
# Emails separados por vírgula. Esses usuários recebem role='admin' ao fazer login.
ADMIN_EMAILS = "voce@exemplo.com,outro@exemplo.com"

# ─── Maritaca AI ─────────────────────────────────────────────────────────────
[maritaca]
MARITACA_API_KEY = "sua-chave-maritaca"
MARITACA_MODEL   = "sabiazinho-4"

# ─── Google OAuth ────────────────────────────────────────────────────────────
[google]
client_id     = "xxxx.apps.googleusercontent.com"
client_secret = "GOCSPX-xxxx"
redirect_uri  = "http://localhost:8501"   # sem /oauth/callback/...

# ─── GitHub OAuth ────────────────────────────────────────────────────────────
[github]
client_id     = "Ov23lixxxx"
client_secret = "xxxxxxxx"
redirect_uri  = "http://localhost:8501"

# ─── Microsoft OAuth ─────────────────────────────────────────────────────────
[microsoft]
client_id     = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
client_secret = "xxxxxxxx"
tenant_id     = "common"   # ou o tenant ID da sua organização
redirect_uri  = "http://localhost:8501"
```

> O arquivo `.streamlit/secrets.toml` já está no `.gitignore`. **Nunca o versione.**

---

## Configurar provedores OAuth

### Google

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie ou selecione um projeto.
3. Ative a **Google+ API** (ou **Google Identity**).
4. Vá em **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
5. Tipo: **Web application**.
6. Authorized redirect URIs: `http://localhost:8501` (apenas a URL base — sem `/oauth/callback`).
7. Copie **Client ID** e **Client Secret** para `secrets.toml`.

### GitHub

1. Acesse **GitHub Settings → Developer settings → OAuth Apps → New OAuth App**.
2. Application name: Niklaus
3. Homepage URL: `http://localhost:8501`
4. Authorization callback URL: `http://localhost:8501`
5. Copie **Client ID** e **Client Secret** para `secrets.toml`.

### Microsoft (Entra ID / Azure AD)

1. Acesse [Azure Portal](https://portal.azure.com/) → **Azure Active Directory → App registrations → New registration**.
2. Nome: Niklaus.
3. Redirect URI: Web → `http://localhost:8501`
4. Copie o **Application (client) ID**.
5. Em **Certificates & secrets → New client secret**, copie o valor.
6. Preencha `secrets.toml` com `client_id`, `client_secret` e `tenant_id`.

> Para produção, use URLs HTTPS e atualize os redirect URIs no provedor e no `secrets.toml`.

---

## Criar usuário administrador

### Via OAuth (automático)
Inclua o e-mail em `ADMIN_EMAILS` — o usuário receberá `role='admin'` ao fazer login.

### Via script (criação direta no banco)
```bash
python scripts/create_admin.py
# Informe e-mail e nome quando solicitado
```

---

## Segurança de tokens

Os tokens OAuth (access e refresh) são **criptografados com Fernet/AES-128** antes de serem persistidos no banco de dados.

- A chave de criptografia é derivada de `NIKLAUS_SECRET_KEY` via SHA-256.
- Tokens armazenados sem criptografia (antes desta versão) são lidos com fallback transparente.
- Quando `NIKLAUS_SECRET_KEY` não está configurado, um aviso é emitido e uma chave fraca derivada dos secrets OAuth é usada.

Se você rotacionar `NIKLAUS_SECRET_KEY`, tokens existentes não poderão ser descriptografados — usuários precisarão fazer login novamente.

---

## Estado OAuth e proteção CSRF

Cada fluxo de login gera um `state` no formato:

```
{provider}:{nonce}:{hmac_sha256_truncado_24_chars}
```

Exemplo: `google:ABCDEFabcdef123456789012:a1b2c3d4e5f6g7h8i9j0k1l2`

O `state` é verificado no callback com `OAuthHandler.verify_state_signature()` usando HMAC-SHA256. Uma falha na verificação rejeita o callback.

---

## Fluxo OAuth passo a passo

```
1. Usuário clica "Login com Google"
   → app.py: _start_oauth_login('google')
   → cria state = OAuthHandler.create_state('google')
   → salva state e provider em st.session_state
   → redireciona para Google via <meta http-equiv="refresh">

2. Google autentica o usuário e redireciona para:
   http://localhost:8501?code=AUTHORIZATION_CODE&state=STATE

3. Streamlit recarrega app.py
   → _handle_oauth_callback() detecta 'code' e 'state' nos query_params
   → OAuthHandler.verify_state_signature(state)  [valida HMAC]
   → OAuthHandler('google').handle_callback(code, state)
     → troca code por access_token via POST
     → obtém perfil do usuário via GET
     → encrypt_token(access_token)  [Fernet]
     → upsert no banco (create_user_from_oauth)
   → SessionManager.login(user_dict)
   → st.query_params.clear()
   → st.rerun()

4. App principal renderizado para o usuário autenticado
```

---

## Arquitetura da autenticação

```
auth/
├── models.py      # User, Submission, AnalysisCache, AuditLog (SQLAlchemy)
├── database.py    # DatabaseManager, get_session(), session_scope()
├── repository.py  # UserRepository, SubmissionRepository, CacheRepository, AuditRepository
├── oauth.py       # OAuthHandler — generate URL, callback, HMAC state, token encrypt
├── config.py      # OAuthConfig, NIKLAUS_SECRET_KEY, encrypt_token(), decrypt_token()
├── session.py     # SessionManager (Streamlit session state, expiração 24h)
└── decorators.py  # @require_auth, @require_admin

ui/auth/
├── login.py       # Página de login OAuth
├── dashboard.py   # Dashboard do usuário
├── history.py     # Histórico de submissões
├── profile.py     # Perfil do usuário
└── admin.py       # Painel de administração

scripts/
├── init_db.py     # Cria tabelas
└── create_admin.py # Cria admin manualmente
```

---

## Schema do banco

### Tabela `users`
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | |
| `email` | String unique | |
| `name` | String | |
| `role` | String | `user` ou `admin` |
| `oauth_provider` | String | google / github / microsoft |
| `oauth_id` | String | ID do usuário no provedor |
| `oauth_access_token` | Text | **Criptografado com Fernet** |
| `oauth_refresh_token` | Text | **Criptografado com Fernet** |
| `oauth_token_expires_at` | DateTime | |
| `is_active`, `is_verified` | Boolean | |
| `submissions_count` | Integer | Incrementado automaticamente |
| `total_analyses` | Integer | Incrementado automaticamente |
| `total_suspicious_pairs` | Integer | Incrementado automaticamente |
| `created_at`, `updated_at`, `last_login_at`, `last_submission_at` | DateTime | |

### Tabela `submissions`
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK | Cascade delete |
| `filename` | String | Nome do ZIP |
| `language`, `threshold` | | Configuração usada |
| `files_count`, `suspicious_pairs_count` | Integer | |
| `average_similarity`, `max_similarity` | Float | |
| `status` | String | pending / processing / completed / error |
| `analysis_data` | JSON | Schema v2 (veja `_save_submission` em `app.py`) |
| `created_at`, `processed_at` | DateTime | |

---

## Troubleshooting

### "Provider: não encontrado, Code: ✓, State: ✓"
O provider não foi recuperado nem da sessão nem do estado OAuth.
- Verifique se `NIKLAUS_SECRET_KEY` é idêntico ao usado quando o state foi gerado.
- Tente iniciar o login novamente (o state expira ou pode ser invalidado por reinicialização do servidor).

### "redirect_uri_mismatch"
O `redirect_uri` em `secrets.toml` e no console do provedor devem ser **exatamente iguais** (incluindo protocolo e ausência de trailing slash).

### "Sessão de login inválida ou expirada"
O estado HMAC não passou na verificação. Pode ocorrer se `NIKLAUS_SECRET_KEY` mudou ou se o state foi adulterado. Tente iniciar o login novamente.

### "Database locked"
Use PostgreSQL em produção. SQLite tem limitações de concorrência.

### Tokens não descriptografados após rotação de `NIKLAUS_SECRET_KEY`
Tokens criptografados com a chave anterior tornam-se ilegíveis. Os usuários afetados precisam fazer login novamente para que novos tokens criptografados sejam gerados.

---

## Produção

```bash
# PostgreSQL
export DATABASE_URL="postgresql://user:pass@host:5432/niklaus"

# Secrets via env vars (alternativa ao secrets.toml)
export NIKLAUS_SECRET_KEY="chave-producao"
export GOOGLE_CLIENT_ID="..."
export GOOGLE_CLIENT_SECRET="..."
export GOOGLE_REDIRECT_URI="https://niklaus.seudominio.com"

# Inicializar
python scripts/init_db.py

# Executar
streamlit run app.py --server.port 8501
```

Checklist de produção:
- [ ] HTTPS habilitado (nginx, Caddy ou Cloudflare)
- [ ] `NIKLAUS_SECRET_KEY` configurada com valor forte e aleatório
- [ ] Redirect URIs atualizados para HTTPS nos consoles dos provedores
- [ ] `secrets.toml` fora do repositório
- [ ] Backup automático do banco de dados
- [ ] Revisão periódica dos audit logs
