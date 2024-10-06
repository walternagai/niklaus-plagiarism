#include <iostream>
#include <fstream>
#include <ctime>

/*
 * Projeto: An�lise de Algoritmos de Ordena��o
 * Integrantes: Arthur Wellington Coelho Santana, Keila Silva Costa, Elioenay Jaiane Dias Gon�alves
 * Data de Submiss�o: 17/09/2024
 * Descri��o: Este programa implementa cinco algoritmos de ordena��o (Bubble Sort, Bubble Sort Melhorado,
 * Selection Sort, Insertion Sort e Quick Sort) e analisa o desempenho de cada um em termos de tempo de execu��o.
 * O programa l� dados de tr�s arquivos de entrada, aplica cada algoritmo de ordena��o aos dados, mede o tempo
 * de execu��o, verifica a corre��o da ordena��o e gera um relat�rio de resultados em um arquivo de sa�da.
 */

const int TAMANHO = 100000; // Define o tamanho fixo para os arrays

// Fun��o para carregar os dados do arquivo para a mem�ria
void carregarDados(const char* nomeArquivo, int vet[], int tamanho) {
    std::ifstream arquivo(nomeArquivo);
    // L� cada n�mero do arquivo e armazena no array vet
    for (int i = 0; i < tamanho; i++) {
        arquivo >> vet[i];
    }
    arquivo.close();
}

// Bubble Sort (Vers�o 1): Algoritmo de ordena��o por bolha
void bubbleSort1(int vet[], int tamanho) {
    for (int i = 0; i < tamanho; i++) {
        for (int j = 0; j < tamanho - 1; j++) {
            // Se o elemento atual � maior que o pr�ximo, faz a troca
            if (vet[j] > vet[j + 1]) {
                int temp = vet[j];
                vet[j] = vet[j + 1];
                vet[j + 1] = temp;
            }
        }
    }
}

// Bubble Sort Melhorado (Vers�o 3): Algoritmo de ordena��o por bolha com otimiza��o
void bubbleSortMelhorado(int vet[], int tamanho) {
    bool trocou;
    for (int i = 0; i < tamanho - 1; i++) {
        trocou = false;
        for (int j = 0; j < tamanho - i - 1; j++) {
            // Se o elemento atual � maior que o pr�ximo, faz a troca
            if (vet[j] > vet[j + 1]) {
                int temp = vet[j];
                vet[j] = vet[j + 1];
                vet[j + 1] = temp;
                trocou = true; // Marca que houve troca
            }
        }
        // Se nenhuma troca foi feita na �ltima passada, o array est� ordenado
        if (!trocou) break;
    }
}

// Selection Sort: Algoritmo de ordena��o por sele��o
void selectionSort(int vet[], int tamanho) {
    for (int i = 0; i < tamanho - 1; i++) {
        int indiceMenor = i;
        // Encontra o menor elemento na parte n�o ordenada do array
        for (int j = i + 1; j < tamanho; j++) {
            if (vet[j] < vet[indiceMenor]) {
                indiceMenor = j;
            }
        }
        // Troca o menor elemento encontrado com o primeiro elemento n�o ordenado
        int temp = vet[i];
        vet[i] = vet[indiceMenor];
        vet[indiceMenor] = temp;
    }
}

// Insertion Sort: Algoritmo de ordena��o por inser��o
void insertionSort(int vet[], int tamanho) {
    for (int i = 1; i < tamanho; i++) {
        int chave = vet[i];
        int j = i - 1;
        // Move os elementos maiores que a chave para uma posi��o � frente
        while (j >= 0 && vet[j] > chave) {
            vet[j + 1] = vet[j];
            j--;
        }
        // Insere a chave na posi��o correta
        vet[j + 1] = chave;
    }
}

