"""
Tooltip constants for UI components.
Provides helpful explanations for metrics and features.
"""

# Analysis Metrics Tooltips
METRICS_TOOLTIPS = {
    # Basic metrics
    "files_count": "Número total de arquivos analisados no ZIP",
    "suspicious_pairs": "Pares de arquivos com similaridade acima do threshold",
    "average_similarity": "Média aritmética de todas as similaridades entre pares de arquivos",
    "max_similarity": "Maior similaridade encontrada entre qualquer par de arquivos",
    "analysis_time": "Tempo total de análise em segundos",
    
    # Threshold
    "threshold": "Valor mínimo de similaridade para considerar um par como suspeito. Valores mais altos = detecção mais rigorosa",
    
    # Advanced metrics
    "loc": "Linhas de Código (LOC) - Total de linhas não vazias no arquivo",
    "cyclomatic_complexity": "Complexidade Ciclomática - Mede o número de caminhos independentes no código. Valores altos (>15) indicam código difícil de testar",
    "nesting_depth": "Profundidade de Aninhamento - Níveis máximos de indentação. Valores altos (>4) dificultam leitura",
    "maintainability_index": "Índice de Manutenibilidade - 0-100, onde valores mais altos indicam código mais fácil de manter",
    "functions_count": "Número de funções/métodos definidos no arquivo",
    
    # Code metrics explanation
    "halstead_volume": "Volume de Halstead - Mede a quantidade de informação no código baseado em operadores e operandos",
    "halstead_difficulty": "Dificuldade de Halstead - Estimativa de quão difícil é escrever/entender o código",
    "cognitive_complexity": "Complexidade Cognitiva - Mede o quão difícil é entender o código ao ler (quebras de fluxo)",
    
    # AST metrics
    "ast_similarity": "Similaridade Estrutural (AST) - Compara a estrutura do código (loops, condicionais, funções)",
    "textual_similarity": "Similaridade Textual - Compara o conteúdo literal do código (tokens, strings)",
    
    # Performance
    "workers": "Número de threads paralelas para processamento. Mais workers = análise mais rápida (use com cautela)",
    "cache": "Armazena resultados anteriores para evitar reprocessamento. Recomendado manter ativo",
    "ai_analysis": "Análise detalhada usando IA (Maritaca) para detectar padrões de plágio mais complexos",
}

# Feature Tooltips
FEATURES_TOOLTIPS = {
    # Upload features
    "zip_file": "Arquivo ZIP contendo os códigos-fonte a serem analisados",
    "language": "Linguagem de programação dos arquivos. Afeta a análise de estrutura (AST) e métricas",
    "max_workers": "Threads paralelas. Use 1-2 para CPU limitada, 4-8 para máquinas potentes",
    
    # Analysis features
    "enable_ai": "Ativa análise com IA para detectar plágio mais sofisticado (ex: reescrita de código)",
    "use_cache": "Reutiliza resultados de análises anteriores (arquivos iguais)",
    
    # Results features
    "heatmap": "Visualização em mapa de calor das similaridades entre todos os pares de arquivos",
    "similarity_graph": "Grafo de rede mostrando conexões entre arquivos com alta similaridade",
    "radar_chart": "Comparação de métricas de código entre dois arquivos",
    
    # Filters
    "similarity_filter": "Exibe apenas pares com similaridade acima deste valor",
    "date_filter": "Filtra submissões por período",
    "status_filter": "Filtra por status da análise",
}

# Validation Messages
VALIDATION_MESSAGES = {
    "file_too_large": "Arquivo excede o tamanho máximo permitido",
    "file_empty": "O arquivo ZIP está vazio",
    "file_corrupted": "O arquivo ZIP está corrompido ou não pode ser lido",
    "file_invalid_format": "O ZIP contém arquivos de formato não suportado",
    "file_not_zip": "O arquivo não é um ZIP válido",
    "min_files": "Mínimo de 2 arquivos necessários para análise",
    "max_files": "Muitos arquivos podem causar lentidão",
    
    # API errors
    "api_timeout": "A análise demorou muito e foi interrompida",
    "api_rate_limit": "Limite de requisições da API excedido",
    "api_invalid_key": "Chave de API inválida ou não configurada",
    "api_connection_failed": "Falha na conexão com a API",
    
    # Authentication errors
    "auth_expired": "Sua sessão expirou. Faça login novamente",
    "auth_invalid": "Credenciais inválidas",
    "auth_permission": "Você não tem permissão para acessar este recurso",
}

