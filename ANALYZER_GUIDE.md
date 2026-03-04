# Niklaus Analyzer Module - Guia de Uso

## Visão Geral

O módulo `analyzer` fornece análise avançada de plágio com 4 componentes principais:

1. **ASTParser** - Parsing e comparação de árvores sintáticas
2. **CodeMetrics** - Cálculo de métricas de complexidade
3. **ClusterDetector** - Detecção de clusters de similaridade
4. **PlagiarismPatternDetector** - Detecção de padrões de plágio

## Instalação de Dependências

```bash
pip install -r requirements.txt
```

Dependências principais:
- `scipy>=1.11.0` - Clustering hierárquico
- `scikit-learn>=1.3.0` - Machine learning utilities
- `networkx>=3.0` - Grafos de similaridade
- `plotly>=5.18.0` - Visualizações interativas
- `fpdf>=1.7.2` - Relatórios PDF

## Uso dos Módulos

### 1. ASTParser - Análise Estrutural

```python
from analyzer.ast_parser import ASTParser

parser = ASTParser()

# Detectar linguagem
language = parser.detect_language('example.py', content)
# Retorna: 'python', 'java', 'javascript', etc.

# Análise estrutural
code1 = "def foo(a, b): return a + b"
code2 = "def bar(x, y): return x + y"

similarity = parser.structural_similarity(code1, code2, 'python')
# Retorna: 0.95 (muito similar estruturalmente)

# Extrair features AST
features = parser.parse_python_ast(code1)
# Retorna: {'functions': [...], 'variables': [...], 'imports': [...], ...}

# Fingerprint (Winnowing)
fp1 = parser.extract_code_fingerprint(code1, k=5)
fp2 = parser.extract_code_fingerprint(code2, k=5)
# Comparar fingerprints

# Detectar refactoring
patterns = parser.detect_refactoring_patterns(code1, code2)
# Retorna: [{'type': 'VARIABLE_RENAME', 'description': '...', 'confidence': 0.8}]
```

### 2. CodeMetrics - Métricas de Complexidade

```python
from analyzer.metrics import CodeMetrics

metrics = CodeMetrics()

code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

# Calcular todas as métricas
all_metrics = metrics.calculate_all_metrics(code, 'python')
# Retorna: {
#   'loc': {'total': 5, 'code': 4, 'comments': 0, 'blank': 1},
#   'cyclomatic_complexity': 3,
#   'function_count': 1,
#   'max_nesting_depth': 2,
#   'maintainability_index': 85.6,
#   'halstead': {...}
# }

# Comparar métricas entre dois códigos
metrics1 = metrics.calculate_all_metrics(code1, 'python')
metrics2 = metrics.calculate_all_metrics(code2, 'python')

comparison = metrics.compare_metrics(metrics1, metrics2)
# Retorna: {'loc_similarity': 0.95, 'cyclomatic_similarity': 0.87, ...}

# Detectar anomalias
anomalies = metrics.detect_anomalies(textual_sim, comparison)
# Retorna: [{'type': 'METRIC_MISMATCH', 'description': '...', 'confidence': 0.75}]
```

### 3. ClusterDetector - Clusters de Similaridade

```python
from analyzer.clustering import ClusterDetector
import numpy as np

detector = ClusterDetector()

# Matriz de similaridade (NxN)
similarity_matrix = np.array([
    [1.0, 0.9, 0.3],
    [0.9, 1.0, 0.2],
    [0.3, 0.2, 1.0]
])
files = ['file1.py', 'file2.py', 'file3.py']

# Clustering hierárquico
clusters = detector.hierarchical_clustering(similarity_matrix, files, threshold=0.3)
# Retorna: {1: ['file1.py', 'file2.py'], 2: ['file3.py']}

# Construir grafo de similaridade
graph = detector.build_similarity_graph(similarity_matrix, files, min_similarity=0.7)
# NetworkX Graph

# Detectar comunidades
communities = detector.detect_communities(graph)
# Retorna: [{0, 1}, {2}]

# Análise completa
analysis = detector.analyze_clusters(similarity_matrix, files, min_similarity=0.5)
# Retorna: {
#   'clusters': {...},
#   'num_clusters': 2,
#   'largest_cluster': 2,
#   'graph_density': 0.33,
#   'communities': [...]
# }
```

