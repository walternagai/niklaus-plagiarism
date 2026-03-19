# Guia do Módulo Analyzer

O pacote `analyzer/` fornece os primitivos de análise de baixo nível usados pelo pipeline. Ele contém quatro classes independentes e um módulo `__init__.py` que as exporta.

```python
from analyzer import ASTParser, CodeMetrics, ClusterDetector, PlagiarismPatternDetector
```

---

## 1. ASTParser — Análise Estrutural

Parsing de AST para Python e fingerprint Winnowing determinístico para demais linguagens.

```python
from analyzer.ast_parser import ASTParser

parser = ASTParser()

# Detectar linguagem pelo filename (fallback: conteúdo)
lang = parser.detect_language('exemplo.py')          # 'python'
lang = parser.detect_language('Main.java')           # 'java'
lang = parser.detect_language('unknown', content='def foo(): pass')  # 'python'

# Fingerprint Winnowing (SHA-256, determinístico entre processos)
fp1 = parser.extract_code_fingerprint("def foo(a, b): return a + b", k=5)
fp2 = parser.extract_code_fingerprint("def bar(x, y): return x + y", k=5)
jaccard = len(fp1 & fp2) / len(fp1 | fp2)  # similaridade por Jaccard

# Similaridade estrutural (Python: AST; outros: fingerprint)
sim = parser.structural_similarity(code1, code2, 'python')  # 0.0–1.0

# Parse AST Python
features = parser.parse_python_ast(code)
# {
#   'functions': [{'name': 'foo', 'args': ['a', 'b'], 'line': 1}],
#   'classes': [],
#   'imports': [],
#   'variables': ['a', 'b'],
#   'calls': [],
#   'loops': [],
#   'conditionals': [],
#   'operators': []
# }

# Padrões de refatoração (apenas Python)
patterns = parser.detect_refactoring_patterns(code1, code2)
# [{'type': 'VARIABLE_RENAME', 'description': '...', 'confidence': 0.8},
#  {'type': 'FUNCTION_RENAME', 'description': '...', 'confidence': 0.8}]
```

### Notas importantes

- `extract_code_fingerprint()` usa **SHA-256** internamente — fingerprints são estáveis entre processos e reinicializações (diferente do `hash()` built-in do Python, que varia por `PYTHONHASHSEED`).
- `detect_language()` corrige a precedência de operadores no fallback por conteúdo: `'def ' in content or ('import ' in content and '#' in content)`.

---

## 2. CodeMetrics — Métricas de Complexidade

```python
from analyzer.metrics import CodeMetrics

metrics = CodeMetrics()
code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

# Todas as métricas de uma vez
result = metrics.calculate_all_metrics(code, 'python')
# {
#   'loc': {'total': 6, 'code': 4, 'comments': 0, 'blank': 2},
#   'cyclomatic_complexity': 2,
#   'function_count': 1,
#   'max_nesting_depth': 1,
#   'maintainability_index': 88.4,
#   'halstead': {'vocabulary': N, 'length': N, 'volume': ..., 'difficulty': ..., 'effort': ...}
# }

# Individualmente
cc  = metrics.calculate_cyclomatic_complexity(code, 'python')
loc = metrics.count_loc(code)
mi  = metrics.calculate_maintainability_index(code, 'python')
h   = metrics.calculate_halstead_metrics(code, 'python')

# Comparar dois conjuntos de métricas
m1 = metrics.calculate_all_metrics(code1, 'python')
m2 = metrics.calculate_all_metrics(code2, 'python')
comp = metrics.compare_metrics(m1, m2)
# {
#   'loc_similarity': 0.95, 'cyclomatic_similarity': 0.87,
#   'function_count_similarity': 1.0, 'nesting_similarity': 0.9,
#   'maintainability_similarity': 0.92, 'overall_similarity': 0.93
# }

# Detectar anomalias que indicam plágio com refatoração
anomalies = metrics.detect_anomalies(textual_sim=0.8, metrics_comparison=comp)
```

