#include <iostream>
#include <locale.h>
#include <fstream>
#include <ctime>
#include <cstdlib> // para a função exit()

using namespace std;

/** INTEGRANTES DO GRUPO:
 * Anna Clara Cardoso Martins
 * Lucas Campos Silva
 * Tiago Andrade Marques
 */

// Funções dos algoritmos de ordenação
void bubbleSort(int arr[], int n);
void bubbleSortMelhorado(int arr[], int n);
void selectionSort(int arr[], int n);
void insertionSort(int arr[], int n);
void quickSort(int arr[], int low, int high);

// Funções auxiliares
void carregarDados(const string &nomeArquivo, int arr[], int n);
bool verificarOrdenacao(int arr[], int n);
void medirTempoExecucao(void (*func)(int[], int), int arr[], int n, const string &nomeAlgoritmo, ofstream &arquivo);
void medirTempoExecucao(void (*func)(int[], int, int), int arr[], int low, int high, const string &nomeAlgoritmo, ofstream &arquivo);

// Função para copiar arrays
void copiarArray(const int src[], int dest[], int n)
{
    for (int i = 0; i < n; i++) {
        dest[i] = src[i];
    }
}

int main()
{
    setlocale(LC_ALL, "Portuguese");
    const int tamanho = 100000;
    int aleatorio[tamanho], crescente[tamanho], decrescente[tamanho];

    // Carregar os dados dos arquivos
    carregarDados("aleat_100000.txt", aleatorio, tamanho);
    carregarDados("cresc_100000.txt", crescente, tamanho);
    carregarDados("decresc_100000.txt", decrescente, tamanho);

    // Abrir arquivo para gravar resultados
    ofstream arquivoResultados("resultados.txt", ios::app);
    if (!arquivoResultados)
    {
        cerr << "Erro ao abrir o arquivo resultados.txt" << endl;
        return 1;
    }

    // Testar todas as funções de ordenação com todos os tipos de dados
    void (*algoritmosSemParametros[])(int[], int) = {bubbleSort, bubbleSortMelhorado, selectionSort, insertionSort};
    string nomesAlgoritmos[] = {"Bubble Sort", "Bubble Sort Melhorado", "Selection Sort", "Insertion Sort"};

    for (int i = 0; i < 4; ++i)
    {
        for (int tipo = 0; tipo < 3; ++tipo)
        {
            const int* arrayOriginal;
            string tipoNome;

            switch (tipo)
            {
            case 0:
                arrayOriginal = aleatorio;
                tipoNome = "Aleatório";
                break;
            case 1:
                arrayOriginal = crescente;
                tipoNome = "Crescente";
                break;
            case 2:
                arrayOriginal = decrescente;
                tipoNome = "Decrescente";
                break;
            }

            int arrayCopia[tamanho];
            copiarArray(arrayOriginal, arrayCopia, tamanho);

            // Registrar execução no arquivo
            arquivoResultados << "\n"
                              << nomesAlgoritmos[i] << " com dados " << tipoNome << ":\n";
            medirTempoExecucao(algoritmosSemParametros[i], arrayCopia, tamanho, nomesAlgoritmos[i], arquivoResultados);
        }
    }

    // Medir o tempo do Quick Sort
    string nomeQuickSort = "Quick Sort";

    for (int tipo = 0; tipo < 3; ++tipo)
    {
        const int* arrayOriginal;
        string tipoNome;

        switch (tipo)
        {
        case 0:
            arrayOriginal = aleatorio;
            tipoNome = "Aleatório";
            break;
        case 1:
            arrayOriginal = crescente;
            tipoNome = "Crescente";
            break;
        case 2:
            arrayOriginal = decrescente;
            tipoNome = "Decrescente";
            break;
        }

        int arrayCopia[tamanho];
        copiarArray(arrayOriginal, arrayCopia, tamanho);

        // Registrar execução no arquivo
        arquivoResultados << "\n"
                          << nomeQuickSort << " com dados " << tipoNome << ":\n";
        medirTempoExecucao(quickSort, arrayCopia, 0, tamanho - 1, nomeQuickSort, arquivoResultados);
    }

    return 0;
}

