#include <iostream>
#include <fstream>
#include <ctime>

/*
 * Projeto: Análise de Algoritmos de Ordenação
 * Integrantes: Arthur Wellington Coelho Santana, Keila Silva Costa, Elioenay Jaiane Dias Gonçalves
 * Data de Submissão: 17/09/2024
 * Descrição: Este programa implementa cinco algoritmos de ordenação (Bubble Sort, Bubble Sort Melhorado,
 * Selection Sort, Insertion Sort e Quick Sort) e analisa o desempenho de cada um em termos de tempo de execução.
 * O programa lê dados de três arquivos de entrada, aplica cada algoritmo de ordenação aos dados, mede o tempo
 * de execução, verifica a correção da ordenação e gera um relatório de resultados em um arquivo de saída.
 */

const int TAMANHO = 100000; // Define o tamanho fixo para os arrays

// Função para carregar os dados do arquivo para a memória
void carregarDados(const char* nomeArquivo, int vet[], int tamanho) {
    std::ifstream arquivo(nomeArquivo);
    // Lê cada número do arquivo e armazena no array vet
    for (int i = 0; i < tamanho; i++) {
        arquivo >> vet[i];
    }
    arquivo.close();
}

// Bubble Sort (Versão 1): Algoritmo de ordenação por bolha
void bubbleSort1(int vet[], int tamanho) {
    for (int i = 0; i < tamanho; i++) {
        for (int j = 0; j < tamanho - 1; j++) {
            // Se o elemento atual é maior que o próximo, faz a troca
            if (vet[j] > vet[j + 1]) {
                int temp = vet[j];
                vet[j] = vet[j + 1];
                vet[j + 1] = temp;
            }
        }
    }
}

// Bubble Sort Melhorado (Versão 3): Algoritmo de ordenação por bolha com otimização
void bubbleSortMelhorado(int vet[], int tamanho) {
    bool trocou;
    for (int i = 0; i < tamanho - 1; i++) {
        trocou = false;
        for (int j = 0; j < tamanho - i - 1; j++) {
            // Se o elemento atual é maior que o próximo, faz a troca
            if (vet[j] > vet[j + 1]) {
                int temp = vet[j];
                vet[j] = vet[j + 1];
                vet[j + 1] = temp;
                trocou = true; // Marca que houve troca
            }
        }
        // Se nenhuma troca foi feita na última passada, o array está ordenado
        if (!trocou) break;
    }
}

// Selection Sort: Algoritmo de ordenação por seleção
void selectionSort(int vet[], int tamanho) {
    for (int i = 0; i < tamanho - 1; i++) {
        int indiceMenor = i;
        // Encontra o menor elemento na parte não ordenada do array
        for (int j = i + 1; j < tamanho; j++) {
            if (vet[j] < vet[indiceMenor]) {
                indiceMenor = j;
            }
        }
        // Troca o menor elemento encontrado com o primeiro elemento não ordenado
        int temp = vet[i];
        vet[i] = vet[indiceMenor];
        vet[indiceMenor] = temp;
    }
}

// Insertion Sort: Algoritmo de ordenação por inserção
void insertionSort(int vet[], int tamanho) {
    for (int i = 1; i < tamanho; i++) {
        int chave = vet[i];
        int j = i - 1;
        // Move os elementos maiores que a chave para uma posição à frente
        while (j >= 0 && vet[j] > chave) {
            vet[j + 1] = vet[j];
            j--;
        }
        // Insere a chave na posição correta
        vet[j + 1] = chave;
    }
}

// Quick Sort: Algoritmo de ordenação rápida
void quickSort(int vet[], int esquerda, int direita) {
    int i = esquerda, j = direita;
    int pivo = vet[(esquerda + direita) / 2];

    // Particiona o array em elementos menores e maiores que o pivô
    while (i <= j) {
        while (vet[i] < pivo) i++;
        while (vet[j] > pivo) j--;
        if (i <= j) {
            // Troca os elementos que estão fora de ordem
            int temp = vet[i];
            vet[i] = vet[j];
            vet[j] = temp;
            i++;
            j--;
        }
    }

    // Recursivamente ordena as duas subpartes
    if (esquerda < j) quickSort(vet, esquerda, j);
    if (i < direita) quickSort(vet, i, direita);
}

// Função para medir o tempo de execução de um algoritmo de ordenação
double medirTempoOrdenacao(void (*funcaoOrdenacao)(int[], int), int vet[], int tamanho) {
    clock_t inicio = clock(); // Marca o início do tempo
    funcaoOrdenacao(vet, tamanho); // Executa o algoritmo de ordenação
    clock_t fim = clock(); // Marca o fim do tempo
    return double(fim - inicio) / CLOCKS_PER_SEC; // Retorna o tempo em segundos
}

// Função para verificar se o vetor está ordenado corretamente
bool estaOrdenado(int vet[], int tamanho) {
    // Verifica se cada elemento é menor ou igual ao próximo
    for (int i = 1; i < tamanho; i++) {
        if (vet[i] < vet[i - 1]) return false;
    }
    return true;
}

