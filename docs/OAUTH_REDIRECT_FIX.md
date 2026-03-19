# Configuração de Redirect URI para OAuth

## Regra fundamental

O Streamlit não tem roteamento por path — todas as páginas são renderizadas em `/`. Por isso, o redirect URI OAuth **deve apontar para a URL base**, sem sufixo `/oauth/callback/...`:

```
✅  http://localhost:8501
❌  http://localhost:8501/oauth/callback/google
```

Configure o mesmo valor no console do provedor e em `secrets.toml`.

---

## secrets.toml

```toml
NIKLAUS_SECRET_KEY = "chave-aleatoria"   # assina o estado OAuth

[google]
client_id     = "GOOGLE_CLIENT_ID"
client_secret = "GOOGLE_CLIENT_SECRET"
redirect_uri  = "http://localhost:8501"

[github]
client_id     = "GITHUB_CLIENT_ID"
client_secret = "GITHUB_CLIENT_SECRET"
redirect_uri  = "http://localhost:8501"

[microsoft]
client_id     = "MICROSOFT_CLIENT_ID"
client_secret = "MICROSOFT_CLIENT_SECRET"
tenant_id     = "common"
redirect_uri  = "http://localhost:8501"

ADMIN_EMAILS = "seu.email@exemplo.com"
```

---

## Como configurar cada provedor

### Google Cloud Console
1. **APIs & Services → Credentials** → selecione sua credencial OAuth.
2. Em **Authorized redirect URIs**, adicione:
   - `http://localhost:8501` (desenvolvimento)
   - `https://seudominio.com` (produção — apenas HTTPS)
3. Em **Authorized JavaScript origins**, adicione a mesma URL.

### GitHub
1. **Settings → Developer settings → OAuth Apps** → selecione o app.
2. Em **Authorization callback URL**: `http://localhost:8501`

### Microsoft (Entra ID)
1. **Azure Portal → App registrations** → selecione o app.
2. **Authentication → Platform configurations → Web → Redirect URIs**: `http://localhost:8501`

---

## Fluxo implementado

```
Usuário clica "Login com Google"
  ↓
app.py: _start_oauth_login('google')
  → state = OAuthHandler.create_state('google')   # google:nonce:hmac
  → st.session_state['oauth_provider'] = 'google'
  → st.session_state['oauth_state'] = state
  → redireciona para URL de autorização Google

Google authentica → redireciona para:
  http://localhost:8501?code=AUTH_CODE&state=google:nonce:hmac

app.py carrega → _handle_oauth_callback()
  → recupera provider do signed state (ou session_state)
  → OAuthHandler.verify_state_signature(state)   # valida HMAC
  → OAuthHandler.handle_callback(code, state)
    → troca code por access_token
    → obtém perfil do usuário
    → criptografa tokens (Fernet)
    → upsert no banco
  → SessionManager.login(user_dict)
  → st.query_params.clear()
  → st.rerun() → app principal
```

### Proteção de estado OAuth

O `state` transporta o provider de forma segura e autenticada:

```
formato: {provider}:{nonce_24chars}:{hmac_sha256[:24]}
exemplo: google:ABCxyz123456789012345:a1b2c3d4e5f6g7h8i9j0k1l2
```

O HMAC é calculado com `NIKLAUS_SECRET_KEY`. Uma falha na verificação rejeita o callback imediatamente — o usuário vê "Sessão de login inválida ou expirada".

---

## Problemas comuns

| Erro | Causa | Solução |
|---|---|---|
| `redirect_uri_mismatch` | redirect_uri no `secrets.toml` diferente do console do provedor | Torne os valores idênticos (maiúsc./minúsc., trailing slash) |
| `Provider: não encontrado` | Provider não recuperado nem da sessão nem do state | Inicie o login novamente; verifique `NIKLAUS_SECRET_KEY` |
| `Sessão de login inválida` | HMAC falhou — state adulterado ou `NIKLAUS_SECRET_KEY` mudou | Inicie o login novamente |
| Tela branca após callback | redirect_uri aponta para path errado ou app não iniciado | Use apenas a URL base (`http://localhost:8501`) |
| `Access blocked: app is pending` | App do Google em modo de teste | Adicione o e-mail como Test User no console |

---

## Checklist

- [ ] redirect_uri = `http://localhost:8501` (sem path) no `secrets.toml`
- [ ] Mesmo valor no console do provedor
- [ ] `NIKLAUS_SECRET_KEY` configurado
- [ ] App reiniciado após mudanças no `secrets.toml`
- [ ] Cache do navegador limpo (`Ctrl+Shift+R`)
- [ ] Para produção: HTTPS e redirect_uri atualizado para `https://...`

---

## Teste rápido

```bash
# Verificar configuração OAuth (sem Streamlit rodando)
python scripts/test_oauth_config.py

# Iniciar app
streamlit run app.py
```

Acesse `http://localhost:8501` → clique em um botão de login → autentique no provedor → deve retornar ao app com "✅ Bem-vindo, Nome!".
