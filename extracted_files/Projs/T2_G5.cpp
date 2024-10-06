// João Henrique Veloso Maglhães - 2024003520
// Eduardo Castro Guidette - 2024014382
// Emilio José De Almeida Silveira - 2024014103
// 16/09/2024
// Nosso grupo construiu um programa que análisa os arquivos enviados pela professora e trasfere os números para o vetor,
// após isso verifica se está ordenado, caso não esteja o programa ordena os numeros de acordo com as funções solicitadas 
// e imprime o tempo que demorou para ordenar no arquivo de saída, mas caso já esteja ordenado ele apenas confere e imprime
// o tempo de execução no arquivo de saída.

#include <iostream>
#include <fstream>
#include <ctime>
using namespace std;

void quicksort(int v[], int left, int right)
{
    int pivo = v[(left + right) / 2];
    int i = left, j = right;
    do
    {
        while (v[i] < pivo)
            i++;
        while (v[j] > pivo)
            j--;
        if (i <= j)
        {
            int aux = v[i];
            v[i] = v[j];
            v[j] = aux;
            i++;
            j--;
        }
    } while (i <= j);
    if (left < j)
        quicksort(v, left, j);
    if (i < right)
        quicksort(v, i, right);
}

void insertionsort(int v[], int n)
{
    for (int i = 1; i < n; i++)
    {
        int aux = v[i], j = i;
        while (j > 0 && v[j - 1] > aux)
        {
            v[j] = v[j - 1];
            j--;
        }
        v[j] = aux;
    }
}

void selectionsort(int v[], int n)
{
    for (int i = 0; i < n - 1; i++)
    {
        int i_menor = i;
        for (int j = i + 1; j < n; j++)
        {
            if (v[j] < v[i_menor])
                i_menor = j;
        }
        int aux = v[i];
        v[i] = v[i_menor];
        v[i_menor] = aux;
    }
}

void bubble_sortmel(int v[], int n)
{
    int troca = 1, aux;
    for (int i = 1; i < n && troca; i++)
    {
        troca = 0;
        for (int j = 0; j < n - i; j++)
        {
            if (v[j] > v[j + 1])
            {
                troca = 1;
                aux = v[j];
                v[j] = v[j + 1];
                v[j + 1] = aux;
            }
        }
    }
}

void bubble_sort(int v[])
{
    int aux, n = 99999;
    for (int i = 1; i < n; i++)
    {
        for (int j = 0; j < n - 1; j++)
        {
            if (v[j] > v[j + 1])
            {
                aux = v[j];
                v[j] = v[j + 1];
                v[j + 1] = aux;
            }
        }
    }
}

bool confere(int v[], int n, ofstream &fout)
{
    for (int i = 0; i < n - 1; i++)
    {
        if (v[i] > v[i + 1])
        {
            cout << "Nao esta ordenado!" << endl;
            fout << "Nao esta ordenado!\n";
            return false;
        }
    }
    cout << "Esta ordenado!" << endl;
    fout << "Esta ordenado!\n";
    fout << "\n";
    return true;
}

void writeResults(ofstream &arq_said, const string &nome_arquivo, int v[], int n) // Prepara a saida pro cmd e pro arquivo
{
    string resultado;
    resultado = nome_arquivo + "\n";


    int k[100000]; // Array para copiar os dados
    for (int i = 0; i < n; i++)
    {
        k[i] = v[i]; // Copiando o array original
    }

    // Quicksort
    clock_t inicial = clock();
    quicksort(k, 0, n - 1);
    resultado += "quicksort: " + to_string((float)(clock() - inicial) / CLOCKS_PER_SEC) + " segundos\n";
    resultado += "Ordenou!\n";

    // Insertion sort
    for (int i = 0; i < n; i++)
    {
        k[i] = v[i];
    }
    inicial = clock();
    insertionsort(k, n);
    resultado += "insertionsort: " + to_string((float)(clock() - inicial) / CLOCKS_PER_SEC) + " segundos\n";
    resultado += "Ordenou!\n";

    // Selection sort
    for (int i = 0; i < n; i++)
    {
        k[i] = v[i];
    }
    inicial = clock();
    selectionsort(k, n);
    resultado += "selection_sort: " + to_string((float)(clock() - inicial) / CLOCKS_PER_SEC) + " segundos\n";
    resultado += "Ordenou!\n";

    // Bubble sort melhorado
    for (int i = 0; i < n; i++)
    {
        k[i] = v[i];
    }
    inicial = clock();
    bubble_sortmel(k, n);
    resultado += "bubblesort_melhorado: " + to_string((float)(clock() - inicial) / CLOCKS_PER_SEC) + " segundos\n";
    resultado += "Ordenou!\n";

    // Bubble sort
    for (int i = 0; i < n; i++)
    {
        k[i] = v[i];
    }
    inicial = clock();
    bubble_sort(k);
    resultado += "bubblesort: " + to_string((float)(clock() - inicial) / CLOCKS_PER_SEC) + " segundos\n";
    resultado += "Ordenou!\n";

    resultado += "________________________________\n";

    // escrever no cmd e no arquivo
    arq_said << resultado;
    cout << resultado;
}

int main()
{
    ifstream arq_ent("aleat_100000.txt"), arq_ent1("cresc_100000.txt"), arq_ent2("decresc_100000.txt");
    ofstream arq_said("resultados.txt");

    if (!arq_ent.is_open() || !arq_said.is_open())
    {
        cout << "Erro ao abrir arquivo!" << endl;
        return 1;
    }

    // Arrays para armazenar os dados dos arquivos
    int vetor_aleat[100000], vetor_cresc[100000], vetor_decresc[100000];
    string s;
    int j = 0, n = 100000;

    // Leitura do arquivo aleatório
    while (getline(arq_ent, s))
    {
        vetor_aleat[j++] = stoi(s); // Uso do stoi para converter string para inteiro
    }

    // Leitura do arquivo crescente
    j = 0;
    while (getline(arq_ent1, s))
    {
        vetor_cresc[j++] = stoi(s);
    }

    // Leitura do arquivo decrescente
    j = 0;
    while (getline(arq_ent2, s))
    {
        vetor_decresc[j++] = stoi(s);
    }

    // Gerar resultados para o arquivo aleatório
    arq_said << "aleat_100000.txt\n";
    cout << "Verificando se o vetor aleatorio esta ordenado...\n";
    confere(vetor_aleat, n, arq_said);  // Verificação do vetor aleatório
    writeResults(arq_said, "aleat_100000.txt", vetor_aleat, n);

    // Gerar resultados para o arquivo crescente
    arq_said << "cresc_100000.txt\n";
    cout << "Verificando se o vetor crescente esta ordenado...\n";
    confere(vetor_cresc, n, arq_said);  // Verificação do vetor crescente
    writeResults(arq_said, "cresc_100000.txt", vetor_cresc, n);

    // Gerar resultados para o arquivo decrescente
    arq_said << "decresc_100000.txt\n";
    cout << "Verificando se o vetor decrescente esta ordenado...\n";
    confere(vetor_decresc, n, arq_said);  // Verificação do vetor decrescente
    writeResults(arq_said, "decresc_100000.txt", vetor_decresc, n);

    return 0;
}