// Função para escrever o relatório no arquivo de saída
void escreverRelatorio(const char* nomeArquivoSaida, const char* nomeArquivoEntrada, const char* nomeAlgoritmo, double tempo, bool ordenadoCorretamente) {
    std::ofstream arquivo(nomeArquivoSaida, std::ios_base::app);  // Abre o arquivo no modo de anexar
    arquivo << "Arquivo de Entrada: " << nomeArquivoEntrada << "\n";
    arquivo << nomeAlgoritmo << " levou " << tempo << " segundos. Ordenado corretamente: " << (ordenadoCorretamente ? "Sim" : "Não") << "\n";
    arquivo.close();
}

// Função para adicionar um traço separador no arquivo de relatório
void traco(const char* nomeArquivoSaida) {
    std::ofstream arquivo(nomeArquivoSaida, std::ios_base::app);
    arquivo << "----------------------------------------------------" << "\n";
    arquivo.close();
}

// Função principal
int main() {
    // Definindo arrays estáticos para armazenar os dados e suas cópias
    int dados[TAMANHO];
    int copiaDados[TAMANHO];

    const char* arquivosEntrada[] = {
        "aleat_100000.txt",    // Arquivo 1 (aleatório)
        "cresc_100000.txt",    // Arquivo 2 (crescente)
        "decresc_100000.txt"   // Arquivo 3 (decrescente)
    };
    const char* nomeArquivoSaida = "resultados.txt"; // Nome do arquivo de saída

    // Para cada arquivo de entrada
    for (int arq = 0; arq < 3; arq++) {
        const char* nomeArquivo = arquivosEntrada[arq];
        std::cout << "Carregando dados do arquivo: " << nomeArquivo << "..." << std::endl;
        carregarDados(nomeArquivo, dados, TAMANHO); // Carrega os dados do arquivo para o array

        std::cout << "Iniciando testes de ordenação para o arquivo: " << nomeArquivo << "..." << std::endl;

        // Bubble Sort 1
        std::cout << "Executando Bubble Sort 1..." << std::endl;
        for (int i = 0; i < TAMANHO; i++) copiaDados[i] = dados[i]; // Copia os dados originais para um array temporário
        double tempoBubble1 = medirTempoOrdenacao(bubbleSort1, copiaDados, TAMANHO); // Mede o tempo de execução
        bool ordenadoBubble1 = estaOrdenado(copiaDados, TAMANHO); // Verifica se está ordenado corretamente
        escreverRelatorio(nomeArquivoSaida, nomeArquivo, "Bubble Sort 1", tempoBubble1, ordenadoBubble1);
        std::cout << "Bubble Sort 1 concluído." << std::endl;

        // Bubble Sort Melhorado
        std::cout << "Executando Bubble Sort Melhorado..." << std::endl;
        for (int i = 0; i < TAMANHO; i++) copiaDados[i] = dados[i];
        double tempoBubbleMelhorado = medirTempoOrdenacao(bubbleSortMelhorado, copiaDados, TAMANHO);
        bool ordenadoBubbleMelhorado = estaOrdenado(copiaDados, TAMANHO);
        escreverRelatorio(nomeArquivoSaida, nomeArquivo, "Bubble Sort Melhorado", tempoBubbleMelhorado, ordenadoBubbleMelhorado);
        std::cout << "Bubble Sort Melhorado concluído." << std::endl;

        // Selection Sort
        std::cout << "Executando Selection Sort..." << std::endl;
        for (int i = 0; i < TAMANHO; i++) copiaDados[i] = dados[i];
        double tempoSelection = medirTempoOrdenacao(selectionSort, copiaDados, TAMANHO);
        bool ordenadoSelection = estaOrdenado(copiaDados, TAMANHO);
        escreverRelatorio(nomeArquivoSaida, nomeArquivo, "Selection Sort", tempoSelection, ordenadoSelection);
        std::cout << "Selection Sort concluído." << std::endl;

        // Insertion Sort
        std::cout << "Executando Insertion Sort..." << std::endl;
        for (int i = 0; i < TAMANHO; i++) copiaDados[i] = dados[i];
        double tempoInsertion = medirTempoOrdenacao(insertionSort, copiaDados, TAMANHO);
        bool ordenadoInsertion = estaOrdenado(copiaDados, TAMANHO);
        escreverRelatorio(nomeArquivoSaida, nomeArquivo, "Insertion Sort", tempoInsertion, ordenadoInsertion);
        std::cout << "Insertion Sort concluído." << std::endl;

        // Quick Sort
        std::cout << "Executando Quick Sort..." << std::endl;
        for (int i = 0; i < TAMANHO; i++) copiaDados[i] = dados[i];
        double tempoQuick = medirTempoOrdenacao([](int vet[], int tam){ quickSort(vet, 0, tam - 1); }, copiaDados, TAMANHO);
        bool ordenadoQuick = estaOrdenado(copiaDados, TAMANHO);
        escreverRelatorio(nomeArquivoSaida, nomeArquivo, "Quick Sort", tempoQuick, ordenadoQuick);
        std::cout << "Quick Sort concluído." << std::endl;

        // Adiciona um traço para separar os relatórios de diferentes arquivos
        traco(nomeArquivoSaida);
    }

    std::cout << "Todos os testes de ordenação foram concluídos. Resultados armazenados em '" << nomeArquivoSaida << "'." << std::endl;

    return 0;
}
