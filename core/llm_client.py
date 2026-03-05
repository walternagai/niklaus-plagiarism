"""
Maritaca API client wrapper with rate limiting and retry logic.
"""

import time
from typing import Dict, Optional
import openai

from utils.config import config
from utils.exceptions import MaritacaAPIError, RateLimitError
from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_minute: Maximum number of calls per minute
        """
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0
    
    def wait(self) -> None:
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()


class MaritacaClient:
    """Client wrapper for Maritaca API with rate limiting and retry logic."""
    
    def __init__(
        self,
        api_key: str,
        model: str = None,
        timeout: int = None,
        max_retries: int = None,
        rate_limit: int = None
    ):
        """
        Initialize Maritaca client.
        
        Args:
            api_key: Maritaca API key
            model: Model name (default: sabiazinho-4)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries on failure
            rate_limit: Maximum calls per minute
        """
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=config.MARITACA_API_URL,
            timeout=timeout or config.MARITACA_TIMEOUT
        )
        self.model = model or config.MARITACA_MODEL
        self.max_retries = max_retries or config.MARITACA_MAX_RETRIES
        self.rate_limiter = RateLimiter(rate_limit or config.MARITACA_RATE_LIMIT)
        
        logger.info(f"Initialized Maritaca client with model {self.model}")
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for plagiarism analysis."""
        return """Você é Niklaus, um assistente especializado em análise de plágio em código-fonte para professores de programação.

## Seu Papel
Você recebe DOIS códigos-fonte que foram previamente comparados por análise automatizada (similaridade textual e estrutural já calculadas). Sua função é ANALISAR qualitativamente os trechos semelhantes e fornecer insights sobre a natureza da similaridade.

## O que você DEVE fazer
1. **Identificar trechos problemáticos**: Aponte exatamente quais blocos de código são similares
2. **Classificar a similaridade**: Diferencie entre:
   - Cópia direta (idêntica ou quase)
   - Refatoração (renomeação de variáveis, reordenação)
   - Coincidência (lógica simples, padrões comuns, bibliotecas)
3. **Explicar o contexto**: Por que esses trechos são problemáticos ou não?
4. **Fornecer recomendações**: O professor deve investigar mais? É claramente plágio? É falso positivo?

## O que você NÃO deve fazer
- NÃO invente similaridades inexistentes
- NÃO classifique como plágio código que usa padrões comuns, algoritmos clássicos ou bibliotecas padrão
- NÃO forneça conselhos pedagógicos extras além da análise solicitada
- NÃO tente calcular métricas matemáticas — o sistema já fez isso

## Formato de Resposta Obrigatório

**Resumo Executivo**

[2-3 frases sobre a natureza da similaridade]

**Trechos Problemáticos Identificados**

[Lista de blocos específicos com linha aproximada e descrição]

**Classificação da Similaridade**

[COPIA_DIRETA / RENOMEACAO_VARIAVEIS / REORDENACAO / COINCIDENCIA / REUSO_LEGITIMO]

**Recomendação para o Professor**

[Ação sugerida: investigar, descartar, ou atenção]

## Idioma
Todas as respostas devem ser em português do Brasil."""
    
    def _build_user_prompt(
        self,
        code1: str,
        code2: str,
        file1: str,
        file2: str,
        textual_similarity: float,
        ast_similarity: float,
        plagiarism_type: str,
        confidence: float
    ) -> str:
        """Build user prompt with code comparison details."""
        return f"""Analise os dois códigos abaixo e identifique trechos plagiados.

## Dados da Análise Automatizada
- Arquivo 1: {file1}
- Arquivo 2: {file2}
- Similaridade textual: {textual_similarity:.1%}
- Similaridade estrutural (AST): {ast_similarity:.1%}
- Tipo de plágio detectado: {plagiarism_type}
- Confiança: {confidence:.1%}

## Código 1 ({file1})
```
{code1}
```

## Código 2 ({file2})
```
{code2}
```

Siga o formato de resposta obrigatório definido nas instruções."""
    
    def analyze_plagiarism(
        self,
        code1: str,
        code2: str,
        file1: str,
        file2: str,
        textual_similarity: float,
        ast_similarity: float,
        plagiarism_type: str,
        confidence: float,
        max_tokens: int = 1500
    ) -> str:
        """
        Analyze code pair for plagiarism with AI.
        
        Args:
            code1: First code snippet
            code2: Second code snippet
            file1: First filename
            file2: Second filename
            textual_similarity: Textual similarity score (0-1)
            ast_similarity: AST similarity score (0-1)
            plagiarism_type: Detected plagiarism type
            confidence: Confidence score (0-1)
            max_tokens: Maximum tokens in response
        
        Returns:
            AI analysis text
        
        Raises:
            MaritacaAPIError: If API call fails
            RateLimitError: If rate limit exceeded
        """
        # Wait for rate limiter
        self.rate_limiter.wait()
        
        system_prompt = self._get_system_prompt()
        user_prompt = self._build_user_prompt(
            code1, code2, file1, file2,
            textual_similarity, ast_similarity,
            plagiarism_type, confidence
        )
        
        # Retry loop
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Analyzing {file1} vs {file2} (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=max_tokens
                )
                
                result = response.choices[0].message.content
                logger.info(f"Analysis completed for {file1} vs {file2}")
                
                return result
                
            except openai.RateLimitError as e:
                logger.warning(f"Rate limit hit: {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    sleep_time = (attempt + 1) * 5
                    logger.info(f"Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    raise RateLimitError(
                        retry_after=getattr(e, 'retry_after', None)
                    )
            
            except openai.APIError as e:
                logger.error(f"API error: {e}")
                if attempt < self.max_retries - 1:
                    sleep_time = (attempt + 1) * 2
                    logger.info(f"Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    raise MaritacaAPIError(
                        f"Failed to analyze code after {self.max_retries} attempts: {str(e)}",
                        status_code=getattr(e, 'status_code', None),
                        original_error=e
                    )
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise MaritacaAPIError(
                    f"Unexpected error during analysis: {str(e)}",
                    original_error=e
                )
        
        # Should never reach here
        raise MaritacaAPIError("Failed to complete analysis")
    
    def test_connection(self) -> bool:
        """
        Test API connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.rate_limiter.wait()
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Teste de conexão. Responda apenas 'OK'."}
                ],
                max_tokens=10
            )
            
            result = response.choices[0].message.content
            logger.info(f"Connection test successful: {result}")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False