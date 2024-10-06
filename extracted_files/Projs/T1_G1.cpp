/*  
    Nome dos Integrantes:
    Aderson Ferreira Cassimiro de Oliveira
    Davi Amaro Amaral
    Vinicius Gabriel Pereira Rosa

    Data de Submissão: 14/09/2024

    Introdução: Este código tem como objetivo analisar o 
    desempenho e a eficácia de cinco algoritmos de ordenação: Bubble Sort v1, Bubble 
    Sort v3, Selection Sort, Insertion Sort e Quick Sort. A análise considera a 
    complexidade de tempo de cada algoritmo em diferentes cenários, como o pior 
    caso, caso médio e melhor caso, além de discutir suas vantagens e limitações 
    práticas. 
*/

#include<iostream>
#include<fstream>
#include<ctime>
#include<iomanip>
#include<sstream>
#include<windows.h>

using namespace std;

// Função para carregar os números do arquivo no array
void carregarDados(const char* nomeArquivo, int arr[])
{    
    int TAM = 100000;
    
    ifstream arquivo(nomeArquivo);
    if (!arquivo) 
    {
        cerr << "Erro ao abrir o arquivo " << nomeArquivo << endl;
        exit(1);
    }
    for (int i = 0; i < TAM; i++) 
    {
        arquivo >> arr[i];
    }
    arquivo.close();
}


// Implementação do Bubble Sort (V1)
void bubbleSort(int arr[], int n)
{
    int aux;
    for (int i = 1; i < n; i++)
    {
        for (int j = 0; j < n - 1; j++)
        {
            if (arr[j] > arr[j + 1])
            {  
                // Ordem crescente
                aux = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = aux;
            }
        }
    }
}


// Implementação do Bubble Sort (V2)
void bubbleSortMelhorado(int arr[], int n)
{
    int troca = 1, aux;
    for (int i = 1; i < n && troca; i++)
    {
        troca = 0;
        for (int j = 0; j < n - i; j++)
        {
            if (arr[j] > arr[j + 1])
            {  
                // Ordem crescente
                troca = 1;
                aux = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = aux;
            }
        }
    }
}


// Implementação do Selection Sort
void selectionSort(int arr[], int n)
{
    int aux; //Auxiliar para a troca
    
    for (int i = 0; i < n - 1; i++)
    {
        int min_idx = i;
        for (int j = i + 1; j < n; j++)
        {
            if (arr[j] < arr[min_idx])
            {
                min_idx = j;
            }
        }
        if (min_idx != i)
        {
            aux = arr[i];
            arr[i] = arr[min_idx];
            arr[min_idx] = aux;
        }
    }
}


// Implementação do Insertion Sort
void insertionSort(int arr[], int n)
{
    int key, j;
    for (int i = 1; i < n; i++)
    {
        key = arr[i];
        j = i - 1;
        while (j >= 0 && arr[j] > key)
        {
            arr[j + 1] = arr[j];
            j--;
        }
        arr[j + 1] = key;
    }
}


// Declaração antecipada da função partition
int partition(int arr[], int low, int high);

// Implementação do Quick Sort
void quickSort(int arr[], int low, int high)
{
    if (low < high)
    {
        int pi = partition(arr, low, high);
        quickSort(arr, low, pi - 1);
        quickSort(arr, pi + 1, high);
    }
}

int partition(int arr[], int low, int high)
{
    int randomPivot = low + rand() % (high - low);  // Escolhe um pivô aleatório entre low e high
    int aux1, aux2, aux3;  // auxílio nas trocas
    aux3 = arr[randomPivot];
    arr[randomPivot] = arr[high];
    arr[high] = aux3;
    int pivot = arr[high];
    int i = (low - 1);  // Índice do menor elemento

    for (int j = low; j < high; j++)
    {
        if (arr[j] < pivot)
        {
            i++;
            aux1 = arr[i];
            arr[i] = arr[j];
            arr[j] = aux1;
        }
    }
    aux2 = arr[i + 1];
    arr[i + 1] = arr[high];
    arr[high] = aux2;
    return (i + 1);
}


