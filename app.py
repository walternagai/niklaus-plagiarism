import io
import os
import re
import math
import time
import json
import string
import random
import shutil
import tempfile
import zipfile
import numpy as np
import chardet
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from zipfile import ZipFile
from difflib import SequenceMatcher, unified_diff
import openai
from datetime import datetime
from fpdf import FPDF

# Import analyzer modules
from analyzer import ASTParser, CodeMetrics, ClusterDetector, PlagiarismPatternDetector

def remove_blank_spaces_and_comments(code, language):
    if language.lower() == 'python':
        code = re.sub(r'""".*?"""|\'\'\'.*?\'\'\'', '', code, flags=re.DOTALL)
        code = re.sub(r'#.*', '', code)
    elif language.lower() in ['c', 'c++', 'java', 'javascript']:
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'(\".*?\"|\'.*?\')', '', code, flags=re.DOTALL)
        code = re.sub(r'\s+', ' ', code)
    code = code.strip()
    return code

def read_file(file):
    file_content = file.getvalue()
    file_encoding = chardet.detect(file_content)['encoding']
    file_content = file_content.decode(file_encoding)
    return file_content

def calculate_similarity(code1, code2):
    my_seq = SequenceMatcher(a=code1, b=code2)
    return my_seq.ratio()

def comparate_files(code1, code2, language='python'):
    language = language.lower()
    if not code1 or not code2:
        return 0.0
    clean_code1 = remove_blank_spaces_and_comments(code1, language)
    clean_code2 = remove_blank_spaces_and_comments(code2, language)
    similaridade = calculate_similarity(clean_code1, clean_code2)
    return similaridade

def generate_response_maritaca(api_key, model, file_content, file_content_to_compare, 
                                file1_name, file2_name, textual_similarity, ast_similarity,
                                plagiarism_type, confidence):
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://chat.maritaca.ai/api"
    )
    
    system_prompt = """Você é Niklaus, um assistente especializado em análise de plágio em código-fonte para professores de programação.

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

**### Resumo Executivo**
[2-3 frases sobre a natureza da similaridade]

**### Trechos Problemáticos Identificados**
[Lista de blocos específicos com linha aproximada e descrição]

**### Classificação da Similaridade**
[COPIA_DIRETA / RENOMEACAO_VARIAVEIS / REORDENACAO / COINCIDENCIA / REUSO_LEGITIMO]

**### Recomendação para o Professor**
[Ação sugerida: investigar, descartar, ou atenção]

## Idioma
Todas as respostas devem ser em português do Brasil."""

    user_prompt = f"""Analise os dois códigos abaixo e identifique trechos plagiados.

## Dados da Análise Automatizada
- Arquivo 1: {file1_name}
- Arquivo 2: {file2_name}
- Similaridade textual: {textual_similarity:.1%}
- Similaridade estrutural (AST): {ast_similarity:.1%}
- Tipo de plágio detectado: {plagiarism_type}
- Confiança: {confidence:.1%}

## Código 1 ({file1_name})
```
{file_content}
```

## Código 2 ({file2_name})
```
{file_content_to_compare}
```

Siga o formato de resposta obrigatório definido nas instruções."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=1500
    )

    return response.choices[0].message.content

def stream_data(response):
    for word in response.split(" "):
        yield word + " "
        time.sleep(0.01)

def create_heatmap(files, similarity_matrix):
    fig = px.imshow(
        similarity_matrix,
        x=files,
        y=files,
        color_continuous_scale="RdYlGn_r",
        labels=dict(x="Arquivo", y="Arquivo", color="Similaridade"),
        title="Matriz de Similaridade entre Arquivos",
        aspect="auto"
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        width=800,
        height=800
    )
    fig.update_traces(
        hovertemplate="Similaridade: %{z:.2%}<extra></extra>"
    )
    return fig

def create_pdf_report(df, files, language, threshold):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Relatorio de Analise de Plagio - Niklaus", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=True)
    pdf.cell(0, 8, f"Linguagem: {language}", ln=True)
    pdf.cell(0, 8, f"Limite de Similaridade: {threshold:.0%}", ln=True)
    pdf.cell(0, 8, f"Arquivos Analisados: {len(files)}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Resultados", ln=True)
    pdf.set_font("Arial", "", 10)
    
    for idx, row in df.iterrows():
        pdf.cell(0, 8, f"{row['Arquivo 1']} vs {row['Arquivo 2']}: {row['Similaridade']:.2%}", ln=True)

    output = pdf.output(dest='S')
    return output.encode('latin-1') if isinstance(output, str) else bytes(output)

def perform_advanced_analysis(files, files_content, language):
    """Perform advanced analysis using analyzer modules."""
    ast_parser = ASTParser()
    metrics_calc = CodeMetrics()
    
    ast_similarities = []
    all_metrics = []
    
    progress_msg = st.empty()
    progress_msg.info("Calculando similaridade estrutural (AST)...")
    
    # Calculate AST similarities
    for i in range(len(files_content)):
        for j in range(i+1, len(files_content)):
            ast_sim = ast_parser.structural_similarity(
                files_content[i], 
                files_content[j], 
                language
            )
            ast_similarities.append((files[i], files[j], ast_sim))
    
    progress_msg.info("Calculando métricas de complexidade...")
    
    # Calculate metrics for each file
    for i, code in enumerate(files_content):
        metrics = metrics_calc.calculate_all_metrics(code, language)
        all_metrics.append({
            'file': files[i],
            'loc': metrics['loc']['code'],
            'cyclomatic': metrics['cyclomatic_complexity'],
            'functions': metrics['function_count'],
            'nesting': metrics['max_nesting_depth'],
            'maintainability': metrics['maintainability_index']
        })
    
    progress_msg.empty()
    
    return {
        'ast_similarities': ast_similarities,
        'metrics': all_metrics
    }

def display_metrics_comparison(metrics1, metrics2, file1, file2):
    """Display metrics comparison between two files."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**{file1}**")
        st.metric("Linhas de Código", metrics1['loc'])
        st.metric("Complexidade Ciclomática", metrics1['cyclomatic'])
        st.metric("Funções/Métodos", metrics1['functions'])
        st.metric("Profundidade Aninhamento", metrics1['nesting'])
        st.metric("Índice Manutenibilidade", f"{metrics1['maintainability']:.1f}")
    
    with col2:
        st.markdown(f"**{file2}**")
        st.metric("Linhas de Código", metrics2['loc'])
        st.metric("Complexidade Ciclomática", metrics2['cyclomatic'])
        st.metric("Funções/Métodos", metrics2['functions'])
        st.metric("Profundidade Aninhamento", metrics2['nesting'])
        st.metric("Índice Manutenibilidade", f"{metrics2['maintainability']:.1f}")

