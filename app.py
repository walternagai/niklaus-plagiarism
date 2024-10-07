import io
import os
import re
import time
import string
import random
import chardet
import pandas as pd
import streamlit as st
from zipfile import ZipFile 
from difflib import SequenceMatcher  
from langchain_groq import ChatGroq

def remove_blank_spaces_and_comments(code, language):
    """
    Remove espaços em branco e comentários de um código-fonte.
    Parâmetros:
    - code: str - Código-fonte a ser processado.
    - language: str - Linguagem de programação do código-fonte.
    Retorno:
    - str - Código-fonte sem espaços em branco e comentários
    """
    if language.lower() == 'python':
        # Remove comentários de uma linha
        code = re.sub(r'#.*', '', code)
        # Remove comentários de múltiplas linhas
        code = re.sub(r'(\"\"\".*?\"\"\"|\'\'\'.*?\'\'\'|".*?"|\'.*?\')', '', code, flags=re.DOTALL)
    elif language.lower() in ['c', 'c++', 'java', 'javascript']:
        # Remove comentários de uma linha
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        # Remove comentários de múltiplas linhas
        code = re.sub(r'//.*', '', code)
        # Remove strings
        code = re.sub(r'(\".*?\"|\'.*?\')', '', code, flags=re.DOTALL)
        # Remove espaços em branco
        code = re.sub(r'\s+', ' ', code)
    # Remove espaços em branco no início e no final
    code = code.strip()
    return code

def read_file(file):
    """
    Lê o conteúdo de um arquivo.
    Parâmetros:
    - file: BytesIO - Arquivo a ser lido.
    Retorno:
    - str - Conteúdo do arquivo.
    """
    # Lê o conteúdo do arquivo
    file_content = file.getvalue()
    # Detecta o encoding do arquivo
    file_encoding = chardet.detect(file_content)['encoding']
    # Decodifica o arquivo
    file_content = file_content.decode(file_encoding)
    # Retorna o conteúdo do arquivo
    return file_content

def calculate_similarity(code1, code2):
    """
    Calcula a similaridade entre dois códigos-fonte.
    Parâmetros:
    - code1: str - Código-fonte a ser comparado.
    - code2: str - Código-fonte de referência.
    Retorno:
    - float - Similaridade entre os códigos-fonte (0.0 a 1.0).
    """
    # Calcula a similaridade entre os códigos-fonte
    my_seq = SequenceMatcher(a = code1, b = code2)

    # Retorna a similaridade
    return my_seq.ratio()

def comparate_files(code1, code2, language='python'):
    """
    Compara dois códigos-fonte e retorna a similaridade entre eles.
    Parâmetros:
    - code1: str - Código-fonte a ser comparado.
    - code2: str - Código-fonte de referência.
    - language: str - Linguagem de programação dos códigos-fonte.
    Retorno:
    - float - Similaridade entre os códigos-fonte (0.0 a 1.0).
    """
    # Converte a linguagem para minúsculo
    language = language.lower()

    # Se code1 ou code2 forem vazios, retorna 0.0
    if not code1 or not code2:
        return 0.0
    
    # clean_code1 e clean_code2 são os códigos sem espaços em branco e comentários
    clean_code1 = remove_blank_spaces_and_comments(code1, language)
    clean_code2 = remove_blank_spaces_and_comments(code2, language)

    # Calcula a similaridade entre os códigos-fonte    
    similaridade = calculate_similarity(clean_code1, clean_code2)

    # Retorna a similaridade
    return similaridade

def generate_response_groq(api_key, model, file_content, file_content_to_compare):
    """
    Gera uma resposta a partir de um modelo Groq.
    Parâmetros:
    - api_key: str - Chave de API do modelo Groq.
    - model: str - Modelo Groq a ser utilizado.
    - file_content: str - Conteúdo do arquivo a ser comparado.
    - file_content_to_compare: str - Conteúdo do arquivo de referência.
    Retorno:
    - str - Resposta gerada pelo modelo GPT-3.
    """
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
    """
    Gera um stream de dados a partir de uma resposta.
    Parâmetros:
    - response: str - Resposta a ser processada.
    """
    for word in response.split(" "):
        yield word + " "
        time.sleep(0.01)

def id_generator(size=16, chars=string.ascii_lowercase + string.digits):
    """
    Gera um identificador aleatório.
    Parâmetros:
    - size: int - Tamanho do identificador.
    - chars: str - Caracteres possíveis para o identificador.
    Retorno:
    - str - Identificador gerado.
    """
    return ''.join(random.choice(chars) for _ in range(size))