### Notas importantes

- **Halstead `n1` corrigido**: conta operadores *encontrados no código*, não o tamanho do conjunto de referência (que era sempre 42). O resultado é válido para cálculo de Volume, Dificuldade e Esforço de Halstead.
- `count_loc()` usa `str.splitlines()` — conta corretamente arquivos sem newline final.
- O índice de manutenibilidade (MI) usa a fórmula simplificada `171 - 5.2 ln(V) - 0.23 G - 16.2 ln(LOC)`, substituindo Volume de Halstead por LOC quando necessário.

---

## 3. ClusterDetector — Clusters de Similaridade

```python
from analyzer.clustering import ClusterDetector
import numpy as np

detector = ClusterDetector()

sim_matrix = np.array([
    [1.0, 0.9, 0.3],
    [0.9, 1.0, 0.2],
    [0.3, 0.2, 1.0]
])
files = ['a.py', 'b.py', 'c.py']

# Clustering hierárquico
clusters = detector.hierarchical_clustering(sim_matrix, files, threshold=0.3)
# {1: ['a.py', 'b.py'], 2: ['c.py']}

# Grafo de similaridade
graph = detector.build_similarity_graph(sim_matrix, files, min_similarity=0.7)
# NetworkX Graph

# Comunidades (greedy modularity)
communities = detector.detect_communities(graph)
# [{0, 1}, {2}]

# Análise completa
analysis = detector.analyze_clusters(sim_matrix, files, min_similarity=0.5)
# {
#   'clusters': {...},
#   'num_clusters': 2,
#   'largest_cluster': 2,
#   'graph_density': 0.33,
#   'communities': [...]
# }
```

---

## 4. PlagiarismPatternDetector — Detecção de Padrões

```python
from analyzer.patterns import PlagiarismPatternDetector

detector = PlagiarismPatternDetector()

code1 = "def add(a, b): return a + b"
code2 = "def sum(x, y): return x + y"  # parâmetros renomeados

# Renomeação de variáveis/parâmetros
result = detector.detect_variable_renaming(code1, code2, 'python')
# {
#   'detected': True,
#   'variables_renamed': [('a', 'x'), ('b', 'y')],
#   'confidence': 0.75
# }

# Reordenação de código
result = detector.detect_code_reordering(code1, code2)
# {'detected': bool, 'reordered_blocks': [], 'confidence': float}

# Inserção de código morto
result = detector.detect_dead_code_insertion(code1, code2)
# {'detected': bool, 'inserted_lines': int, 'confidence': float}

# Análise abrangente
analysis = detector.comprehensive_analysis(
    code1, code2,
    textual_sim=0.6,
    ast_sim=0.95,
    metrics_comp={'overall_similarity': 0.9}
)
# {
#   'plagiarism_type': 'RENOMEACAO_VARIAVEIS',
#   'plagiarism_description': 'Variáveis e/ou funções renomeadas...',
#   'confidence': 0.71,
#   'patterns_detected': {...},
#   'explanation': 'O código estrutural é muito similar (95%)...'
# }
```

### Guards na detecção de renomeação

O detector usa verificações estruturais antes de classificar como renomeação, evitando falsos positivos:

1. Requer ao menos uma variável/parâmetro diferente entre os arquivos.
2. Rejeita quando variáveis e funções são idênticas (`vars1 == vars2 and funcs1 == funcs2`).
3. Rejeita quando sobreposição de nomes > 90% (não é renomeação).
4. Verifica que assinaturas de função (nº de argumentos) são iguais.
5. Só sinaliza pares com nomes efetivamente distintos (não mapeia nomes iguais).

A `confidence` retornada é 0.75 (anteriormente 0.85 — reduzida para refletir a natureza heurística).

`_extract_all_names()` agora coleta parâmetros de função (`ast.arg`) além de variáveis de atribuição (`ast.Store`) — corrigindo o caso em que apenas parâmetros eram renomeados.