### 4. PlagiarismPatternDetector - Detecção de Padrões

```python
from analyzer.patterns import PlagiarismPatternDetector

detector = PlagiarismPatternDetector()

code1 = "def add(a, b): return a + b"
code2 = "def sum(x, y): return x + y"

# Detectar renomeação de variáveis
rename_analysis = detector.detect_variable_renaming(code1, code2, 'python')
# Retorna: {'detected': True, 'variables_renamed': [('a', 'x'), ('b', 'y')], 'confidence': 0.85}

# Detectar reordenação de código
reorder_analysis = detector.detect_code_reordering(code1, code2)
# Retorna: {'detected': False, 'reordered_blocks': [], 'confidence': 0.0}

# Detectar inserção de código morto
deadcode_analysis = detector.detect_dead_code_insertion(code1, code2)
# Retorna: {'detected': False, 'inserted_lines': 0, 'confidence': 0.0}

# Análise completa
full_analysis = detector.comprehensive_analysis(
    code1, code2,
    textual_sim=0.75,
    ast_sim=0.95,
    metrics_comp={'overall_similarity': 0.85}
)
# Retorna: {
#   'plagiarism_type': 'RENOMEACAO_VARIAVEIS',
#   'plagiarism_description': 'Variáveis e/ou funções renomeadas...',
#   'confidence': 0.85,
#   'patterns_detected': {...},
#   'explanation': 'O código estrutural é muito similar (95%)...'
# }

# Classificar tipo de plágio
plagiarism_type = detector.classify_plagiarism_type(
    textual_sim=0.75,
    ast_sim=0.95,
    metrics_comparison={'overall_similarity': 0.85},
    pattern_analysis={'variable_renaming': {'detected': True}}
)
# Retorna: 'RENOMEACAO_VARIAVEIS'
```

## Tipos de Plágio Detectados

O sistema classifica em 8 tipos:

1. **COPIA_DIRETA** - Similaridade > 95% textual e estrutural
2. **RENOMEACAO_VARIAVEIS** - Estrutura similar, variáveis renomeadas
3. **REORDENACAO_CODIGO** - Blocos reorganizados mas funcionalmente equivalentes
4. **INSERCAO_CODIGO_MORTO** - Código morto ou comentários inseridos
5. **REFATORACAO_LEVE** - Pequenas modificações estruturais
6. **REFATORACAO_PESADA** - Refatoração significativa mantendo funcionalidade
7. **SIMILARIDADE_BAIXA** - Código provavelmente original
8. **REUSO_LEGITIMO** - Reutilização de bibliotecas/código comum

## Integração com a Interface Streamlit

Os módulos estão totalmente integrados no `app.py` e operam automaticamente:

### Fluxo de Análise (Phase 2)

1. **Upload de arquivos** → Validação e extração do ZIP
2. **Similaridade textual** → Matriz de similaridade comparando todos os pares
3. **Análise AST** → Similaridade estrutural calculada para cada par
4. **Métricas de complexidade** → LOC, CC, funções, aninhamento, MI
5. **Clustering** → Detecção automática de grupos de plágio
6. **Detecção de padrões** → Classificação do tipo de plágio
7. **Visualização** → Grafo interativo, heatmaps, radar charts

### Abas da Interface

| Tab | Funcionalidade | Módulos Usados |
|-----|---------------|----------------|
| Upload & Análise | Upload, configuração, resumo | - |
| Resultados | Tabela de similaridade, AI analysis, diff visual | PlagiarismPatternDetector |
| Estatísticas | Heatmap, histograma, preview | - |
| Análise Avançada | AST, métricas, radar, padrões | ASTParser, CodeMetrics, PlagiarismPatternDetector |
| Grafo de Similaridade | Rede interativa, clusters, comunidades | ClusterDetector |

## Exemplo Completo de Uso

