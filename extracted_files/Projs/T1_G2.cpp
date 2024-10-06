/*Universidade Federal de Itajubá-Campus Itabira
Integrantes: Saymara Gonçalves Souza,Alessandra Meireles Teixeira, Ana Paulla Mota
Professora: Claudia Izeki- Algoritmos e Estruturas de Dados I
Data:17/09/2024
Descrição:
Este programa implementa e avalia cinco métodos de ordenação (Bubble Sort, Bubble Sort melhorado,
Selection Sort, Insertion Sort e Quick Sort) sobre três conjuntos de dados com 100.000 números.
O objetivo é medir o desempenho de cada algoritmo e validar a precisão da ordenação, registrando
os resultados em arquivos de saída.
*/


#include <iostream>
#include <fstream>
#include <cstdlib>  // Para std::atoi
#include <ctime>    // Para std::clock

// Função para carregar dados de um arquivo para um vetor
void carregarDados(const char* nomeArquivo, int vet[], int& n) {
    std::ifstream fim(nomeArquivo);
    if (fim.is_open()) {
        n = 0;
        // Lê os números do arquivo e armazena no vetor até o tamanho máximo
        while (fim >> vet[n] && n < 100000) {
            n++;
        }
        fim.close();
    } else {
        std::cerr << "Erro ao abrir o arquivo: " << nomeArquivo << std::endl;
    }
}

// Função para verificar se o vetor está ordenado
bool estaOrdenado(int arr[], int n) {
    for (int i = 1; i < n; i++) {
        if (arr[i] < arr[i - 1]) {
            return false;
        }
    }
    return true;
}

// Implementação do Bubble Sort
void bubbleSort(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

// Implementação do Bubble Sort Melhorado
void bubbleSortMelhorado(int arr[], int n, int& trocas) {
    bool trocou;
    trocas = 0;
    for (int i = 0; i < n - 1; i++) {
        trocou = false;
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
                trocas++;
                trocou = true;
            }
        }
        if (!trocou) break;
    }
}

// Implementação do Selection Sort
void selectionSort(int v[], int n, int& comparacoes) {
    comparacoes = 0;
    for (int i = 0; i < n - 1; i++) {
        int i_menor = i;
        for (int j = i + 1; j < n; j++) {
            comparacoes++; // Incrementa a contagem de comparações
            if (v[j] < v[i_menor]) {
                i_menor = j;
            }
        }
        int aux = v[i];
        v[i] = v[i_menor];
        v[i_menor] = aux;
    }
}

// Implementação do Insertion Sort
void insertionSort(int arr[], int n, int& comparacoes) {
    comparacoes = 0;
    for (int i = 1; i < n; i++) {
        int aux = arr[i];
        int j = i - 1;
        while (j >= 0 && arr[j] > aux) {
            arr[j + 1] = arr[j];
            j--;
            comparacoes++;// Incrementa a contagem de comparações
        }
        arr[j + 1] = aux;
        if (j >= 0) comparacoes++;
    }
}

// Implementação do Quick Sort
void quickSort(int v[], int left, int right) {
    int i = left;
    int j = right;
    int pivo = v[(left + right) / 2];
    do {
        while (v[i] < pivo) i++;
        while (v[j] > pivo) j--;
        if (i <= j) {
            int aux = v[i];
            v[i] = v[j];
            v[j] = aux;
            i++;
            j--;
        }
    } while (i <= j);
    if (left < j) quickSort(v, left, j);
    if (i < right) quickSort(v, i, right);
}

// Função para salvar os dados ordenados e informações no arquivo
void salvarResultado(const char* nomeArquivo, const char* algoritmo, double tempo, int adicionalInfo, bool sucesso) {
    std::ofstream fout(nomeArquivo, std::ios::app); // Modo de acréscimo
    if (fout.is_open()) {
        fout << algoritmo << ":\n";
        fout << "Tempo de execução: " << tempo << " segundos\n";
        fout << "Informação adicional: " << adicionalInfo << "\n";
        fout << (sucesso ? "Ordenação correta.\n\n" : "Erro: os dados não foram ordenados corretamente.\n\n");
        fout.close();
    } else {
        std::cerr << "Erro ao salvar os dados no arquivo: " << nomeArquivo << std::endl;
    }
}

// Função wrapper para testar o algoritmo
void testarAlgoritmo(const char* arquivoEntrada, const char* algoritmo, void (*funcaoOrdenacao)(int[], int, int&), const char* arquivoResultado, bool usaQuickSort = false) {
    int vet[100000];
    int n = 0;
    int adicionalInfo = 0;

    carregarDados(arquivoEntrada, vet, n);

    std::clock_t start = std::clock(); // Inicia o cronômetro
    if (usaQuickSort) {
        quickSort(vet, 0, n - 1);
    } else {
        funcaoOrdenacao(vet, n, adicionalInfo);
    }
    std::clock_t end = std::clock(); // Termina o cronômetro

    double tempo = static_cast<double>(end - start) / CLOCKS_PER_SEC;

    bool sucesso = estaOrdenado(vet, n);

    // Mensagens no console
    if (sucesso) {
        std::cout << algoritmo << " ordenou corretamente.\n";
        std::cout << "Tempo de execução: " << tempo << " segundos\n";
        std::cout << "Informação adicional: " << adicionalInfo << std::endl;
    } else {
        std::cerr << "Erro: os dados não foram ordenados corretamente com o " << algoritmo << std::endl;
    }

    // Mensagens no arquivo
    salvarResultado(arquivoResultado, algoritmo, tempo, adicionalInfo, sucesso);
}

int main() {
    // Nome dos arquivos de entrada
    const char* arquivosEntrada[] = {"aleat_100000.txt", "cresc_100000.txt", "decresc_100000.txt"};
    const char* nomesAlgoritmos[] = {"Bubble Sort", "Bubble Sort Melhorado", "Selection Sort", "Insertion Sort", "Quick Sort"};

    // Nome do arquivo de resultado
    const char* arquivoResultado = "resultados.txt";

    for (int i = 0; i < 3; i++) {
        const char* arquivoEntrada = arquivosEntrada[i];

        std::cout << "Executando algoritmos para o arquivo " << arquivoEntrada << "...\n";

        // Testar os algoritmos para o arquivo atual
        std::cout << "Executando Bubble Sort...\n";
        testarAlgoritmo(arquivoEntrada, nomesAlgoritmos[0], [](int arr[], int n, int& info){ bubbleSort(arr, n); }, arquivoResultado);

        std::cout << "\nExecutando Bubble Sort Melhorado...\n";
        testarAlgoritmo(arquivoEntrada, nomesAlgoritmos[1], [](int arr[], int n, int& info){ bubbleSortMelhorado(arr, n, info); }, arquivoResultado);

        std::cout << "\nExecutando Selection Sort...\n";
        testarAlgoritmo(arquivoEntrada, nomesAlgoritmos[2], [](int arr[], int n, int& info){ selectionSort(arr, n, info); }, arquivoResultado);

        std::cout << "\nExecutando Insertion Sort...\n";
        testarAlgoritmo(arquivoEntrada, nomesAlgoritmos[3], [](int arr[], int n, int& info){ insertionSort(arr, n, info); }, arquivoResultado);

        std::cout << "\nExecutando Quick Sort...\n";
        testarAlgoritmo(arquivoEntrada, nomesAlgoritmos[4], nullptr, arquivoResultado, true);
    }

    return 0;
}