def create_similarity_graph(similarity_matrix, files, min_similarity=0.5, cluster_data=None):
    """
    Create an interactive similarity network graph using Plotly.
    Uses spring layout simulation via Fruchterman-Reingold to position nodes.
    """
    import networkx as nx

    n = len(files)
    mat = np.array(similarity_matrix)

    G = nx.Graph()
    for i, f in enumerate(files):
        G.add_node(i, label=f)
    for i in range(n):
        for j in range(i + 1, n):
            if mat[i, j] >= min_similarity:
                G.add_edge(i, j, weight=mat[i, j])

    if G.number_of_nodes() == 0:
        return None

    # Compute layout
    if G.number_of_edges() > 0:
        pos = nx.spring_layout(G, weight='weight', seed=42, k=1.5)
    else:
        pos = nx.circular_layout(G)

    # Determine node colors based on clusters
    node_colors = ['#636EFA'] * n
    if cluster_data and 'clusters' in cluster_data:
        palette = [
            '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
            '#19D3F3', '#FF6692', '#B6E880', '#FF97FF',
            '#FECB52', '#636EFA'
        ]
        for cid, info in cluster_data['clusters'].items():
            color = palette[(int(cid) - 1) % len(palette)]
            for fname in info['files']:
                if fname in files:
                    node_colors[files.index(fname)] = color

    # Build edge traces
    edge_traces = []
    for i, j, data in G.edges(data=True):
        x0, y0 = pos[i]
        x1, y1 = pos[j]
        sim = data['weight']
        # Opacity proportional to similarity
        opacity = 0.3 + 0.7 * (sim - min_similarity) / max(1 - min_similarity, 0.01)
        width = 1 + 5 * (sim - min_similarity) / max(1 - min_similarity, 0.01)
        edge_traces.append(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode='lines',
            line=dict(width=width, color=f'rgba(150,150,150,{opacity:.2f})'),
            hovertemplate=f'{files[i]} ↔ {files[j]}: {sim:.1%}<extra></extra>',
            showlegend=False
        ))

    # Build node trace
    node_x = [pos[i][0] for i in range(n)]
    node_y = [pos[i][1] for i in range(n)]

    # Compute node size based on degree
    degrees = dict(G.degree())
    node_sizes = [20 + degrees.get(i, 0) * 5 for i in range(n)]

    # Hover text with stats
    hover_texts = []
    for i, fname in enumerate(files):
        neighbors = list(G.neighbors(i))
        if neighbors:
            sims = [mat[i, j] for j in neighbors]
            hover_texts.append(
                f"<b>{fname}</b><br>"
                f"Conexões: {len(neighbors)}<br>"
                f"Sim. média: {np.mean(sims):.1%}<br>"
                f"Sim. máx: {np.max(sims):.1%}"
            )
        else:
            hover_texts.append(f"<b>{fname}</b><br>Sem conexões acima do limiar")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers+text',
        text=[os.path.splitext(f)[0] for f in files],
        textposition='top center',
        textfont=dict(size=10),
        hovertext=hover_texts,
        hoverinfo='text',
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='white'),
            opacity=0.9
        ),
        showlegend=False
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        title=dict(
            text=f"Grafo de Similaridade (limiar ≥ {min_similarity:.0%})",
            x=0.5,
            font=dict(size=16)
        ),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        hovermode='closest',
        margin=dict(l=20, r=20, t=60, b=20),
        height=600,
        plot_bgcolor='rgba(250,250,250,0.8)',
    )
    return fig


def create_diff_view(code1, code2, file1, file2, language='python'):
    """
    Generate side-by-side diff HTML view with highlighted differences.
    Returns HTML string for st.markdown with unsafe_allow_html=True.
    """
    lines1 = code1.splitlines()
    lines2 = code2.splitlines()

    diff = list(unified_diff(lines1, lines2, fromfile=file1, tofile=file2, lineterm=''))

    # Parse diff into changed line numbers
    removed_lines = set()
    added_lines = set()
    line_num1, line_num2 = 0, 0
    for line in diff[2:]:  # Skip the header lines
        if line.startswith('@@'):
            # Parse hunk header like @@ -a,b +c,d @@
            parts = line.split()
            try:
                m = re.match(r'-(\d+)', parts[1])
                if m:
                    line_num1 = int(m.group(1)) - 1
                m = re.match(r'\+(\d+)', parts[2])
                if m:
                    line_num2 = int(m.group(1)) - 1
            except Exception:
                pass
        elif line.startswith('-') and not line.startswith('---'):
            removed_lines.add(line_num1)
            line_num1 += 1
        elif line.startswith('+') and not line.startswith('+++'):
            added_lines.add(line_num2)
            line_num2 += 1
        else:
            line_num1 += 1
            line_num2 += 1

    def render_side(lines, highlight_set, header, color):
        html = f'<div style="flex:1;min-width:0;"><b style="color:{color};">{header}</b><pre style="background:#f8f8f8;padding:10px;border-radius:6px;overflow-x:auto;font-size:12px;line-height:1.5;">'
        for i, line in enumerate(lines, start=1):
            escaped = (line
                       .replace('&', '&amp;')
                       .replace('<', '&lt;')
                       .replace('>', '&gt;'))
            if i in highlight_set:
                bg = '#ffe0e0' if color == '#c0392b' else '#e0ffe0'
                html += f'<span style="background:{bg};display:block;">{i:4d} | {escaped}</span>'
            else:
                html += f'<span style="display:block;">{i:4d} | {escaped}</span>'
        html += '</pre></div>'
        return html

    left = render_side(lines1, removed_lines, file1, '#c0392b')
    right = render_side(lines2, added_lines, file2, '#27ae60')

    return f'<div style="display:flex;gap:12px;">{left}{right}</div>'