---

## Tipos de plágio

| Tipo | Condição de classificação |
|---|---|
| `COPIA_DIRETA` | Textual > 95% e AST > 95% |
| `RENOMEACAO_VARIAVEIS` | Renomeação detectada + textual > 60% e AST > 85% |
| `REORDENACAO_CODIGO` | Reordenação detectada + AST > 90% |
| `INSERCAO_CODIGO_MORTO` | Dead code detectada |
| `REFATORACAO_PESADA` | Textual < 70% mas AST > 80% |
| `REFATORACAO_LEVE` | Textual > 70% e AST > 85% e métricas > 70% |
| `SIMILARIDADE_BAIXA` | Textual < 50% e AST < 60% |
| `REUSO_LEGITIMO` | Default |

---

## Exemplo completo via pipeline (recomendado)

Para análise de múltiplos arquivos, use o `AnalysisPipeline` em vez de chamar os módulos diretamente:

```python
from core.pipeline import AnalysisPipeline

pipeline = AnalysisPipeline(
    language='python',
    api_key=None,        # None desativa análise IA
    max_workers=4,
    use_cache=True
)

results = pipeline.run_full_analysis(
    files=['a.py', 'b.py', 'c.py'],
    contents=[code_a, code_b, code_c],
    threshold=0.7,
    enable_ai=False
)
# results contém: files, textual_similarities, ast_similarities,
#   metrics, similarity_matrix, cluster_data, patterns,
#   pairwise_results, suspicious_pairs, ...
```

---

## Exemplo standalone (sem pipeline)

```python
from analyzer import ASTParser, CodeMetrics, ClusterDetector, PlagiarismPatternDetector
import numpy as np

files    = ['a.py', 'b.py', 'c.py']
contents = [open(f).read() for f in files]

parser   = ASTParser()
metrics  = CodeMetrics()
clusters = ClusterDetector()
patterns = PlagiarismPatternDetector()

# 1. Similaridade estrutural
n = len(files)
sim_matrix = np.eye(n)
pairs = []
for i in range(n):
    for j in range(i+1, n):
        sim = parser.structural_similarity(contents[i], contents[j], 'python')
        sim_matrix[i, j] = sim_matrix[j, i] = sim
        pairs.append((files[i], files[j], sim))

# 2. Métricas por arquivo
all_metrics = [metrics.calculate_all_metrics(c, 'python') for c in contents]

# 3. Clustering
cluster_result = clusters.analyze_clusters(sim_matrix, files)

# 4. Padrões para pares suspeitos
for f1, f2, sim in pairs:
    if sim > 0.7:
        i1, i2 = files.index(f1), files.index(f2)
        comp = metrics.compare_metrics(all_metrics[i1], all_metrics[i2])
        analysis = patterns.comprehensive_analysis(
            contents[i1], contents[i2],
            textual_sim=sim, ast_sim=sim, metrics_comp=comp
        )
        print(f"{f1} vs {f2}: {analysis['plagiarism_type']} (conf={analysis['confidence']:.2f})")
```

---

## Testes

```bash
# Suite completa do analyzer
pytest tests/test_analyzer.py -v

# Importação rápida
python3 -c "from analyzer import ASTParser, CodeMetrics, ClusterDetector, PlagiarismPatternDetector; print('OK')"
```

---

## Limitações conhecidas

- **AST detalhado** funciona apenas em Python. Outras linguagens usam fingerprint Winnowing.
- **Fingerprint** compara apenas estrutura léxica — não semântica. Código equivalente com sintaxe diferente pode ter baixa similaridade.
- **Detecção de renomeação** usa heurísticas (contagem e comparação de nomes) — não garante 100% de precisão.
- Arquivos muito longos (> 10.000 linhas) podem tornar o cálculo de métricas lento.

---

## Contato

Dúvidas ou sugestões: [walternagai@unifei.edu.br](mailto:walternagai@unifei.edu.br)