// Função para verificar se o array foi ordenado corretamente
bool verificarOrdenacao(int arr[], int n, bool crescente = true)
{
    if (crescente)
    {
        for (int i = 0; i < n - 1; i++)
        {
            if (arr[i] > arr[i + 1])
            {  
                // Verifica se está em ordem crescente
                return false;
            }
        }
    } 
    else 
    {
        for (int i = 0; i < n - 1; i++)
        {
            if (arr[i] < arr[i + 1])
            {  
                // Verifica se está em ordem decrescente
                return false;
            }
        }
    }
    return true;
}


// Função para gravar os resultados em um arquivo
void gravarRelatorio(const string& texto) 
{
    ofstream arquivo("resultados.txt", ios::app);
    if (!arquivo) 
    {
        cerr << "Erro ao abrir o arquivo resultados.txt" << endl;
        exit(1);
    }
    arquivo << texto << endl;
    arquivo.close();
}


// Função para medir o tempo de execução do algoritmo e gerar relatório
void medirTempoExecucao(void (algoritmo)(int[], int), int arr[], int n, const char* nomeArquivo, const char* nomeAlgoritmo, bool crescente)
{
    stringstream resultado;
    resultado << "Ordenando arquivo " << nomeArquivo << " com " << nomeAlgoritmo << "...\n";

    clock_t inicio = clock();  // Marca o tempo inicial
    algoritmo(arr, n);         // Chama o algoritmo de ordenação
    clock_t fim = clock();     // Marca o tempo final

    double tempoGasto = double(fim - inicio) / CLOCKS_PER_SEC;  // Calcula o tempo gasto
    resultado << nomeAlgoritmo << " demorou: " << fixed << setprecision(6) << tempoGasto << " segundos.\n";
    

    // Verifica se o array foi ordenado corretamente
    if (verificarOrdenacao(arr, n, crescente))
    {
        resultado << "Ordenação correta!" << endl;
        resultado << "============================================================================\n";
    } 
    else
    {
        resultado << "Erro na ordenação!" << endl;
        resultado << "============================================================================\n";
    }

    cout << resultado.str();   // Exibe no console
    gravarRelatorio(resultado.str()); // Grava no arquivo
}

void medirTempoExecucaoQuickSort(void (algoritmo)(int[], int, int), int arr[], int n, const char* nomeArquivo, const char* nomeAlgoritmo, bool)
{
    stringstream resultado;
    resultado << "Ordenando arquivo " << nomeArquivo << " com " << nomeAlgoritmo << "...\n";

    clock_t inicio = clock();  // Marca o tempo inicial
    algoritmo(arr, 0, n - 1);  // Chama o algoritmo de ordenação
    clock_t fim = clock();     // Marca o tempo final

    double tempoGasto = double(fim - inicio) / CLOCKS_PER_SEC;  // Calcula o tempo gasto
    resultado << nomeAlgoritmo << " demorou: " << fixed << setprecision(6) << tempoGasto << " segundos.\n";

    // Verifica se o array foi ordenado corretamente
    if (verificarOrdenacao(arr, n, true)) 
    {
        resultado << "Ordenação correta!" << endl;
        resultado << "============================================================================\n";
    } 
    else 
    {
        resultado << "Erro na ordenação!" << endl;
        resultado << "============================================================================\n";
    }

    cout << resultado.str();   // Exibe no console
    gravarRelatorio(resultado.str()); // Grava no arquivo
}



