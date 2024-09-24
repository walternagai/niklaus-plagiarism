import re
import time
import chardet
from difflib import SequenceMatcher  
import streamlit as st
from langchain_groq import ChatGroq

def remove_blank_spaces_and_comments(code, language):
    if language.lower() == 'python':
        code = re.sub(r'#.*', '', code)
        code = re.sub(r'(\"\"\".*?\"\"\"|\'\'\'.*?\'\'\'|".*?"|\'.*?\')', '', code, flags=re.DOTALL)
    elif language.lower() in ['c', 'c++', 'java', 'javascript']:
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'(\".*?\"|\'.*?\')', '', code, flags=re.DOTALL)

    code = re.sub(r'\s+', ' ', code)
    
    return code

def read_file(file):
    file_content = file.getvalue()
    file_encoding = chardet.detect(file_content)['encoding']
    file_content = file_content.decode(file_encoding)
    return file_content

def calculate_similarity(code1, code2):
    my_seq = SequenceMatcher(a = code1, b = code2)  
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
                     api_key=api_key)
    
    prompt = f"Compare o código abaixo com o código a seguir e identifique possíveis trechos plagiados.\n\n{file_content}\n\n{file_content_to_compare}"

    messages = [
        ("system", 
            """Você é Niklaus, um assistente virtual especializado em auxiliar professores de programação na análise e comparação de projetos práticos entregues pelos alunos. Seu objetivo é facilitar a identificação de trabalhos semelhantes, detectar possíveis plágios e fornecer insights sobre padrões comuns nos projetos. Siga as diretrizes abaixo para oferecer assistência eficaz:

Recepção e Organização de Projetos:

Aceitar e organizar projetos submetidos em formatos compatíveis (código-fonte, documentação, etc.).
Catalogar projetos com metadados relevantes (nome do aluno, data, linguagem, descrição).
Análise de Similaridade e Detecção de Plágio:

Utilizar técnicas avançadas para comparar códigos e identificar trechos semelhantes.
Realizar comparações usando dados quantitativos, como métricas de complexidade ciclomática, número de linhas de código, número de funções/métodos, e cobertura de testes.
Gerar relatórios detalhados com índices de similaridade e destacar áreas de coincidência.
Implementar algoritmos que analisam estrutura, lógica e comentários para detectar plágio.
Alertar sobre possíveis casos de plágio e sugerir ações conforme as políticas acadêmicas.
Pesquisa de Trabalhos Externos:

Buscar projetos similares em repositórios públicos (GitHub, GitLab) e bases de dados acadêmicas.
Comparar projetos submetidos com trabalhos externos para verificar originalidade.
Fornecer links e referências de projetos com similaridades significativas.
Geração de Relatórios e Visualizações:

Criar relatórios personalizados resumindo análises de similaridade e plágio.
Fornecer visualizações gráficas (mapas de calor, redes de similaridade) para ilustrar relações entre projetos.
Permitir exportação de relatórios em formatos comuns (PDF, Excel).
Sugestões de Melhoria e Boas Práticas:

Identificar áreas para aprimoramento nas habilidades de programação e originalidade dos alunos.
Sugerir recursos educacionais (tutoriais, cursos, leituras) para desenvolvimento das competências.
Promover boas práticas de codificação e originalidade com feedback construtivo.
Gestão de Referências e Bibliografia:

Verificar referências utilizadas nos projetos, garantindo citação adequada de fontes externas.
Detectar ausência de referências e incentivar a correta atribuição de trabalhos de terceiros.
Confidencialidade e Segurança:

Manter confidencialidade dos projetos submetidos, protegendo a privacidade dos alunos.
Implementar medidas de segurança para evitar acesso não autorizado aos projetos e análises.
Suporte e Feedback Contínuo:

Responder a dúvidas dos professores sobre análises e interpretar resultados fornecidos.
Coletar feedback para aprimorar continuamente as funcionalidades e precisão das análises.
Instruções Adicionais:

Comunique-se de forma clara, objetiva e profissional.
Adapte análises e sugestões ao contexto da disciplina e ao nível dos alunos.
Utilize fontes e algoritmos confiáveis para garantir precisão e integridade.
Respeite as políticas acadêmicas e éticas da instituição.
Incentive a originalidade e criatividade dos alunos, promovendo um ambiente de aprendizado justo.
Responda as questões dos professores com precisão e eficiência, fornecendo insights valiosos sobre os projetos submetidos.
Todas as respostas devem estar em português do Brasil.
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

def main():    
    api_key = st.secrets.pytheo_groq.GROQ_API_KEY
    model = st.secrets.pytheo_groq.GROQ_MODEL

    st.title("Niklaus")

    st.write("Niklaus é um assistente virtual para ajudar a encontrar plágios em projetos práticos de programação.")

    dict_languages_extensions = {
        "Python": "py",
        "Java": "java",
        "C": "c",
        "C++": "cpp",
        "JavaScript": "js"
    }

    language_selected = st.selectbox("Escolha a linguagem de programação", 
                                     dict_languages_extensions.keys(), 
                                     help="Selecione a linguagem de programação dos arquivos que deseja comparar.")

    how_many_files = st.number_input("Quantos arquivos você deseja comparar?", 
                                     min_value=2, max_value=10, 
                                     value=2, 
                                     help="Selecione a quantidade de arquivos que deseja comparar.")

    extensions_list = list(dict_languages_extensions.values())

    extension_file = dict_languages_extensions[language_selected].lower()

    files = []
    for i in range(how_many_files):
        file = st.file_uploader(f"Arquivo {i+1}", 
                                type=extension_file,
                                help=f"Carregue o arquivo {i+1} para comparar com os demais.")
        if file:
            files.append(file)
            st.warning(f"Arquivo {file.name} carregado com sucesso!")

    if len(files) == how_many_files:
        if st.button("Comparar arquivos"):
            files_content = []
            for file in files:
                files_content.append(read_file(file))

            st.markdown("### Similaridade entre os arquivos")
            for i in range(len(files_content)):
                for j in range(i+1, len(files_content)):
                    similarity = comparate_files(files_content[i], files_content[j], language_selected)
                    st.metric(label=f"Arquivos: ``{files[i].name}`` e ``{files[j].name}``", 
                              value=f"{similarity:.2%}" if similarity > 0.0 else "0 %")                        

                    if similarity > 0.7:
                        st.error("Os arquivos possuem mais de 70% de similaridade.")
                        response = generate_response_groq(api_key, model, files_content[i], files_content[j])
                        st.write_stream(stream_data(response))
                    elif similarity > 0.5:
                        st.warning("Os arquivos possuem mais de 50% de similaridade.")
                    elif similarity > 0.3:
                        st.info("Os arquivos possuem mais de 30% de similaridade.")

            if st.button("Limpar"):
                st.caching.clear_cache()
                for file in files:
                    file.close()
                    file.unlink()

if __name__ == "__main__":
    main()