# Help Messages
HELP_MESSAGES = {
    "why_threshold": """
    **Por que usar threshold?**
    
    O threshold define o nível mínimo de similaridade para considerar como suspeito:
    
    - **50% (Agressivo):** Detecta mais plágio, mas pode ter falsos positivos
    - **70% (Moderado):** Equilíbrio entre detecção e precisão
    - **80% (Conservador):** Alta confiança, pode perder plágios sutis
    
    Recomendamos:
    - Projetos grandes: 70-80%
    - Projetos pequenos: 50-70%
    - Revisão manual: 60%
    """,
    
    "why_ai": """
    **Por que usar análise com IA?**
    
    A IA detecta padrões que a análise textual não consegue:
    
    ✅ Detecção de:
    - Reescrita de código (variáveis renomeadas)
    - Mudança de ordem de instruções
    - Simplificação de expressões
    - Inserção de comentários irrelevantes
    
    ❌ Sem IA:
    - Similaridade textual apenas
    - Não detecta reescrita
    - Mais falsos positivos
    
    💡 Recomendamos usar IA para revisão profunda
    """,
    
    "why_workers": """
    **Workers paralelos**
    
    Workers = número de threads que processam arquivos simultaneamente
    
    **Impacto:**
    - Mais workers = análise mais rápida
    - Porém, mais uso de CPU
    
    **Recomendado:**
    - CPU 4 núcleos: 2-4 workers
    - CPU 8 núcleos: 4-6 workers
    - CPU 16+ núcleos: 6-8 workers
    
    ⚠️ Usar muitos workers em CPU limitada pode causar lentidão
    """,
    
    "why_ast": """
    **Similaridade Estrutural (AST)**
    
    AST = Abstract Syntax Tree (Árvore Sintática Abstrata)
    
    Compara a estrutura do código:
    - Loops (for, while)
    - Condicionais (if, switch)
    - Funções e classes
    - Chamadas de função
    
    **Vantagens:**
    ✅ Detecta mudanças de nomes de variáveis
    ✅ Identifica reestruturação de código
    ✅ Ignora formatação e comentários
    
    **Diferença de textual:**
    - Textual: compara caracteres
    - AST: compara lógica/estrutura
    """,
    
    "why_cache": """
    **Cache de resultados**
    
    Armazena resultados de análises anteriores:
    
    **Benefícios:**
    ⚡ Análise instantânea de arquivos já processados
    💾 Economia de tempo e recursos
    🔄 Reutilização em novas análises
    
    **Quando limpar:**
    - Código fonte alterou
    - Arquivos atualizados
    - Erros na análise anterior
    
    💡 Mantenha ativo para melhor performance
    """,
    
    "interpret_similarity": """
    **Como interpretar a similaridade**
    
    **0-30%: Similaridade Baixa**
    - Código provavelmente original
    - Pode ser coincidência (nomes de variáveis comuns)
    - Não requer ação
    
    **30-50%: Similaridade Moderada**
    - Pode haver plágio parcial
    - Verifique manualmente
    - Compare trechos específicos
    
    **50-70%: Similaridade Alta**
    - Forte indício de plágio
    - Análise detalhada necessária
    - Revise com IA se disponível
    
    **70-100%: Similaridade Muito Alta**
    - Plágio provável
    - Código muito similar ou idêntico
    - Requer ação imediata
    """,
}

# Status Messages
STATUS_MESSAGES = {
    "analysis_running": "Análise em andamento... Este processo pode levar alguns minutos.",
    "analysis_complete": "Análise concluída com sucesso!",
    "analysis_cancelled": "Análise cancelada pelo usuário",
    "analysis_error": "Erro durante a análise. Verifique os logs para detalhes.",
    
    "upload_success": "Arquivo carregado e extraído com sucesso!",
    "upload_error": "Erro ao processar o arquivo",
    
    "login_success": "Login realizado com sucesso!",
    "logout_success": "Logout realizado com sucesso!",
    
    "filter_applied": "Filtros aplicados",
    "filter_cleared": "Filtros removidos",
}


def get_metric_tooltip(metric_name: str) -> str:
    """Get tooltip text for a metric."""
    return METRICS_TOOLTIPS.get(metric_name, "Métrica não documentada")


def get_feature_tooltip(feature_name: str) -> str:
    """Get tooltip text for a feature."""
    return FEATURES_TOOLTIPS.get(feature_name, "Feature não documentada")


def get_help_message(help_key: str) -> str:
    """Get detailed help message."""
    return HELP_MESSAGES.get(help_key, "Ajuda não disponível")


def get_status_message(status_key: str) -> str:
    """Get status message."""
    return STATUS_MESSAGES.get(status_key, "Status desconhecido")


def get_validation_message(validation_key: str) -> str:
    """Get validation message."""
    return VALIDATION_MESSAGES.get(validation_key, "Validação desconhecida")