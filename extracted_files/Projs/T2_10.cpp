#include <iostream>
#include <fstream>
#include <ctime>  // Para medir o tempo de execução
#include <string>
#include <tchar.h>

using namespace std;

// Função Bubble Sort (versão simples)
void bubbleSort(int arr[], int n) {
    for (int i = 0; i < n-1; i++) {
        for (int j = 0; j < n-i-1; j++) {
            if (arr[j] > arr[j+1]) {
                swap(arr[j], arr[j+1]);
            }
        }
    }
}

// Função Bubble Sort Melhorado
void bubbleSortMelhorado(int arr[], int n) {
    bool trocado;
    for (int i = 0; i < n-1; i++) {
        trocado = false;
        for (int j = 0; j < n-i-1; j++) {
            if (arr[j] > arr[j+1]) {
                swap(arr[j], arr[j+1]);
                trocado = true;
            }
        }
        if (!trocado)
            break; // Se não houve troca, o array já está ordenado
    }
}

// Função Selection Sort
void selectionSort(int arr[], int n) {
    for (int i = 0; i < n-1; i++) {
        int minIndex = i;
        for (int j = i+1; j < n; j++) {
            if (arr[j] < arr[minIndex]) {
                minIndex = j;
            }
        }
        swap(arr[minIndex], arr[i]);
    }
}

// Função Insertion Sort
void insertionSort(int arr[], int n) {
    for (int i = 1; i < n; i++) {
        int key = arr[i];
        int j = i - 1;
        while (j >= 0 && arr[j] > key) {
            arr[j+1] = arr[j];
            j = j - 1;
        }
        arr[j+1] = key;
    }
}

// Função Quick Sort
int partition(int arr[], int low, int high) {
    int pivot = arr[high];
    int i = (low - 1);
    for (int j = low; j <= high - 1; j++) {
        if (arr[j] < pivot) {
            i++;
            swap(arr[i], arr[j]);
        }
    }
    swap(arr[i + 1], arr[high]);
    return (i + 1);
}

void quickSort(int arr[], int low, int high) {
    if (low < high) {
        int pi = partition(arr, low, high);
        quickSort(arr, low, pi - 1);
        quickSort(arr, pi + 1, high);
    }
}

// Função para carregar dados do arquivo
void carregarDados(const string& nomeArquivo, int arr[], int n) {
    ifstream arquivo(nomeArquivo);
    if (!arquivo.is_open()) {
        cerr << "Erro ao abrir o arquivo " << nomeArquivo << endl;
        exit(1);
    }

    for (int i = 0; i < n; i++) {
        arquivo >> arr[i];
    }
    arquivo.close();
}

// Função para verificar se o array está ordenado
bool verificarOrdenacao(int arr[], int n) {
    for (int i = 0; i < n-1; i++) {
        if (arr[i] > arr[i+1]) {
            return false;
        }
    }
    return true;
}

// Função para medir o tempo e executar a ordenação
void executarAlgoritmo(void (*algoritmo)(int[], int), int arr[], int n, const string& nomeAlgoritmo, ofstream& resultados) {
    clock_t inicio = clock();
    algoritmo(arr, n);
    clock_t fim = clock();
    double tempo = double(fim - inicio) / CLOCKS_PER_SEC;

    resultados << "Algoritmo: " << nomeAlgoritmo << ", Tempo: " << tempo << " segundos." << endl;
    cout << nomeAlgoritmo << " concluído em " << tempo << " segundos." << endl;

    if (verificarOrdenacao(arr, n)) {
        resultados << nomeAlgoritmo << ": Ordenação correta." << endl;
    } else {
        resultados << nomeAlgoritmo << ": Erro na ordenação." << endl;
    }
}

int main() {

    _tsetlocale(LC_ALL,_T("portuguese"));
    const int n = 100000;  // Tamanho dos arrays
    int arr[n];

    // Arquivos de saída para os resultados
    ofstream resultados("resultados.txt");

    if (!resultados.is_open()) {
        cerr << "Erro ao criar o arquivo de resultados." << endl;
        return 1;
    }

    string arquivosEntrada[] = {"../aleat_100000.txt", "../cresc_100000.txt", "../decresc_100000.txt"};

    for (const string& arquivo : arquivosEntrada) {
        resultados << "Resultados para o arquivo: " << arquivo << endl;
        cout << "Executando algoritmos para o arquivo " << arquivo << endl;

        carregarDados(arquivo, arr, n);

        // Bubble Sort (Simples)
        executarAlgoritmo(bubbleSort, arr, n, "Bubble Sort Simples", resultados);

        carregarDados(arquivo, arr, n);
        // Bubble Sort Melhorado
        executarAlgoritmo(bubbleSortMelhorado, arr, n, "Bubble Sort Melhorado", resultados);

        carregarDados(arquivo, arr, n);
        // Selection Sort
        executarAlgoritmo(selectionSort, arr, n, "Selection Sort", resultados);

        carregarDados(arquivo, arr, n);
        // Insertion Sort
        executarAlgoritmo(insertionSort, arr, n, "Insertion Sort", resultados);

        carregarDados(arquivo, arr, n);
        // Quick Sort
        executarAlgoritmo([](int arr[], int n) { quickSort(arr, 0, n-1); }, arr, n, "Quick Sort", resultados);

        resultados << "-----------------------------------" << endl;
    }

    resultados.close();
    return 0;
}

