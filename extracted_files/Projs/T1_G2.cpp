/*Universidade Federal de Itajub�-Campus Itabira
Integrantes: Saymara Gon�alves Souza,Alessandra Meireles Teixeira, Ana Paulla Mota
Professora: Claudia Izeki- Algoritmos e Estruturas de Dados I
Data:17/09/2024
Descri��o:
Este programa implementa e avalia cinco m�todos de ordena��o (Bubble Sort, Bubble Sort melhorado,
Selection Sort, Insertion Sort e Quick Sort) sobre tr�s conjuntos de dados com 100.000 n�meros.
O objetivo � medir o desempenho de cada algoritmo e validar a precis�o da ordena��o, registrando
os resultados em arquivos de sa�da.
*/


#include <iostream>
#include <fstream>
#include <cstdlib>  // Para std::atoi
#include <ctime>    // Para std::clock

// Fun��o para carregar dados de um arquivo para um vetor
void carregarDados(const char* nomeArquivo, int vet[], int& n) {
    std::ifstream fim(nomeArquivo);
    if (fim.is_open()) {
        n = 0;
        // L� os n�meros do arquivo e armazena no vetor at� o tamanho m�ximo
        while (fim >> vet[n] && n < 100000) {
            n++;
        }
        fim.close();
    } else {
        std::cerr << "Erro ao abrir o arquivo: " << nomeArquivo << std::endl;
    }
}

// Fun��o para verificar se o vetor est� ordenado
bool estaOrdenado(int arr[], int n) {
    for (int i = 1; i < n; i++) {
        if (arr[i] < arr[i - 1]) {
            return false;
        }
    }
    return true;
}

// Implementa��o do Bubble Sort
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

// Implementa��o do Bubble Sort Melhorado
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

// Implementa��o do Selection Sort
void selectionSort(int v[], int n, int& comparacoes) {
    comparacoes = 0;
    for (int i = 0; i < n - 1; i++) {
        int i_menor = i;
        for (int j = i + 1; j < n; j++) {
            comparacoes++; // Incrementa a contagem de compara��es
            if (v[j] < v[i_menor]) {
                i_menor = j;
            }
        }
        int aux = v[i];
        v[i] = v[i_menor];
        v[i_menor] = aux;
    }
}

// Implementa��o do Insertion Sort
void insertionSort(int arr[], int n, int& comparacoes) {
    comparacoes = 0;
    for (int i = 1; i < n; i++) {
        int aux = arr[i];
        int j = i - 1;
        while (j >= 0 && arr[j] > aux) {
            arr[j + 1] = arr[j];
            j--;
            comparacoes++;// Incrementa a contagem de compara��es
        }
        arr[j + 1] = aux;
        if (j >= 0) comparacoes++;
    }
}

// Implementa��o do Quick Sort
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

// Fun��o para salvar os dados ordenados e informa��es no arquivo
void salvarResultado(const char* nomeArquivo, const char* algoritmo, double tempo, int adicionalInfo, bool sucesso) {
    std::ofstream fout(nomeArquivo, std::ios::app); // Modo de acr�scimo
    if (fout.is_open()) {
        fout << algoritmo << ":\n";
        fout << "Tempo de execu��o: " << tempo << " segundos\n";
        fout << "Informa��o adicional: " << adicionalInfo << "\n";
        fout << (sucesso ? "Ordena��o correta.\n\n" : "Erro: os dados n�o foram ordenados corretamente.\n\n");
        fout.close();
    } else {
        std::cerr << "Erro ao salvar os dados no arquivo: " << nomeArquivo << std::endl;
    }
}

// Fun��o wrapper para testar o algoritmo
void testarAlgoritmo(const char* arquivoEntrada, const char* algoritmo, void (*funcaoOrdenacao)(int[], int, int&), const char* arquivoResultado, bool usaQuickSort = false) {
    int vet[100000];
    int n = 0;
    int adicionalInfo = 0;

    carregarDados(arquivoEntrada, vet, n);

    std::clock_t start = std::clock(); // Inicia o cron�metro
    if (usaQuickSort) {
        quickSort(vet, 0, n - 1);
    } else {
        funcaoOrdenacao(vet, n, adicionalInfo);
    }
    std::clock_t end = std::clock(); // Termina o cron�metro

    double tempo = static_cast<double>(end - start) / CLOCKS_PER_SEC;

    bool sucesso = estaOrdenado(vet, n);

    // Mensagens no console
    if (sucesso) {
        std::cout << algoritmo << " ordenou corretamente.\n";
        std::cout << "Tempo de execu��o: " << tempo << " segundos\n";
        std::cout << "Informa��o adicional: " << adicionalInfo << std::endl;
    } else {
        std::cerr << "Erro: os dados n�o foram ordenados corretamente com o " << algoritmo << std::endl;
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