def create_enriched_pdf_report(df, files, language, threshold, advanced_analysis=None, cluster_data=None):
    """Enhanced PDF report with metrics, AST scores, and plagiarism patterns."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, "Niklaus - Relatorio de Analise de Plagio", ln=True, align='C')
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=True, align='C')
    pdf.ln(4)

    # Summary box
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Resumo da Analise", ln=True, fill=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(60, 7, f"Linguagem: {language}", ln=False)
    pdf.cell(60, 7, f"Limite de similaridade: {threshold:.0%}", ln=False)
    pdf.cell(0, 7, f"Arquivos analisados: {len(files)}", ln=True)
    pdf.cell(60, 7, f"Pares suspeitos: {len(df)}", ln=False)

    if not df.empty:
        pdf.cell(60, 7, f"Maior similaridade: {df['Similaridade'].max():.1%}", ln=False)
        pdf.cell(0, 7, f"Media: {df['Similaridade'].mean():.1%}", ln=True)
    pdf.ln(6)

    # Results table
    if not df.empty:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Pares com Similaridade Suspeita", ln=True, fill=True)
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(70, 7, "Arquivo 1", border=1, fill=True)
        pdf.cell(70, 7, "Arquivo 2", border=1, fill=True)
        pdf.cell(50, 7, "Similaridade", border=1, fill=True, ln=True)
        pdf.set_font("Arial", "", 10)

        for _, row in df.iterrows():
            sim = row['Similaridade']
            if sim >= 0.9:
                pdf.set_fill_color(255, 180, 180)
            elif sim >= 0.7:
                pdf.set_fill_color(255, 230, 180)
            else:
                pdf.set_fill_color(255, 255, 255)
            f1 = str(row['Arquivo 1'])[:30]
            f2 = str(row['Arquivo 2'])[:30]
            pdf.cell(70, 6, f1, border=1, fill=True)
            pdf.cell(70, 6, f2, border=1, fill=True)
            pdf.cell(50, 6, f"{sim:.2%}", border=1, fill=True, ln=True)
        pdf.ln(6)

    # Advanced metrics table
    if advanced_analysis and advanced_analysis.get('metrics'):
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, "Metricas de Complexidade por Arquivo", ln=True, fill=True)
        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(200, 200, 200)
        cols = [("Arquivo", 55), ("LOC", 20), ("Complexidade", 30), ("Funcoes", 25), ("Aninhamento", 30), ("Manutenib.", 30)]
        for label, w in cols:
            pdf.cell(w, 7, label, border=1, fill=True)
        pdf.ln()
        pdf.set_font("Arial", "", 9)
        for m in advanced_analysis['metrics']:
            pdf.set_fill_color(255, 255, 255)
            fname = str(m['file'])[:22]
            pdf.cell(55, 6, fname, border=1, fill=True)
            pdf.cell(20, 6, str(m['loc']), border=1, fill=True)
            pdf.cell(30, 6, str(m['cyclomatic']), border=1, fill=True)
            pdf.cell(25, 6, str(m['functions']), border=1, fill=True)
            pdf.cell(30, 6, str(m['nesting']), border=1, fill=True)
            pdf.cell(30, 6, f"{m['maintainability']:.1f}", border=1, fill=True, ln=True)
        pdf.ln(6)

        # AST similarities
        if advanced_analysis.get('ast_similarities'):
            pdf.set_font("Arial", "B", 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 8, "Similaridade Estrutural (AST)", ln=True, fill=True)
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(75, 7, "Arquivo 1", border=1, fill=True)
            pdf.cell(75, 7, "Arquivo 2", border=1, fill=True)
            pdf.cell(40, 7, "Sim. AST", border=1, fill=True, ln=True)
            pdf.set_font("Arial", "", 9)
            sorted_ast = sorted(advanced_analysis['ast_similarities'], key=lambda x: x[2], reverse=True)
            for f1, f2, ast_sim in sorted_ast[:20]:
                pdf.set_fill_color(255, 255, 255)
                pdf.cell(75, 6, str(f1)[:30], border=1, fill=True)
                pdf.cell(75, 6, str(f2)[:30], border=1, fill=True)
                pdf.cell(40, 6, f"{ast_sim:.2%}", border=1, fill=True, ln=True)
            pdf.ln(6)

    # Cluster summary
    if cluster_data and cluster_data.get('clusters'):
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, "Analise de Clusters", ln=True, fill=True)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 7, f"Total de clusters: {cluster_data['num_clusters']}", ln=True)
        pdf.cell(0, 7, f"Maior cluster: {cluster_data['largest_cluster']} arquivos", ln=True)
        pdf.cell(0, 7, f"Arestas no grafo: {cluster_data['graph_edges']}", ln=True)
        density_pct = cluster_data['graph_density'] * 100
        pdf.cell(0, 7, f"Densidade do grafo: {density_pct:.1f}%", ln=True)
        pdf.ln(4)

        for cid, info in cluster_data['clusters'].items():
            if info['size'] > 1:
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 7, f"Cluster {cid} ({info['size']} arquivos):", ln=True)
                pdf.set_font("Arial", "", 10)
                for fname in info['files']:
                    pdf.cell(10, 6, "", ln=False)
                    pdf.cell(0, 6, f"- {fname}", ln=True)
                stats = info['stats']
                pdf.cell(0, 6, f"  Similaridade media: {stats['avg_similarity']:.1%}  |  Max: {stats['max_similarity']:.1%}", ln=True)
                pdf.ln(2)

    output = pdf.output(dest='S')
    return output.encode('latin-1') if isinstance(output, str) else bytes(output)


def create_metrics_radar_chart(metrics1, metrics2, file1, file2):
    """Create radar chart comparing metrics."""
    categories = ['LOC', 'Complexidade', 'Funções', 'Aninhamento', 'Manutenibilidade']
    
    # Normalize values to 0-1 scale
    max_loc = max(metrics1['loc'], metrics2['loc'], 1)
    max_cc = max(metrics1['cyclomatic'], metrics2['cyclomatic'], 1)
    max_func = max(metrics1['functions'], metrics2['functions'], 1)
    max_nest = max(metrics1['nesting'], metrics2['nesting'], 1)
    
    values1 = [
        metrics1['loc'] / max_loc,
        metrics1['cyclomatic'] / max_cc,
        metrics1['functions'] / max_func,
        metrics1['nesting'] / max_nest,
        metrics1['maintainability'] / 100
    ]
    
    values2 = [
        metrics2['loc'] / max_loc,
        metrics2['cyclomatic'] / max_cc,
        metrics2['functions'] / max_func,
        metrics2['nesting'] / max_nest,
        metrics2['maintainability'] / 100
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values1,
        theta=categories,
        fill='toself',
        name=file1,
        line_color='blue'
    ))
    
    fig.add_trace(go.Scatterpolar(
        r=values2,
        theta=categories,
        fill='toself',
        name=file2,
        line_color='red'
    ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title="Comparação de Métricas"
    )
    
    return fig

def main():
    st.set_page_config(
        page_title="Niklaus - Detecção de Plágio",
        page_icon=":mag:",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    if 'cancel' not in st.session_state:
        st.session_state['cancel'] = False
    
    if 'last_analysis' not in st.session_state:
        st.session_state['last_analysis'] = None
    
    with st.sidebar:
        st.markdown("## :gear: Configurações")
        
        st.markdown("### Tema")
        theme = st.selectbox("Tema Visual", ["Claro", "Escuro"])
        if theme == "Escuro":
            st.markdown("""
            <style>
            .stApp { background-color: #1e1e1e; color: #f0f0f0; }
            .stMarkdown, .stText { color: #f0f0f0; }
            </style>
            """, unsafe_allow_html=True)
        
        st.markdown("---")

        try:
            api_key = st.secrets["maritaca"]["MARITACA_API_KEY"]
            model = st.secrets["maritaca"].get("MARITACA_MODEL", "sabiazinho-4")
        except KeyError:
            st.error("Configure MARITACA_API_KEY no arquivo .streamlit/secrets.toml")
            st.info("""
Crie o arquivo `.streamlit/secrets.toml` com o seguinte conteúdo:

[maritaca]
MARITACA_API_KEY = "sua-chave-api-aqui"
MARITACA_MODEL = "sabiazinho-4"
""")
            st.stop()
        
        st.markdown("### Linguagem")
        dict_languages_extensions = {
            "C": "c",
            "C++": "cpp",
            "Java": "java",
            "JavaScript": "js",
            "Python": "py",
            "Go": "go",
            "Rust": "rs",
            "TypeScript": "ts",
            "Kotlin": "kt",
        }

        language_selected = st.selectbox(
            "Escolha a linguagem de programação",
            dict_languages_extensions.keys(),
            help="Selecione a linguagem de programação dos arquivos que deseja comparar.",
            key="language_select"
        )
        extension_file = dict_languages_extensions[language_selected].lower()
        
        st.markdown("### Análise")
        preset = st.selectbox(
            "Preset de análise",
            ["Personalizado", "Conservador (80%)", "Moderado (70%)", "Agressivo (50%)"]
        )
        
        presets = {
            "Conservador (80%)": 0.8,
            "Moderado (70%)": 0.7,
            "Agressivo (50%)": 0.5
        }
        
        default_limit = presets.get(preset, st.session_state.get('limit', 0.7))
        
        limit = st.slider(
            "Limite de Similaridade",
            min_value=0.0,
            max_value=1.0,
            value=default_limit,
            step=0.01,
            help="Selecione o limite de similaridade entre os arquivos para ser considerado plágio.",
            key="limit_slider"
        )
        
        st.markdown("---")
        st.markdown("### 📖 Instruções")
        st.markdown("1. Escolha a linguagem")
        st.markdown("2. Ajuste o limite")
        st.markdown("3. Faça upload do ZIP")
        st.markdown("4. Clique em 'Analisar'")
        
        st.markdown("---")
        st.markdown(":computer: [GitHub](https://www.github.com/walternagai/niklaus-plagiarism)")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        ":file_folder: Upload & Análise",
        ":bar_chart: Resultados",
        ":chart_with_upwards_trend: Estatísticas",
        ":microscope: Análise Avançada",
        ":spider_web: Grafo de Similaridade"
    ])
    
    with tab1:
        st.title(":computer: Niklaus")
        st.markdown("### Assistente de Detecção de Plágio em Código")
        st.markdown("Niklaus compara arquivos de código-fonte e identifica similaridades usando análise estática e inteligência artificial.")
        
        st.markdown("---")
        
        zip_file = st.file_uploader(
            "Carregar arquivo ZIP",
            type="zip",
            help="Carregue um arquivo ZIP contendo os arquivos a serem comparados (máx: 50MB)"
        )
        
        if zip_file:
            st.info(f"Arquivo carregado: {zip_file.name} ({zip_file.size / 1024 / 1024:.2f} MB)")
        
        analyze_button = st.button(":mag: Analisar Arquivos", type="primary", use_container_width=True)
        
        if st.session_state['last_analysis']:
            st.markdown("---")
            st.markdown("#### :clock1: Última Análise")
            st.info(f"Arquivos analisados: {st.session_state['last_analysis']['files_count']} | Similaridades encontradas: {st.session_state['last_analysis']['similarities_count']}")
    
    extract_path = tempfile.mkdtemp()
    
    try:
        if analyze_button and zip_file:
            st.session_state['cancel'] = False
            
            if zip_file.size > 50 * 1024 * 1024:
                st.error("Arquivo muito grande. Limite máximo: 50MB")
                st.stop()
            
            with st.spinner("Validando arquivo ZIP..."):
                time.sleep(0.5)
            
            if not zipfile.is_zipfile(zip_file):
                st.error("O arquivo não é um ZIP válido")
                st.stop()
            
            try:
                progress_bar = st.progress(0, text="Extraindo arquivos...")
                
                with ZipFile(zip_file, 'r') as zip_ref:
                    for member in zip_ref.namelist():
                        if member.startswith('/') or '..' in member:
                            st.error("Arquivo ZIP contém caminhos inválidos")
                            st.stop()
                    
                    zip_ref.extractall(path=extract_path)
                
                progress_bar.progress(10, text="Arquivos extraídos!")
                
                files_path = os.path.join(extract_path, zip_file.name.replace(".zip", ""))
                files = os.listdir(files_path)
                
                if not files:
                    st.error("Arquivo ZIP está vazio")
                    st.stop()
                
                if not files[0].endswith(extension_file):
                    st.error(f"Os arquivos extraídos não possuem a extensão .{extension_file}")
                    st.stop()
                
                st.toast(f"✅ {len(files)} arquivos extraídos com sucesso!")
                
                progress_bar.progress(20, text="Lendo arquivos...")
                
                files_content = []
                for i, file in enumerate(files):
                    file_stream = io.BytesIO(open(os.path.join(files_path, file), "rb").read())
                    files_content.append(read_file(file_stream))
                    progress_bar.progress(20 + int(i / len(files) * 30), text=f"Lendo {file}...")
                
                with tab2:
                    pass
                
                with tab3:
                    st.markdown("### :page_facing_up: Preview dos Arquivos")
                    preview_files = st.multiselect("Selecione arquivos para visualizar", files, default=files[:3] if len(files) <= 3 else files[:3])
                    
                    for file in preview_files:
                        with st.expander(f"📄 {file}"):
                            file_idx = files.index(file)
                            st.code(files_content[file_idx], language=language_selected.lower())
                            st.metric("Linhas de código", len(files_content[file_idx].split('\n')))
                
                progress_bar.progress(50, text="Calculando similaridades...")
                
                status_text = st.empty()
                similarities_matrix = []
                total_comparisons = len(files_content) * (len(files_content) - 1) // 2
                current_comparison = 0
                
                for i in range(len(files_content)):
                    if st.session_state['cancel']:
                        st.warning("Análise cancelada pelo usuário")
                        st.stop()
                    
                    for j in range(i+1, len(files_content)):
                        current_comparison += 1
                        progress_text = f"Comparando {files[i]} vs {files[j]} ({current_comparison}/{total_comparisons})"
                        progress_bar.progress(50 + int(current_comparison / total_comparisons * 30), text=progress_text)
                        status_text.text(progress_text)
                        similarity = comparate_files(files_content[i], files_content[j], language_selected)
                        similarities_matrix.append((files[i], files[j], similarity))
                
                progress_bar.progress(80, text="Gerando matriz de similaridade...")
                
                similarities_matrix = sorted(similarities_matrix, key=lambda x: x[2], reverse=True)
                similarities_df = pd.DataFrame(similarities_matrix, columns=["Arquivo 1", "Arquivo 2", "Similaridade"])
                
                n = len(files)
                similarity_mat = [[0.0]*n for _ in range(n)]
                for i in range(n):
                    similarity_mat[i][i] = 1.0
                    for j in range(n):
                        if i < j:
                            similarity_mat[i][j] = next((s[2] for s in similarities_matrix if (s[0] == files[i] and s[1] == files[j]) or (s[0] == files[j] and s[1] == files[i])), 0.0)
                            similarity_mat[j][i] = similarity_mat[i][j]
                
                progress_bar.progress(85, text="Analisando trechos semelhantes...")

                # Perform advanced analysis (AST + metrics)
                advanced_analysis = perform_advanced_analysis(files, files_content, language_selected)
                st.session_state['advanced_analysis'] = advanced_analysis

                progress_bar.progress(90, text="Detectando clusters de plágio...")

                # Cluster analysis
                cluster_detector = ClusterDetector()
                sim_mat_np = np.array(similarity_mat)
                cluster_data = cluster_detector.analyze_clusters(
                    sim_mat_np, files, min_similarity=limit
                )
                st.session_state['cluster_data'] = cluster_data

                similarities_df_filtered = similarities_df[similarities_df["Similaridade"] > limit].copy()
                
                if not similarities_df_filtered.empty:
                    with st.status("Analisando similaridades com IA...", expanded=True) as status:
                        analyses = []
                        
                        # Pre-calculate pattern detection for all pairs
                        pattern_detector = PlagiarismPatternDetector()
                        
                        for idx, row in similarities_df_filtered.iterrows():
                            if st.session_state['cancel']:
                                st.warning("Análise cancelada pelo usuário")
                                st.stop()
                            
                            file1 = row['Arquivo 1']
                            file2 = row['Arquivo 2']
                            file1_idx = files.index(file1)
                            file2_idx = files.index(file2)
                            
                            # Get textual similarity
                            textual_sim = row['Similaridade']
                            
                            # Get AST similarity from advanced analysis
                            ast_sim = 0.0
                            if 'advanced_analysis' in st.session_state and st.session_state['advanced_analysis']:
                                ast_sim = next(
                                    (s[2] for s in st.session_state['advanced_analysis']['ast_similarities']
                                     if (s[0] == file1 and s[1] == file2) or (s[0] == file2 and s[1] == file1)),
                                    0.0
                                )
                            
                            # Detect plagiarism pattern
                            pattern_result = pattern_detector.comprehensive_analysis(
                                files_content[file1_idx],
                                files_content[file2_idx],
                                textual_sim,
                                ast_sim,
                                {'overall_similarity': textual_sim}
                            )
                            
                            plagiarism_type = pattern_result['plagiarism_type']
                            confidence = pattern_result['confidence']
                            
                            analysis = generate_response_maritaca(
                                api_key, model,
                                files_content[file1_idx],
                                files_content[file2_idx],
                                file1, file2,
                                textual_sim, ast_sim,
                                plagiarism_type, confidence
                            )
                            analyses.append(analysis)
                            st.write(f"✓ {file1} ↔ {file2}: {textual_sim:.1%}")
                        
                        similarities_df_filtered['Analise'] = analyses
                        status.update(label="Análise concluída!", state="complete")
                    
                    st.session_state['last_analysis'] = {
                        'files_count': len(files),
                        'similarities_count': len(similarities_df_filtered),
                        'df': similarities_df_filtered,
                        'files': files,
                        'files_content': files_content,
                        'language': language_selected,
                        'threshold': limit,
                        'matrix': similarity_mat,
                        'textual_similarities': similarities_matrix,
                        'cluster_data': cluster_data,
                    }
                else:
                    st.success("✅ Não foram encontrados trechos de código plagiados abaixo do limite definido.")
                    st.session_state['last_analysis'] = {
                        'files_count': len(files),
                        'similarities_count': 0,
                        'df': pd.DataFrame(),
                        'files': files,
                        'files_content': files_content,
                        'language': language_selected,
                        'threshold': limit,
                        'matrix': similarity_mat,
                        'textual_similarities': similarities_matrix,
                        'cluster_data': cluster_data,
                    }
                
                progress_bar.progress(100, text="Análise concluída!")
                st.toast("✅ Análise concluída com sucesso!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")
    
    except Exception as e:
        st.error(f"Erro inesperado: {str(e)}")
    
    finally:
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
    
    if st.session_state['last_analysis']:
        analysis_data = st.session_state['last_analysis']
        
        with tab2:
            if not analysis_data['df'].empty:
                st.markdown("### :bar_chart: Resultados da Análise")
                
                col1, col2, col3 = st.columns([2, 2, 2])
                with col1:
                    st.metric("Arquivos Analisados", analysis_data['files_count'])
                with col2:
                    st.metric("Pares com Similaridade", len(analysis_data['df']))
                with col3:
                    st.metric("Maior Similaridade", f"{analysis_data['df']['Similaridade'].max():.1%}")
                
                st.markdown("---")
                
                min_filter = st.slider(
                    "Filtrar resultados por similaridade mínima",
                    min_value=0.0,
                    max_value=float(analysis_data['df']['Similaridade'].max()),
                    value=float(analysis_data['threshold']),
                    step=0.01
                )
                
                filtered_df = analysis_data['df'][analysis_data['df']['Similaridade'] >= min_filter]
                
                st.dataframe(
                    filtered_df.style.format({"Similaridade": "{:.2%}"}),
                    use_container_width=True,
                    column_config={
                        "Similaridade": st.column_config.ProgressColumn(
                            "Similaridade",
                            format="%.2f%%",
                            min_value=0,
                            max_value=1,
                        )
                    }
                )
                
                st.markdown("### :notebook: Análises Detalhadas")
                for idx, row in filtered_df.iterrows():
                    with st.expander(f":mag_right: {row['Arquivo 1']} ↔ {row['Arquivo 2']} - {row['Similaridade']:.1%}"):
                        st.write_stream(stream_data(row['Analise']))

                        file1_idx = analysis_data['files'].index(row['Arquivo 1'])
                        file2_idx = analysis_data['files'].index(row['Arquivo 2'])

                        view_mode = st.radio(
                            "Modo de visualização",
                            ["Código lado a lado", "Diff interativo"],
                            key=f"view_{idx}",
                            horizontal=True
                        )

                        if view_mode == "Código lado a lado":
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**{row['Arquivo 1']}**")
                                st.code(analysis_data['files_content'][file1_idx], language=analysis_data['language'].lower())
                            with col2:
                                st.markdown(f"**{row['Arquivo 2']}**")
                                st.code(analysis_data['files_content'][file2_idx], language=analysis_data['language'].lower())
                        else:
                            diff_html = create_diff_view(
                                analysis_data['files_content'][file1_idx],
                                analysis_data['files_content'][file2_idx],
                                row['Arquivo 1'],
                                row['Arquivo 2'],
                                analysis_data['language']
                            )
                            st.markdown(diff_html, unsafe_allow_html=True)
                            st.caption("Vermelho = linhas removidas/alteradas | Verde = linhas adicionadas/alteradas")
                
                st.markdown("---")
                st.markdown("### :inbox_tray: Exportar Resultados")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        "📥 Baixar CSV",
                        data=csv,
                        file_name=f"similaridade_plagio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    report = {
                        "timestamp": datetime.now().isoformat(),
                        "language": analysis_data['language'],
                        "threshold": float(analysis_data['threshold']),
                        "files": analysis_data['files'],
                        "similarities": filtered_df.to_dict('records')
                    }
                    st.download_button(
                        "📥 Baixar JSON",
                        data=json.dumps(report, indent=2, ensure_ascii=False),
                        file_name=f"relatorio_plagio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col3:
                    adv_for_pdf = st.session_state.get('advanced_analysis')
                    cluster_for_pdf = analysis_data.get('cluster_data')
                    pdf_data = create_enriched_pdf_report(
                        filtered_df,
                        analysis_data['files'],
                        analysis_data['language'],
                        analysis_data['threshold'],
                        advanced_analysis=adv_for_pdf,
                        cluster_data=cluster_for_pdf
                    )
                    st.download_button(
                        "📥 Baixar PDF",
                        data=pdf_data,
                        file_name=f"relatorio_plagio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.info(":white_check_mark: Nenhum resultado para exibir. Nenhuma similaridade acima do limite foi encontrada.")
        
        with tab3:
            if not analysis_data['df'].empty:
                st.markdown("### :chart_with_upward_trend: Estatísticas e Visualizações")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Média de Similaridade", f"{analysis_data['df']['Similaridade'].mean():.1%}")
                with col2:
                    st.metric("Mediana", f"{analysis_data['df']['Similaridade'].median():.1%}")
                with col3:
                    st.metric("Desvio Padrão", f"{analysis_data['df']['Similaridade'].std():.2f}")
                with col4:
                    st.metric("Acima de 70%", len(analysis_data['df'][analysis_data['df']['Similaridade'] > 0.7]))
                
                st.markdown("---")
                st.markdown("### :fire: Mapa de Calor de Similaridade")
                
                fig = create_heatmap(analysis_data['files'], analysis_data['matrix'])
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                st.markdown("### :bar_chart: Distribuição de Similaridades")
                
                hist_df = analysis_data['df'].copy()
                hist_df['Faixa'] = pd.cut(
                    hist_df['Similaridade'],
                    bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                    labels=['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
                )
                
                hist_fig = px.bar(
                    hist_df['Faixa'].value_counts().sort_index(),
                    title="Distribuição de Pares por Faixa de Similaridade",
                    labels={'index': 'Faixa', 'value': 'Quantidade'},
                    color='value',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(hist_fig, use_container_width=True)
            else:
                st.info(":white_check_mark: Sem dados estatísticos disponíveis.")
        
        with tab4:
            st.markdown("### :microscope: Análise Avançada de Código")
            st.markdown("**Análise estrutural (AST), métricas de complexidade e detecção de padrões de plágio**")
            
            if not analysis_data['df'].empty:
                st.markdown("---")
                st.markdown("#### Similaridade Estrutural (AST)")
                st.info("A similaridade estrutural compara a árvore sintática do código, identificando similaridades mesmo com variáveis renomeadas ou código reorganizado.")
                
                if 'advanced_analysis' in st.session_state and st.session_state['advanced_analysis']:
                    adv = st.session_state['advanced_analysis']
                    
                    # AST Similarities
                    ast_df = pd.DataFrame(adv['ast_similarities'], columns=['Arquivo 1', 'Arquivo 2', 'Similaridade Estrutural'])
                    ast_df = ast_df.sort_values('Similaridade Estrutural', ascending=False)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Similaridade Estrutural Média", f"{ast_df['Similaridade Estrutural'].mean():.1%}")
                    with col2:
                        st.metric("Similaridade Estrutural Máxima", f"{ast_df['Similaridade Estrutural'].max():.1%}")
                    
                    st.dataframe(
                        ast_df.style.format({"Similaridade Estrutural": "{:.2%}"}),
                        use_container_width=True
                    )
                    
                    st.markdown("---")
                    st.markdown("#### Métricas de Complexidade")
                    
                    # Metrics summary
                    metrics_all = []
                    for m in adv['metrics']:
                        metrics_all.append({
                            'Arquivo': m['file'],
                            'LOC': m['loc'],
                            'Complexidade': m['cyclomatic'],
                            'Funções': m['functions'],
                            'Aninhamento': m['nesting'],
                            'Manutenibilidade': m['maintainability']
                        })
                    
                    metrics_df = pd.DataFrame(metrics_all)
                    st.dataframe(metrics_df, use_container_width=True)
                    
                    st.markdown("---")
                    st.markdown("#### Análise de Métricas Comparativas")
                    
                    # Select files to compare
                    file_pairs = [(row['Arquivo 1'], row['Arquivo 2']) for _, row in analysis_data['df'].iterrows()]
                    selected_pair_idx = st.selectbox(
                        "Selecione par de arquivos para análise detalhada",
                        range(len(file_pairs)),
                        format_func=lambda x: f"{file_pairs[x][0]} vs {file_pairs[x][1]}"
                    )
                    
                    if selected_pair_idx is not None and len(file_pairs) > 0:
                        file1, file2 = file_pairs[selected_pair_idx]
                        
                        # Get metrics for both files
                        m1 = next((m for m in adv['metrics'] if m['file'] == file1), None)
                        m2 = next((m for m in adv['metrics'] if m['file'] == file2), None)
                        
                        if m1 and m2:
                            # Display metrics comparison
                            display_metrics_comparison(m1, m2, file1, file2)
                            
                            # Radar chart
                            radar_fig = create_metrics_radar_chart(m1, m2, file1, file2)
                            st.plotly_chart(radar_fig, use_container_width=True)
                            
                            # Pattern detection
                            st.markdown("---")
                            st.markdown("#### Detecção de Padrões de Plágio")
                            
                            file_idx1 = analysis_data['files'].index(file1)
                            file_idx2 = analysis_data['files'].index(file2)
                            
                            textual_sim = next((s[2] for s in analysis_data.get('textual_similarities', []) 
                                               if (s[0] == file1 and s[1] == file2) or (s[0] == file2 and s[1] == file1)), 0)
                            
                            ast_sim = next((s[2] for s in adv['ast_similarities']
                                           if (s[0] == file1 and s[1] == file2) or (s[0] == file2 and s[1] == file1)), 0)
                            
                            pattern_detector = PlagiarismPatternDetector()
                            
                            pattern_analysis = pattern_detector.comprehensive_analysis(
                                analysis_data['files_content'][file_idx1],
                                analysis_data['files_content'][file_idx2],
                                textual_sim,
                                ast_sim,
                                {'overall_similarity': 0.5}
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Tipo Detectado", pattern_analysis['plagiarism_type'].replace('_', ' '))
                            with col2:
                                st.metric("Confiança", f"{pattern_analysis['confidence']:.1%}")
                            
                            st.info(f"**Explicação:** {pattern_analysis['explanation']}")
                            
                            with st.expander("Detalhes dos Padrões"):
                                st.json(pattern_analysis['patterns_detected'])
                else:
                    st.warning("Execute uma análise para ver os dados avançados.")
            else:
                st.info(":white_check_mark: Nenhum dado disponível. Execute uma análise primeiro.")

        with tab5:
            st.markdown("### :spider_web: Grafo de Similaridade")
            st.markdown(
                "Cada **nó** representa um arquivo. "
                "As **arestas** conectam pares com similaridade acima do limiar escolhido, "
                "com espessura proporcional à similaridade. "
                "Cores indicam o cluster (grupo) ao qual o arquivo pertence."
            )

            cluster_data = analysis_data.get('cluster_data')

            if cluster_data:
                # Controls
                col_ctrl1, col_ctrl2 = st.columns([1, 2])
                with col_ctrl1:
                    graph_threshold = st.slider(
                        "Limiar do grafo",
                        min_value=0.0,
                        max_value=1.0,
                        value=float(analysis_data['threshold']),
                        step=0.05,
                        key="graph_threshold",
                        help="Apenas pares com similaridade acima deste valor aparecem no grafo"
                    )
                with col_ctrl2:
                    st.markdown("")  # spacer

                # Rebuild graph with chosen threshold (for display only)
                cluster_detector = ClusterDetector()
                sim_mat_np = np.array(analysis_data['matrix'])
                display_cluster_data = cluster_detector.analyze_clusters(
                    sim_mat_np, analysis_data['files'], min_similarity=graph_threshold
                )

                graph_fig = create_similarity_graph(
                    analysis_data['matrix'],
                    analysis_data['files'],
                    min_similarity=graph_threshold,
                    cluster_data=display_cluster_data
                )

                if graph_fig:
                    st.plotly_chart(graph_fig, use_container_width=True)
                else:
                    st.info("Nenhuma conexão acima do limiar definido. Reduza o limiar para visualizar o grafo.")

                st.markdown("---")
                st.markdown("#### Resumo dos Clusters")

                # Summary metrics
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.metric("Total de clusters", display_cluster_data['num_clusters'])
                with col_m2:
                    st.metric("Maior cluster", f"{display_cluster_data['largest_cluster']} arquivos")
                with col_m3:
                    st.metric("Arestas no grafo", display_cluster_data['graph_edges'])
                with col_m4:
                    density_pct = display_cluster_data['graph_density'] * 100
                    st.metric("Densidade do grafo", f"{density_pct:.1f}%")

                st.markdown("---")
                st.markdown("#### Detalhes por Cluster")

                suspicious_clusters = {
                    cid: info for cid, info in display_cluster_data['clusters'].items()
                    if info['size'] > 1
                }

                if suspicious_clusters:
                    for cid, info in sorted(suspicious_clusters.items(), key=lambda x: x[1]['size'], reverse=True):
                        avg_sim = info['stats']['avg_similarity']
                        max_sim = info['stats']['max_similarity']

                        # Color badge by severity
                        if avg_sim >= 0.9:
                            badge = ":red_circle:"
                            label = "Suspeita Alta"
                        elif avg_sim >= 0.7:
                            badge = ":orange_circle:"
                            label = "Suspeita Moderada"
                        else:
                            badge = ":yellow_circle:"
                            label = "Suspeita Baixa"

                        with st.expander(f"{badge} Cluster {cid} — {info['size']} arquivos | {label} | Sim. média: {avg_sim:.1%}"):
                            # Central files
                            if info.get('central_files'):
                                st.markdown("**Arquivos mais centrais** (possíveis originais ou cópias primárias):")
                                for fname, centrality in info['central_files']:
                                    st.markdown(f"- `{fname}` — centralidade: {centrality:.1%}")

                            st.markdown("**Todos os arquivos no cluster:**")
                            for fname in info['files']:
                                st.markdown(f"- `{fname}`")

                            st.markdown(f"""
                            **Estatísticas do cluster:**
                            - Similaridade média: `{avg_sim:.1%}`
                            - Similaridade máxima: `{max_sim:.1%}`
                            - Similaridade mínima: `{info['stats']['min_similarity']:.1%}`
                            """)
                else:
                    st.success("Nenhum cluster suspeito detectado para o limiar atual.")

                # Community detection results
                if display_cluster_data.get('communities') and len(display_cluster_data['communities']) > 0:
                    st.markdown("---")
                    st.markdown("#### Comunidades Detectadas (Modularidade)")
                    st.caption("Detecção de comunidades por otimização de modularidade (algoritmo greedy).")
                    communities = display_cluster_data['communities']
                    non_trivial = [c for c in communities if len(c) > 1]
                    if non_trivial:
                        for i, comm in enumerate(non_trivial, 1):
                            member_names = [analysis_data['files'][idx] for idx in comm if idx < len(analysis_data['files'])]
                            st.markdown(f"**Comunidade {i}** ({len(comm)} membros): " + ", ".join(f"`{f}`" for f in member_names))
                    else:
                        st.info("Nenhuma comunidade com mais de 1 membro detectada.")
            else:
                st.info("Execute uma análise para visualizar o grafo de similaridade.")

    if st.button("🛑 Cancelar Análise"):
        st.session_state['cancel'] = True
        st.warning("Solicitação de cancelamento enviada...")
    
    st.markdown("---")
    st.markdown(":male-teacher: Desenvolvido por [Walter Nagai](https://www.github.com/walternagai)")

if __name__ == "__main__":
    main()