```python
from analyzer import ASTParser, CodeMetrics, ClusterDetector, PlagiarismPatternDetector
import numpy as np

# Inicializar analisadores
ast_parser = ASTParser()
metrics_calculator = CodeMetrics()
cluster_detector = ClusterDetector()
pattern_detector = PlagiarismPatternDetector()

# Carregar códigos
codes = ['codigo1.py', 'codigo2.py', 'codigo3.py']
contents = [open(f).read() for f in codes]

# 1. Análise estrutural (AST)
ast_similarities = []
for i in range(len(contents)):
    for j in range(i+1, len(contents)):
        sim = ast_parser.structural_similarity(contents[i], contents[j], 'python')
        ast_similarities.append((codes[i], codes[j], sim))

# 2. Métricas de complexidade
all_metrics = [metrics_calculator.calculate_all_metrics(c, 'python') for c in contents]

# 3. Clustering
sim_matrix = np.zeros((len(contents), len(contents)))
# ... preencher matriz ...

cluster_result = cluster_detector.analyze_clusters(sim_matrix, codes)

# 4. Detecção de padrões
for file1, file2, sim in ast_similarities:
    if sim > 0.7:
        analysis = pattern_detector.comprehensive_analysis(
            contents[codes.index(file1)],
            contents[codes.index(file2)],
            textual_sim=sim,
            ast_sim=sim,
            metrics_comp=metrics_calculator.compare_metrics(
                all_metrics[codes.index(file1)],
                all_metrics[codes.index(file2)]
            )
        )
        print(f"{file1} vs {file2}: {analysis['plagiarism_type']}")
        print(f"Confiança: {analysis['confidence']:.2f}")
        print(f"Explicação: {analysis['explanation']}")
```

## Linguagens Suportadas

| Linguagem | Extensão | AST Detalhado | Fingerprint |
|-----------|----------|---------------|-------------|
| Python | .py | Sim (nativo) | Sim |
| C | .c | Não | Sim |
| C++ | .cpp | Não | Sim |
| Java | .java | Não | Sim |
| JavaScript | .js | Não | Sim |
| TypeScript | .ts | Não | Sim |
| Go | .go | Não | Sim |
| Rust | .rs | Não | Sim |
| Kotlin | .kt | Não | Sim |

## Novidades da Phase 2

### Grafo de Similaridade Interativo
- Visualização NetworkX Plotly com layout spring
- Nós coloridos por cluster
- Arestas proporcionais à similaridade
- Hover com estatísticas detalhadas
- Detecção de comunidades (greedy modularity)

### Diff Visual
- Toggle entre "Código lado a lado" e "Diff interativo"
- Linhas adicionadas destacadas em verde
- Linhas removidas destacadas em vermelho
- Numeração preservada

### PDF Enriquecido
- Tabela de similaridade colorida
- Tabela de métricas de complexidade
- Similaridade AST ordenada
- Resumo de clusters com estatísticas
- Badge de severidade por cluster

### UI Expandida
- 9 linguagens no seletor (era 5)
- 5 abas (era 4)
- Resumo de clusters na Tab 5
- Arquivos centrais identificados

## Testando

```bash
# Executar testes básicos
python3 -c "
from analyzer import ASTParser, CodeMetrics, ClusterDetector, PlagiarismPatternDetector
print('Todos os módulos importados com sucesso!')
"

# Testar AST parsing
python3 -c "
from analyzer.ast_parser import ASTParser
parser = ASTParser()
code = 'def foo(a, b): return a + b'
features = parser.parse_python_ast(code)
print('Functions:', features['functions'])
print('AST parsing OK!')
"

# Testar clustering
python3 -c "
from analyzer.clustering import ClusterDetector
import numpy as np
detector = ClusterDetector()
sim = np.array([[1.0, 0.9], [0.9, 1.0]])
result = detector.analyze_clusters(sim, ['a.py', 'b.py'])
print('Clusters:', result['num_clusters'])
print('Clustering OK!')
"
```

## Limitações Conhecidas

- **Linguagens**: Parsing AST detalhado funciona melhor em Python. Outras linguagens usam approach genérico (fingerprint).
- **Código muito longo**: Pode haver lentidão em arquivos > 10.000 linhas.
- **Dependências**: Requer networkx, scipy, scikit-learn instalados.

## Manutenção

Para atualizar ou adicionar novas linguagens:

```python
# Em analyzer/ast_parser.py
SUPPORTED_LANGUAGES = {
    'nova_linguagem': {
        'extensions': ['.nl'],
        'comment_single': '//',
        'comment_multi': ('/*', '*/')
    }
}
```

## Contato

Para dúvidas ou sugestões: walternagai@unifei.edu.br