def main():    
    # Chaves de API e modelo Groq
    api_key = st.secrets.pytheo_groq.GROQ_API_KEY
    model = st.secrets.pytheo_groq.GROQ_MODEL

    # Dicionário de linguagens de programação e extensões de arquivos
    dict_languages_extensions = {
        "C": "c",
        "C++": "cpp",
        "Java": "java",
        "JavaScript": "js",
        "Python": "py",
    }

    extract_path = "extracted_files"

    st.title(":computer: Niklaus")

    st.write("Niklaus é um assistente virtual para ajudar a encontrar plágios em projetos práticos de programação.")

    st.markdown("### Como usar?")

    st.markdown("1. **Escolha a linguagem de programação** dos arquivos que deseja comparar.")
    st.markdown("2. **Defina o limite de similaridade** entre os arquivos para ser considerado plágio.")
    st.markdown("3. **Carregue um arquivo ZIP** contendo os arquivos a serem comparados.")
    st.markdown("4. **Aguarde a análise** de similaridade entre os arquivos.")    

    columns_options = st.columns(2)

    # Seleção da linguagem de programação
    with columns_options[0]:
        language_selected = st.selectbox("Escolha a linguagem de programação", 
                                         dict_languages_extensions.keys(), 
                                         help="Selecione a linguagem de programação dos arquivos que deseja comparar.")
        extension_file = dict_languages_extensions[language_selected].lower()
    
    # Limite de similaridade entre os arquivos
    with columns_options[1]:
        limit = st.slider("Similaridade", 
                          min_value=0.0, 
                          max_value=1.0, 
                          value=0.7, 
                          step=0.05,
                          help="Selecione o limite de similaridade entre os arquivos para ser considerado plágio.")

    # Carregamento do arquivo ZIP com os arquivos a serem comparados
    zip_file = st.file_uploader("Carregar arquivo ZIP", 
                                type="zip",
                                help="Carregue um arquivo ZIP contendo os arquivos a serem comparados.")

    # se o diretório de extração não existir, cria o diretório
    if not os.path.exists(extract_path):
        os.makedirs(extract_path)

    # se o arquivo ZIP foi carregado
    if zip_file:
        # extrair os arquivos do arquivo ZIP
        with ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(path=extract_path)

        # obter a lista de arquivos extraídos
        files_path = os.path.join(extract_path, zip_file.name.replace(".zip", f""))

        # obter a lista de arquivos extraídos
        files = os.listdir(files_path)

        # se os arquivos extraídos possuem a extensão correta 
        if files[0].endswith(extension_file):
            # exibir mensagem de sucesso
            st.toast(f"Arquivos extraídos com sucesso!")

            # ler o conteúdo dos arquivos
            files_content = []
            for file in files:
                file_stream = io.BytesIO(open(os.path.join(files_path, file), "rb").read())
                files_content.append(read_file(file_stream))

            st.markdown("### Análise de similaridade entre os arquivos")

            # gerar matriz de similaridades
            similarities_matrix = []
            for i in range(len(files_content)):
                for j in range(i+1, len(files_content)):
                    # comparar os arquivos e calcular a similaridade entre eles
                    similarity = comparate_files(files_content[i], files_content[j], language_selected)
                    # adicionar à matriz de similaridades
                    similarities_matrix.append((files[i], files[j], similarity))

            # ordenar a matriz de similaridades pela maior similaridade decrescente
            similarities_matrix = sorted(similarities_matrix, key=lambda x: x[2], reverse=True)

            # criar um DataFrame com a matriz de similaridades
            similarities_df = pd.DataFrame(similarities_matrix, columns=["Arquivo 1", "Arquivo 2", "Similaridade"])

            # filtrar as similaridades acima do limite
            similarities_df_filtered = similarities_df[similarities_df["Similaridade"] > limit]

            # se a matriz de similaridades filtrada não estiver vazia
            if not similarities_df_filtered.empty:
                # exibir similaridades acima do limite
                with st.status("Analisando similaridades...") as status:
                    # adicionar coluna para armazenar a análise de similaridade entre os arquivos
                    for i, row in similarities_df_filtered.iterrows():
                        similarities_df_filtered.loc[i, "Analise"] = generate_response_groq(api_key, model, files_content[i], files_content[j])
                        status.update(label=f"Analisando similaridades... {i+1}/{len(similarities_df_filtered)}", state="running")

                    # atualizar o status da análise
                    status.update(label="Análise finalizada!", state="complete")

                # exibir similaridades acima do limite com a análise de similaridade entre os arquivos
                for i, row in similarities_df_filtered.iterrows():
                    # exibir similaridades acima do limite com a análise de similaridade entre os arquivos
                    st.markdown(f"#### {row['Arquivo 1']} x {row['Arquivo 2']} com {row['Similaridade']:.2%} de similaridade")
                    # exibir análise de similaridade entre os arquivos em um stream de dados
                    st.write_stream(stream_data(row["Analise"]))

                # exibir mensagem de conclusão
                st.toast("Análise concluída!")
            else:
                st.markdown("**Não foram encontrados trechos de código plagiados.**")
        else:
            st.error("Os arquivos extraídos não possuem a extensão correta.")
            st.stop()

    # rodapé da aplicação
    st.markdown("---")
    st.markdown(":computer: Código-fonte disponível em [https://www.github.com/walternagai/niklaus-plagiarism](https://www.github.com/walternagai/niklaus-plagiarism)")
    st.markdown(":male-teacher: Desenvolvido por [https://www.github.com/walternagai](https://www.github.com/walternagai)")

if __name__ == "__main__":
    main()
