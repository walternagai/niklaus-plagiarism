# Análise do Fluxo de Renderização

## Problema Identificado

Quando o usuário clica em "Carregar Resultados" na aba Histórico:

### Fluxo Atual (COM ERRO):

```
1. Usuário carrega uma análise do histórico
   ↓
2. history.py salva em session_state['last_analysis']
   ↓
3. st.rerun() é chamado
   ↓
4. Página recarrega
   ↓
5. app.py linha 348: render_upload_tab() é executado na TAB1
   ↓
6. upload.py linha 31-49: Detecta last_analysis e mostra "Nova Análise" / "Ver Última Análise"
   ↓
7. should_analyze = False (não clicou em "Analisar")
   ↓
8. app.py linha 373: Verifica SE session_state['last_analysis'] existe
   ↓
9. PROBLEMA: A condição é verdadeira, MAS o código das abas 2-5 NÃO É EXECUTADO
      PORQUE A VARIÁVEL should_analyze foi definida ANTES DO if
      E SE should_analyze foi definido na TAB1, o código pode estar em estado inconsistente
```

### Análise do Código:

**app.py (linhas 347-400):**

```python
# Linha 347: TAB1 é renderizada
with tab1:
    files, contents, extract_path, should_analyze = render_upload_tab(settings)
    
    # Linha 350: SE should_analyze E files E contents
    if should_analyze and files and contents:
        # Executa análise...
        st.rerun()

# Linha 373: SE last_analysis existe
if st.session_state.get('last_analysis'):
    results = st.session_state['last_analysis']
    settings = st.session_state.get('settings', {})
    
    # Renderiza abas 2-5
    with tab2:
        render_results_tab(results, settings)
    # etc...

# Linha 392: SE NÃO last_analysis
else:
    if not should_analyze:
        # Mostra "Nenhum resultado disponível"
```

### Variáveis de Estado:

1. **last_analysis** - Armazena resultados da análise
2. **settings** - Configurações da análise
3. **should_analyze** - Flag indicando se deve iniciar análise (bool)
4. **loaded_submission_id** - ID da submissão carregada do histórico

### Conflitos Encontrados:

1. **Conflito de Estado**: `should_analyze` é definido na TAB1, mas as abas 2-5 são renderizadas FORA do `with tab1:`.

2. **Condição Conflitante**: A linha 373-390 renderiza as abas 2-5 SE `last_analysis` existe. Mas a linha 392-399 mostra mensagem de erro SE NÃO `last_analysis` E NÃO `should_analyze`.

3. **upload.py Mostra Botões Mesmo com Dados**: A linha 31 verifica se `last_analysis` existe e mostra botões "Nova Análise" / "Ver Última Análise", mas isso NÃO garante que as outras abas vão mostrar os dados.

4. **Condição Redundante**: `else: if not should_analyze:` é confusa. Deveria ser apenas `else:`.

5. **Falta de Sincronização**: Quando `st.rerun()` é chamado em `history.py`, a página recarrega, mas o `render_upload_tab` é executado ANTES das outras abas serem verificadas.

### Solução Proposta:

A lógica deve ser:

```python
# Sempre renderizar a TAB1 (Upload)
with tab1:
    files, contents, extract_path, should_analyze = render_upload_tab(settings)
    
    if should_analyze and files and contents:
        # Executa análise
        results = _run_analysis(...)
        st.session_state['last_analysis'] = results
        st.rerun()

# Verificar last_analysis FORA de todas as tabs
if st.session_state.get('last_analysis'):
    # Renderizar abas 2-5 COM DADOS
    with tab2:
        render_results_tab(results, settings)
    # etc...
else:
    # NÃO há dados - mostrar mensagem nas abas 2-5
    with tab2:
        st.info("Nenhum resultado disponível...")
    # etc...

# SEMPRE renderizar TAB6 (Histórico)
with tab6:
    render_history_tab(current_user.id)
```

### Bugs Específicos:

1. **Linha 393**: `if not should_analyze` é redundante e confuso
2. **Variável `should_analyze`**: Definida na TAB1, mas usada FORA do contexto
3. **Falta de Clear de Estado**: Quando carrega do histórico, não limpa estado anterior