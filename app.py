import io
import os
import re
import time
import json
import string
import random
import shutil
import tempfile
import chardet
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from zipfile import ZipFile 
from difflib import SequenceMatcher  
from langchain_groq import ChatGroq
from datetime import datetime
from fpdf import FPDF

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

def generate_response_groq(api_key, model, file_content, file_content_to_compare):
    model = ChatGroq(model=model,
                     temperature=0.7, 
                     max_tokens=1024,
                     api_key=api_key)
    
    prompt = f"Compare o código 1: ```{file_content}``` com o código 2: ```{file_content_to_compare}``` e identifique trechos plagiados."

    messages = [
        ("system", 
            """
            Você é Niklaus, um assistente virtual especializado em auxiliar professores de programação na análise e 
            comparação de projetos práticos entregues pelos alunos dos professores. 
            
            Seu objetivo é facilitar a identificação de trechos de código semelhantes, detectar plágios e fornecer 
            insights sobre padrões comuns nos projetos. 
            
            Siga as diretrizes abaixo para oferecer assistência eficaz:
            * Recepção e Organização de Projetos:
                - Aceitar e organizar projetos submetidos em formatos compatíveis (código-fonte, documentação, etc.).
                - Identificar metadados relevantes contidos nos projetos (nome do aluno, data, linguagem, descrição).

            * Análise de Similaridade e Detecção de Plágio:
                - Utilizar técnicas computacionais para comparar códigos e identificar trechos semelhantes.
                - Realizar comparações usando dados quantitativos, como métricas de complexidade ciclomática, 
                número de linhas de código, número de funções/métodos, e cobertura de testes.
                - Gerar relatórios detalhados destacando áreas de coincidência ou similaridades.
                - Utilizar algoritmos que analisam estrutura, lógica e comentários para detectar plágio.
                - Identificar padrões de cópia e colagem, tradução, substituição de variáveis e reordenação de instruções.
                - Considerar a originalidade, complexidade e eficiência dos projetos ao avaliar a similaridade.

            * Geração de Relatórios e Visualizações:
                - Criar relatórios resumindo análises de similaridade e plágio.
                - Fornecer visualizações gráficas (mapas de calor, redes de similaridade) para ilustrar relações entre projetos.

            * Instruções Adicionais:
                - Comunique-se de forma clara, objetiva e profissional.
                - Adapte análises e sugestões ao contexto dos projetos.
                - Utilize fontes e algoritmos confiáveis para garantir precisão e integridade.
                - Incentive a originalidade e criatividade promovendo um ambiente de aprendizado justo.
                - Todas as respostas devem ser escritas em português do Brasil.
            """
        ),
        ("human", prompt)
    ]
    response = model.invoke(messages)
    return response.content

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
    
    return pdf.output(dest='S').encode('latin-1')

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
        
        api_key = os.getenv('GROQ_API_KEY') or st.secrets.get("pytheo_groq", {}).get("GROQ_API_KEY")
        model = os.getenv('GROQ_MODEL') or st.secrets.get("pytheo_groq", {}).get("GROQ_MODEL")
        
        if not api_key:
            st.error("Configure GROQ_API_KEY nas variáveis de ambiente ou no arquivo .streamlit/secrets.toml")
            st.stop()
        
        st.markdown("### Linguagem")
        dict_languages_extensions = {
            "C": "c",
            "C++": "cpp",
            "Java": "java",
            "JavaScript": "js",
            "Python": "py",
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
    
    tab1, tab2, tab3 = st.tabs([":file_folder: Upload & Análise", ":bar_chart: Resultados", ":chart_with_upward_trend: Estatísticas"])
    
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
                
                progress_bar.progress(90, text="Analisando trechos semelhantes...")
                
                similarities_df_filtered = similarities_df[similarities_df["Similaridade"] > limit]
                
                if not similarities_df_filtered.empty:
                    with st.status("Analisando similaridades com IA...", expanded=True) as status:
                        analyses = []
                        for idx, row in similarities_df_filtered.iterrows():
                            if st.session_state['cancel']:
                                st.warning("Análise cancelada pelo usuário")
                                st.stop()
                            
                            file1_idx = files.index(row['Arquivo 1'])
                            file2_idx = files.index(row['Arquivo 2'])
                            analysis = generate_response_groq(api_key, model, files_content[file1_idx], files_content[file2_idx])
                            analyses.append(analysis)
                            st.write(f"✓ {row['Arquivo 1']} ↔ {row['Arquivo 2']}: {row['Similaridade']:.1%}")
                        
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
                        'matrix': similarity_mat
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
                        'matrix': similarity_mat
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
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**{row['Arquivo 1']}**")
                            st.code(analysis_data['files_content'][file1_idx], language=analysis_data['language'].lower())
                        with col2:
                            st.markdown(f"**{row['Arquivo 2']}**")
                            st.code(analysis_data['files_content'][file2_idx], language=analysis_data['language'].lower())
                
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
                    pdf_data = create_pdf_report(filtered_df, analysis_data['files'], analysis_data['language'], analysis_data['threshold'])
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
    
    if st.button("🛑 Cancelar Análise"):
        st.session_state['cancel'] = True
        st.warning("Solicitação de cancelamento enviada...")
    
    st.markdown("---")
    st.markdown(":male-teacher: Desenvolvido por [Walter Nagai](https://www.github.com/walternagai)")

if __name__ == "__main__":
    main()