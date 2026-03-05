# Guia de Configuração OAuth

## 🔑 Configuração Correta do Redirect URI

Para OAuth funcionar com Streamlit, **NÃO** use URLs como:
```
❌ http://localhost:8501/oauth/callback/google
``

Use **apenas a URL base**:
```
✅ http://localhost:8501
```

## 📋 Passos para Configurar Google OAuth

### 1. No Google Cloud Console

1. Acesse: https://console.cloud.google.com/
2. Vá em **APIs & Services** → **Credentials**
3. Crie ou edite suas credenciais OAuth 2.0
4. Configure:

**Authorized JavaScript origins:**
```
http://localhost:8501
```

**Authorized redirect URIs:**
```
http://localhost:8501
```

⚠️ **IMPORTANTE:** NÃO adicione `/oauth/callback/google` - use apenas a URL base!

### 2. No `.streamlit/secrets.toml`

```toml
[google]
client_id = "YOUR_GOOGLE_CLIENT_ID_HERE"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET_HERE"
redirect_uri = "http://localhost:8501"

[github]
client_id = "YOUR_GITHUB_CLIENT_ID"
client_secret = "YOUR_GITHUB_CLIENT_SECRET"
redirect_uri = "http://localhost:8501"

[microsoft]
client_id = "YOUR_MICROSOFT_CLIENT_ID"
client_secret = "YOUR_MICROSOFT_CLIENT_SECRET"
redirect_uri = "http://localhost:8501"
tenant_id = "common"

ADMIN_EMAILS = "seu.email@gmail.com"
```

## 🔄 Fluxo OAuth Corrigido

### O que mudou:

**Antes (quebrado):**
```
Usuário → Google OAuth → http://localhost:8501/oauth/callback/google
                              ↓
                        ❌ Página não existe no Streamlit MultiPage
```

**Depois (corrigido):**
```
Usuário → Google OAuth → http://localhost:8501?code=XYZ&state=ABC
                              ↓
                        ✅ app.py processa callback via query_params
                              ↓
                         Login realizado → Redireciona para app principal
```

## 🧪 Testando a Configuração

1. **Teste OAuth Config:**
   ```bash
   python scripts/test_oauth_config.py
   ```

2. **Inicie o app:**
   ```bash
   streamlit run app.py
   ```

3. **Acesse:** `http://localhost:8501`

4. **Clique em:** "Login com Google"

5. **Resultado esperado:**
   - Redireciona para Google
   - Após autorização, volta para `http://localhost:8501?code=XYZ&state=ABC`
   - Processa login automaticamente
   - Mostra "✅ Bem-vindo, {nome}!"
   - Redireciona para página principal

## 🐛 Problemas Comuns

### "Página em branco após OAuth"

**Causa:** redirect_uri incorreto no Google Cloud Console

**Solução:** Configure redirect_uri como:
- ✅ `http://localhost:8501`
- ❌ `http://localhost:8501/oauth/callback/google`

### "redirect_uri_mismatch"

**Causa:** redirect_uri no app diferente do Google Cloud Console

**Solução:** Mantenha o mesmo valor em ambos:
- `secrets.toml` → `redirect_uri = "http://localhost:8501"`
- Google Cloud Console → Authorized redirect URIs → `http://localhost:8501`

### "Access blocked: app is pending"

**Causa:** App em modo de teste no Google Cloud Console

**Solução:** Adicione seu email como **Test User** ou publique o app

## 📝 Checklist

- [ ] Redirect URI configurado como `http://localhost:8501` (sem `/oauth/callback`)
- [ ] Client ID e Client Secret no `.streamlit/secrets.toml`
- [ ] redirect_uri idêntico no Google Cloud Console e no app
- [ ] ADMIN_EMAILS configurado corretamente
- [ ] App reiniciado após mudanças
- [ ] Cache do navegador limpo (Ctrl+Shift+R)