// Quick Sort: Algoritmo de ordena��o r�pida
void quickSort(int vet[], int esquerda, int direita) {
    int i = esquerda, j = direita;
    int pivo = vet[(esquerda + direita) / 2];

    // Particiona o array em elementos menores e maiores que o piv�
    while (i <= j) {
        while (vet[i] < pivo) i++;
        while (vet[j] > pivo) j--;
        if (i <= j) {
            // Troca os elementos que est�o fora de ordem
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

// Fun��o para medir o tempo de execu��o de um algoritmo de ordena��o
double medirTempoOrdenacao(void (*funcaoOrdenacao)(int[], int), int vet[], int tamanho) {
    clock_t inicio = clock(); // Marca o in�cio do tempo
    funcaoOrdenacao(vet, tamanho); // Executa o algoritmo de ordena��o
    clock_t fim = clock(); // Marca o fim do tempo
    return double(fim - inicio) / CLOCKS_PER_SEC; // Retorna o tempo em segundos
}

// Fun��o para verificar se o vetor est� ordenado corretamente
bool estaOrdenado(int vet[], int tamanho) {
    // Verifica se cada elemento � menor ou igual ao pr�ximo
    for (int i = 1; i < tamanho; i++) {
        if (vet[i] < vet[i - 1]) return false;
    }
    return true;
}

// Fun��o para escrever o relat�rio no arquivo de sa�da
void escreverRelatorio(const char* nomeArquivoSaida, const char* nomeArquivoEntrada, const char* nomeAlgoritmo, double tempo, bool ordenadoCorretamente) {
    std::ofstream arquivo(nomeArquivoSaida, std::ios_base::app);  // Abre o arquivo no modo de anexar
    arquivo << "Arquivo de Entrada: " << nomeArquivoEntrada << "\n";
    arquivo << nomeAlgoritmo << " levou " << tempo << " segundos. Ordenado corretamente: " << (ordenadoCorretamente ? "Sim" : "N�o") << "\n";
    arquivo.close();
}

// Fun��o para adicionar um tra�o separador no arquivo de relat�rio
void traco(const char* nomeArquivoSaida) {
    std::ofstream arquivo(nomeArquivoSaida, std::ios_base::app);
    arquivo << "----------------------------------------------------" << "\n";
    arquivo.close();
}

// Fun��o principal
int main() {
    // Definindo arrays est�ticos para armazenar os dados e suas c�pias
    int dados[TAMANHO];
    int copiaDados[TAMANHO];

    const char* arquivosEntrada[] = {
        "aleat_100000.txt",    // Arquivo 1 (aleat�rio)
        "cresc_100000.txt",    // Arquivo 2 (crescente)
        "decresc_100000.txt"   // Arquivo 3 (decrescente)
    };
    const char* nomeArquivoSaida = "resultados.txt"; // Nome do arquivo de sa�da

    // Para cada arquivo de entrada
    for (int arq = 0; arq < 3; arq++) {
        const char* nomeArquivo = arquivosEntrada[arq];
        std::cout << "Carregando dados do arquivo: " << nomeArquivo << "..." << std::endl;
        carregarDados(nomeArquivo, dados, TAMANHO); // Carrega os dados do arquivo para o array

        std::cout << "Iniciando testes de ordena��o para o arquivo: " << nomeArquivo << "..." << std::endl;

        // Bubble Sort 1
        std::cout << "Executando Bubble Sort 1..." << std::endl;
        for (int i = 0; i < TAMANHO; i++) copiaDados[i] = dados[i]; // Copia os dados originais para um array tempor�rio
        double tempoBubble1 = medirTempoOrdenacao(bubbleSort1, copiaDados, TAMANHO); // Mede o tempo de execu��o
        bool ordenadoBubble1 = estaOrdenado(copiaDados, TAMANHO); // Verifica se est� ordenado corretamente
        escreverRelatorio(nomeArquivoSaida, nomeArquivo, "Bubble Sort 1", tempoBubble1, ordenadoBubble1);
        std::cout << "Bubble Sort 1 conclu�do." << std::endl;

        // Bubble Sort Melhorado
        std::cout << "Executando Bubble Sort Melhorado..." << std::endl;
        for (int i = 0; i < TAMANHO; i++) copiaDados[i] = dados[i];
        double tempoBubbleMelhorado = medirTempoOrdenacao(bubbleSortMelhorado, copiaDados, TAMANHO);
        bool ordenadoBubbleMelhorado = estaOrdenado(copiaDados, TAMANHO);
        escreverRelatorio(nomeArquivoSaida, nomeArquivo, "Bubble Sort Melhorado", tempoBubbleMelhorado, ordenadoBubbleMelhorado);
        std::cout << "Bubble Sort Melhorado conclu�do." << std::endl;

        // Selection Sort
        std::cout << "Executando Selection Sort..." << std::endl;
        for (int i = 0; i < TAMANHO; i++) copiaDados[i] = dados[i];
        double tempoSelection = medirTempoOrdenacao(selectionSort, copiaDados, TAMANHO);
        bool ordenadoSelection = estaOrdenado(copiaDados, TAMANHO);
        escreverRelatorio(nomeArquivoSaida, nomeArquivo, "Selection Sort", tempoSelection, ordenadoSelection);
        std::cout << "Selection Sort conclu�do." << std::endl;

        // Insertion Sort
        std::cout << "Executando Insertion Sort..." << std::endl;
        for (int i = 0; i < TAMANHO; i++) copiaDados[i] = dados[i];
        double tempoInsertion = medirTempoOrdenacao(insertionSort, copiaDados, TAMANHO);
        bool ordenadoInsertion = estaOrdenado(copiaDados, TAMANHO);
        escreverRelatorio(nomeArquivoSaida, nomeArquivo, "Insertion Sort", tempoInsertion, ordenadoInsertion);
        std::cout << "Insertion Sort conclu�do." << std::endl;

        // Quick Sort
        std::cout << "Executando Quick Sort..." << std::endl;
        for (int i = 0; i < TAMANHO; i++) copiaDados[i] = dados[i];
        double tempoQuick = medirTempoOrdenacao([](int vet[], int tam){ quickSort(vet, 0, tam - 1); }, copiaDados, TAMANHO);
        bool ordenadoQuick = estaOrdenado(copiaDados, TAMANHO);
        escreverRelatorio(nomeArquivoSaida, nomeArquivo, "Quick Sort", tempoQuick, ordenadoQuick);
        std::cout << "Quick Sort conclu�do." << std::endl;

        // Adiciona um tra�o para separar os relat�rios de diferentes arquivos
        traco(nomeArquivoSaida);
    }

    std::cout << "Todos os testes de ordena��o foram conclu�dos. Resultados armazenados em '" << nomeArquivoSaida << "'." << std::endl;

    return 0;
}