int main()
{
    SetConsoleOutputCP(CP_UTF8); //Comando para permitir a inclusão de caracteres especias/com acento
    
    srand(time(0)); // Inicializa a semente do gerador de números aleatórios

    int TAM = 100000; // Definição do tamanho dos arrays

    // Arrays para armazenar os dados dos três arquivos
    int arrAleatorio[TAM];
    int arrCrescente[TAM];
    int arrDecrescente[TAM];


    // Limpar o conteúdo anterior do arquivo de resultados
    ofstream arquivo("resultados.txt", ios::trunc);
    if (!arquivo) 
    {
        cerr << "Erro ao abrir o arquivo resultados.txt para limpeza" << endl;
        exit(1);
    }
    arquivo.close();


    // Aplicar Bubble Sort (Nova Versão) nos três conjuntos de dados e medir o tempo
    carregarDados("aleat_100000.txt", arrAleatorio);
    medirTempoExecucao(bubbleSort, arrAleatorio, TAM, "aleat_100000.txt", "Bubble Sort (V1)", true);

    carregarDados("cresc_100000.txt", arrCrescente);
    medirTempoExecucao(bubbleSort, arrCrescente, TAM, "cresc_100000.txt", "Bubble Sort (V1)", true);

    carregarDados("decresc_100000.txt", arrDecrescente);
    medirTempoExecucao(bubbleSort, arrDecrescente, TAM, "decresc_100000.txt", "Bubble Sort (V1)", true);



    // Aplicar Bubble Sort (Melhorado) nos três conjuntos de dados e medir o tempo
    carregarDados("aleat_100000.txt", arrAleatorio);
    medirTempoExecucao(bubbleSortMelhorado, arrAleatorio, TAM, "aleat_100000.txt", "Bubble Sort (V3)", true);

    carregarDados("cresc_100000.txt", arrCrescente);
    medirTempoExecucao(bubbleSortMelhorado, arrCrescente, TAM, "cresc_100000.txt", "Bubble Sort (V3)", true);

    carregarDados("decresc_100000.txt", arrDecrescente);
    medirTempoExecucao(bubbleSortMelhorado, arrDecrescente, TAM, "decresc_100000.txt", "Bubble Sort (V3)", true);



    // Aplicar Selection Sort nos três conjuntos de dados e medir o tempo
    carregarDados("aleat_100000.txt", arrAleatorio);
    medirTempoExecucao(selectionSort, arrAleatorio, TAM, "aleat_100000.txt", "Selection Sort", true);

    carregarDados("cresc_100000.txt", arrCrescente);
    medirTempoExecucao(selectionSort, arrCrescente, TAM, "cresc_100000.txt", "Selection Sort", true);

    carregarDados("decresc_100000.txt", arrDecrescente);
    medirTempoExecucao(selectionSort, arrDecrescente, TAM, "decresc_100000.txt", "Selection Sort", true);



    // Aplicar Insertion Sort nos três conjuntos de dados e medir o tempo
    carregarDados("aleat_100000.txt", arrAleatorio);
    medirTempoExecucao(insertionSort, arrAleatorio, TAM, "aleat_100000.txt", "Insertion Sort", true);

    carregarDados("cresc_100000.txt", arrCrescente);
    medirTempoExecucao(insertionSort, arrCrescente, TAM, "cresc_100000.txt", "Insertion Sort", true);

    carregarDados("decresc_100000.txt", arrDecrescente);
    medirTempoExecucao(insertionSort, arrDecrescente, TAM, "decresc_100000.txt", "Insertion Sort", true);



    // Aplicar Quick Sort nos três conjuntos de dados e medir o tempo
    carregarDados("aleat_100000.txt", arrAleatorio);
    medirTempoExecucaoQuickSort(quickSort, arrAleatorio, TAM, "aleat_100000.txt", "Quick Sort", true);

    carregarDados("cresc_100000.txt", arrCrescente);
    medirTempoExecucaoQuickSort(quickSort, arrCrescente, TAM, "cresc_100000.txt", "Quick Sort", true);

    carregarDados("decresc_100000.txt", arrDecrescente);
    medirTempoExecucaoQuickSort(quickSort, arrDecrescente, TAM, "decresc_100000.txt", "Quick Sort", false);



    return 0;
}