// Implementação das funções de ordenação
void bubbleSort(int arr[], int n)
{
    for (int i = 1; i < n; i++)
    {
        for (int j = 0; j < n - 1; j++)
        {
            if (arr[j] > arr[j + 1])
            {
                int aux = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = aux;
            }
        }
    }
}

void bubbleSortMelhorado(int arr[], int n)
{
    bool troca = true;
    for (int i = 1; i < n && troca; i++)
    {
        troca = false;
        for (int j = 0; j < n - i; j++)
        {
            if (arr[j] > arr[j + 1])
            {
                troca = true;
                int aux = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = aux;
            }
        }
    }
}

void selectionSort(int arr[], int n)
{
    for (int i = 0; i < n - 1; i++)
    {
        int i_menor = i;
        for (int j = i + 1; j < n; j++)
        {
            if (arr[j] < arr[i_menor])
                i_menor = j;
        }
        int aux = arr[i];
        arr[i] = arr[i_menor];
        arr[i_menor] = aux;
    }
}

void insertionSort(int arr[], int n)
{
    for (int i = 1; i < n; i++)
    {
        int aux = arr[i];
        int j = i;
        while (j > 0 && arr[j - 1] > aux)
        {
            arr[j] = arr[j - 1];
            j--;
        }
        arr[j] = aux;
    }
}

void quickSort(int arr[], int left, int right)
{
    int pivot = arr[(left + right) / 2];
    int i = left;
    int j = right;

    do
    {
        while (arr[i] < pivot)
            i++;
        while (arr[j] > pivot)
            j--;
        if (i <= j)
        {
            int aux = arr[i];
            arr[i] = arr[j];
            arr[j] = aux;
            i++;
            j--;
        }
    } while (i <= j);

    if (left < j)
        quickSort(arr, left, j);
    if (i < right)
        quickSort(arr, i, right);
}

// Função para carregar os dados do arquivo
void carregarDados(const string &nomeArquivo, int arr[], int n)
{
    ifstream file(nomeArquivo);
    if (!file)
    {
        cerr << "Erro ao abrir o arquivo: " << nomeArquivo << endl;
        exit(1);
    }
    for (int i = 0; i < n; i++)
    {
        file >> arr[i];
    }
    file.close();
}

// Função para verificar se o array está ordenado
bool verificarOrdenacao(int arr[], int n)
{
    for (int i = 1; i < n; i++)
    {
        if (arr[i - 1] > arr[i])
        {
            return false;
        }
    }
    return true;
}

// Função para medir o tempo de execução (para algoritmos com dois parâmetros)
void medirTempoExecucao(void (*func)(int[], int), int arr[], int n, const string &nomeAlgoritmo, ofstream &arquivo)
{
    int arrayCopia[n];
    copiarArray(arr, arrayCopia, n);

    clock_t start = clock();
    func(arrayCopia, n);
    clock_t end = clock();

    double tempo = double(end - start) / CLOCKS_PER_SEC;
    cout << nomeAlgoritmo << ": " << tempo << " segundos" << endl;
    arquivo << nomeAlgoritmo << ": " << tempo << " segundos" << endl;

    if (verificarOrdenacao(arrayCopia, n))
    {
        cout << "Ordenação correta!" << endl;
        arquivo << "Ordenação correta!" << endl;
    }
    else
    {
        cout << "Erro na ordenação!" << endl;
        arquivo << "Erro na ordenação!" << endl;
    }
}

// Função para medir o tempo de execução (para algoritmos com três parâmetros)
void medirTempoExecucao(void (*func)(int[], int, int), int arr[], int low, int high, const string &nomeAlgoritmo, ofstream &arquivo)
{
    int arrayCopia[high + 1];
    copiarArray(arr, arrayCopia, high + 1);

    clock_t start = clock();
    func(arrayCopia, low, high);
    clock_t end = clock();

    double tempo = double(end - start) / CLOCKS_PER_SEC;
    cout << nomeAlgoritmo << ": " << tempo << " segundos" << endl;
    arquivo << nomeAlgoritmo << ": " << tempo << " segundos" << endl;

    if (verificarOrdenacao(arrayCopia, high + 1))
    {
        cout << "Ordenação correta!" << endl;
        arquivo << "Ordenação correta!" << endl;
    }
    else
    {
        cout << "Erro na ordenação!" << endl;
        arquivo << "Erro na ordenação!" << endl;
    }
}
