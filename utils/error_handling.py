"""
Error handling utilities for Niklaus.
Provides specific, actionable error messages for users.
"""

from typing import Optional, Dict, Any
import streamlit as st


class NiklausError(Exception):
    """Base exception for Niklaus-specific errors."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None, help_url: Optional[str] = None):
        self.message = message
        self.suggestion = suggestion
        self.help_url = help_url
        super().__init__(self.message)


class FileValidationError(NiklausError):
    """File validation errors."""
    pass


class APIError(NiklausError):
    """API-related errors."""
    pass


class AuthenticationError(NiklausError):
    """Authentication errors."""
    pass


class AnalysisError(NiklausError):
    """Analysis-related errors."""
    pass


def display_error(error: Exception, context: Optional[str] = None):
    """
    Display user-friendly error message with suggestions.
    
    Args:
        error: Exception that occurred
        context: Additional context about where the error occurred
    """
    if isinstance(error, NiklausError):
        _display_custom_error(error)
    elif isinstance(error, FileValidationError):
        _display_file_error(error)
    elif isinstance(error, APIError):
        _display_api_error(error)
    elif isinstance(error, AuthenticationError):
        _display_auth_error(error)
    elif isinstance(error, AnalysisError):
        _display_analysis_error(error)
    else:
        _display_generic_error(error, context)


def _display_custom_error(error: NiklausError):
    """Display custom Niklaus error with suggestions."""
    st.error(f"❌ {error.message}")
    
    if error.suggestion:
        st.warning(f"💡 **Sugestão:** {error.suggestion}")
    
    if error.help_url:
        st.markdown(f"📖 [Saiba mais]({error.help_url})")


def _display_file_error(error: FileValidationError):
    """Display file-related errors with specific suggestions."""
    error_msg = str(error)
    
    if "tamanho" in error_msg.lower() or "size" in error_msg.lower():
        st.error("❌ Arquivo muito grande")
        st.warning("💡 **Solução:** Compacte o arquivo ZIP ou remova arquivos desnecessários.")
        st.info("📚 Limite máximo: 100MB por arquivo ZIP")
    
    elif "formato" in error_msg.lower() or "extension" in error_msg.lower():
        st.error("❌ Formato de arquivo não suportado")
        st.warning("💡 **Solução:** Use arquivos .zip contendo código-fonte.")
        st.info("📚 Formatos aceitos: .py, .java, .cpp, .c, .js, .ts, .go, .rs, .kt")
    
    elif "vazio" in error_msg.lower() or "empty" in error_msg.lower():
        st.error("❌ Arquivo ZIP vazio")
        st.warning("💡 **Solução:** Adicione pelo menos 2 arquivos de código-fonte para análise.")
    
    elif "corrompido" in error_msg.lower() or "corrupted" in error_msg.lower():
        st.error("❌ Arquivo ZIP corrompido")
        st.warning("💡 **Solução:** Baixe o arquivo novamente ou tente outro navegador.")
    
    else:
        st.error(f"❌ Erro no arquivo: {error_msg}")
        st.warning("💡 **Solução:** Verifique se o arquivo ZIP contém apenas código-fonte.")


def _display_api_error(error: APIError):
    """Display API-related errors with specific suggestions."""
    error_msg = str(error)
    
    if "timeout" in error_msg.lower() or "tempo" in error_msg.lower():
        st.error("❌ Tempo limite excedido")
        st.warning("💡 **Solução:** A análise está demorando muito. Tente:")
        st.markdown("- Diminuir o número de workers")
        st.markdown("- Reduzir o tamanho do arquivo ZIP")
        st.markdown("- Desativar análise com IA")
    
    elif "rate limit" in error_msg.lower():
        st.error("❌ Limite de requisições da API atingido")
        st.warning("💡 **Solução:** Aguarde alguns minutos ou reduza o uso de IA.")
        st.info("📚 A API Maritaca tem limite de requisições por minuto.")
    
    elif "api key" in error_msg.lower() or "chave" in error_msg.lower():
        st.error("❌ Chave de API inválida ou não configurada")
        st.warning("💡 **Solução:** Configure a chave de API corretamente.")
        st.markdown("**Passos:**")
        st.markdown("1. Acesse [Maritaca AI](https://maritaca.ai)")
        st.markdown("2. Obtenha sua chave de API")
        st.markdown("3. Configure no arquivo `.streamlit/secrets.toml`")
    
    elif "connection" in error_msg.lower() or "conexão" in error_msg.lower():
        st.error("❌ Erro de conexão")
        st.warning("💡 **Solução:** Verifique sua conexão com a internet.")
    
    else:
        st.error(f"❌ Erro na API: {error_msg}")
        st.warning("💡 **Solução:** Tente novamente mais tarde ou reduza o uso de IA.")


def _display_auth_error(error: AuthenticationError):
    """Display authentication-related errors."""
    error_msg = str(error)
    
    if "expirado" in error_msg.lower() or "expired" in error_msg.lower():
        st.error("❌ Sessão expirada")
        st.warning("💡 **Solução:** Faça login novamente.")
        st.markdown("[Fazer login](/)")
    
    elif "permissão" in error_msg.lower() or "permission" in error_msg.lower():
        st.error("❌ Sem permissão de acesso")
        st.warning("💡 **Solução:** Entre em contato com o administrador.")
    
    elif "inválido" in error_msg.lower() or "invalid" in error_msg.lower():
        st.error("❌ Credenciais inválidas")
        st.warning("💡 **Solução:** Verifique sua conta ou tente outro provedor.")
    
    else:
        st.error(f"❌ Erro de autenticação: {error_msg}")
        st.warning("💡 **Solução:** Faça login novamente.")


def _display_analysis_error(error: AnalysisError):
    """Display analysis-related errors."""
    error_msg = str(error)
    
    if "memória" in error_msg.lower() or "memory" in error_msg.lower():
        st.error("❌ Memória insuficiente")
        st.warning("💡 **Solução:** Reduza o tamanho dos arquivos ou use menos workers.")
    
    elif "linguagem" in error_msg.lower() or "language" in error_msg.lower():
        st.error("❌ Linguagem não suportada")
        st.warning("💡 **Solução:** Selecione uma linguagem suportada.")
        st.info("📚 Linguagens: Python, Java, C, C++, JavaScript, Go, Rust, TypeScript, Kotlin")
    
    elif "parser" in error_msg.lower() or "sintaxe" in error_msg.lower():
        st.error("❌ Erro de sintaxe nos arquivos")
        st.warning("💡 **Solução:** Verifique se os arquivos têm sintaxe válida.")
    
    else:
        st.error(f"❌ Erro na análise: {error_msg}")
        st.warning("💡 **Solução:** Tente novamente ou reduza o número de arquivos.")


def _display_generic_error(error: Exception, context: Optional[str] = None):
    """Display generic errors with limited information."""
    error_type = type(error).__name__
    
    st.error(f"❌ Erro inesperado: {error_type}")
    
    if context:
        st.warning(f"💡 **Contexto:** {context}")
    
    st.markdown("**Soluções comuns:**")
    st.markdown("- Recarregue a página")
    st.markdown("- Limpe o cache do navegador")
    st.markdown("- Tente novamente em alguns minutos")
    
    with st.expander("🔍 Ver detalhes técnicos"):
        st.code(str(error), language="text")


def suggest_file_solutions():
    """Display common file-related solutions."""
    st.markdown("---")
    st.markdown("### 💡 Dicas para Arquivos")
    st.markdown("""
    - **Formato:** ZIP contendo código-fonte
    - **Tamanho:** Máximo 100MB
    - **Conteúdo:** Arquivos de programação (.py, .java, .cpp, etc.)
    - **Quantidade:** Mínimo 2 arquivos para comparação
    """)


def suggest_performance_improvements():
    """Display suggestions for improving performance."""
    st.markdown("---")
    st.markdown("### ⚡ Otimização de Performance")
    st.markdown("""
    **Para análise mais rápida:**
    - Aumente workers paralelos (configuração → 4-8 workers)
    - Ative cache (reutiliza resultados anteriores)
    - Desative IA (análise textual é mais rápida)
    
    **Para muitos arquivos (>50):**
    - Use threshold alto (0.8) para filtrar resultados
    - Divida em múltiplas análises menores
    - Considere amostragem dos arquivos
    """)


def estimate_analysis_time(file_count: int, enable_ai: bool, max_workers: int) -> str:
    """
    Estimate analysis time based on parameters.
    
    Args:
        file_count: Number of files
        enable_ai: Whether AI analysis is enabled
        max_workers: Number of parallel workers
    
    Returns:
        Human-readable time estimate
    """
    base_time_per_file = 0.5  # seconds
    
    if enable_ai:
        base_time_per_file = 2.0  # AI adds time
    
    # Parallel processing reduces time
    effective_workers = min(max_workers, file_count)
    estimated_time = (file_count * base_time_per_file) / effective_workers
    
    if estimated_time < 60:
        return f"{estimated_time:.0f} segundos"
    elif estimated_time < 3600:
        return f"{estimated_time / 60:.0f} minutos"
    else:
        return f"{estimated_time / 3600:.1f} horas"


def check_file_validity(file_count: int, file_size_mb: float) -> Optional[str]:
    """
    Check if file configuration is valid and suggest actions.
    
    Args:
        file_count: Number of files
        file_size_mb: File size in MB
    
    Returns:
        Warning message if issues found, None otherwise
    """
    warnings = []
    
    if file_count < 2:
        warnings.append("⚠️ Mínimo de 2 arquivos necessário para comparação")
    
    if file_count > 100:
        warnings.append("⚠️ Muitos arquivos podem tornar a análise lenta. Considere dividir em lotes.")
    
    if file_size_mb > 50:
        warnings.append("⚠️ Arquivo grande pode demorar para processar")
    
    return " | ".join(warnings) if warnings else None