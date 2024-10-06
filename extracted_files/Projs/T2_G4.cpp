//Diana Duarte Dias 2024006685
//Gabriel Leandro Fonseca Silva 2024008198
//Giovanna Maira Soares Chaves 2024005472
//17/09/2024
//O c�digo avalia o tempo de ordena��o de diferentes fun��es para ordenar um arquivo, utilizando tr�s arquivos diferentes
#include<iostream>
#include <fstream>
#include <ctime>
using namespace std;
bool ordenado_crescente(int v[]);
bool ordenado_decrescente(int v[]);
void quicksort(int v[], int left, int right);
void insertionsort(int v[], int n);
void selectionsort(int v[], int n);
void bubblesortmelhorado(int v[], int n);
void bubblesort(int v[]);
void writeResults(ofstream &arq_said, const string &filename, int v[], int n);

int main() {
    ifstream arq_ent("aleat_100000.txt"), arq_ent1("cresc_100000.txt"), arq_ent2("decresc_100000.txt");
    ofstream arq_said("resultados.txt");

    if (!arq_ent.is_open() || !arq_said.is_open()) {
        cout << "Erro ao abrir arquivo!" << endl;
        return 1;
    }

    // Arrays para armazenar os dados dos arquivos
    int vetor_aleat[100000], vetor_cresc[100000], vetor_decresc[100000];
    string s;
    int j = 0, n = 100000;

    // Leitura do arquivo aleat�rio
    while (getline(arq_ent, s)) {
        vetor_aleat[j++] = stoi(s);  // Convers�o de string para inteiro
    }

    // Leitura do arquivo crescente
    j = 0;
    while (getline(arq_ent1, s)) {
        vetor_cresc[j++] = stoi(s);
    }

    // Leitura do arquivo decrescente
    j = 0;
    while (getline(arq_ent2, s)) {
        vetor_decresc[j++] = stoi(s);
    }

    // Gerar resultados para o arquivo aleat�rio
    writeResults(arq_said, "aleat_100000.txt", vetor_aleat, n);

    // Gerar resultados para o arquivo crescente
    arq_said << "cresc_100000.txt\n";
    cout << "cresc_100000.txt\n";
    writeResults(arq_said, "", vetor_cresc, n);

    // Gerar resultados para o arquivo decrescente
    writeResults(arq_said, "decresc_100000.txt", vetor_decresc, n);

    return 0;
}


// Fun��o de ordena��o QuickSort
void quicksort(int v[], int left, int right) {
    // Seleciona o piv� como o elemento do meio do intervalo
    int pivo = v[(left + right) / 2];
    int i = left, j = right;
    do {
        // Move i para a direita at� encontrar um elemento maior ou igual ao piv�
        while (v[i] < pivo) i++;
        // Move j para a esquerda at� encontrar um elemento menor ou igual ao piv�
        while (v[j] > pivo) j--;
        // Se os �ndices ainda estiverem em ordem, troca os elementos e ajusta os �ndices
        if (i <= j) {
            int aux = v[i];
            v[i] = v[j];
            v[j] = aux;
            i++;
            j--;
        }
    } while (i <= j); // Continua at� que os �ndices se cruzem
    // Recursivamente ordena as duas metades
    if (left < j) quicksort(v, left, j);
    if (i < right) quicksort(v, i, right);
}

// Fun��o de ordena��o Insertion Sort
void insertionsort(int v[], int n) {
    for (int i = 1; i < n; i++) {
        int aux = v[i], j = i;
        // Move os elementos maiores que o 'aux' uma posi��o para a direita
        while (j > 0 && v[j - 1] > aux) {
            v[j] = v[j - 1];
            j--;
        }
        v[j] = aux; // Insere o 'aux' na posi��o correta
    }
}

// Fun��o de ordena��o Selection Sort
void selectionsort(int v[], int n) {
    for (int i = 0; i < n - 1; i++) {
        int i_menor = i;
        // Encontra o �ndice do menor elemento na sublista
        for (int j = i + 1; j < n; j++) {
            if (v[j] < v[i_menor]) i_menor = j;
        }
        // Troca o menor elemento encontrado com o primeiro elemento da sublista
        int aux = v[i];
        v[i] = v[i_menor];
        v[i_menor] = aux;
    }
}

// Fun��o de ordena��o Bubble Sort Melhorado
void bubblesortmelhorado(int v[], int n) {
    bool swapped; // Utiliza uma vari�vel booleana para indicar se houve troca
    int aux;

    // Continua a ordenar enquanto houver trocas a serem feitas
    for (int i = 0; i < n - 1; i++) {
        swapped = false; // Inicializa a flag swapped como falso para cada nova passagem

        // Faz uma passagem pelos elementos, trocando os elementos fora de ordem
        for (int j = 0; j < n - i - 1; j++) {
            if (v[j] > v[j + 1]) {
                // Troca os elementos se estiverem fora de ordem
                aux = v[j];
                v[j] = v[j + 1];
                v[j + 1] = aux;
                swapped = true; // Marca que houve uma troca
            }
        }

        // Se n�o houve nenhuma troca, o array j� est� ordenado
        if (!swapped) break;
    }
}
// Fun��o de ordena��o Bubble Sort
void bubblesort(int v[]) {
    int aux, n = 99999;
    // Ordena o array com Bubble Sort, sempre comparando pares de elementos
    for (int i = 1; i < n; i++) {
        for (int j = 0; j < n - 1; j++) {
            if (v[j] > v[j + 1]) {
                aux = v[j];
                v[j] = v[j + 1];
                v[j + 1] = aux;
            }
        }
    }
}
bool ordenado_crescente(int v[])
{
    for(int i=0; i<(99999); i++)
    {
        if(v[i] > v[i+1])
            return false;
    }
    return true;
}
bool ordenado_decrescente(int v[])
{
    for(int i=0; i<(99999); i++)
    {
        if(v[i] < v[i+1])
            return false;
    }
    return true;
}
// Fun��o para escrever os resultados dos testes de ordena��o em um arquivo e no console
void writeResults(ofstream &arq_said, const string &filename, int v[], int n) {
    string result;
    result = filename + "\n";
    if (ordenado_crescente(v))
    {
        result += "Esta ordenado!\n";
    } else {
        result += "Nao esta ordenado!\n";
    }

    int k[100000]; // Array para copiar os dados
    for (int i = 0; i < n; i++) {
        k[i] = v[i]; // Copiando o array original
    }

    // Teste QuickSort
    clock_t inicial = clock();
    quicksort(k, 0, n - 1);
    result += "quicksort: " + to_string((float)(clock() - inicial) / CLOCKS_PER_SEC) + " segundos\n";
    result += "Ordenou!\n";

    // Teste Insertion Sort
    for (int i = 0; i < n; i++) {
        k[i] = v[i];
    }
    inicial = clock();
    insertionsort(k, n);
    result += "insertionsort: " + to_string((float)(clock() - inicial) / CLOCKS_PER_SEC) + " segundos\n";
    result += "Ordenou!\n";

    // Teste Selection Sort
    for (int i = 0; i < n; i++) {
        k[i] = v[i];
    }
    inicial = clock();
    selectionsort(k, n);
    result += "selection_sort: " + to_string((float)(clock() - inicial) / CLOCKS_PER_SEC) + " segundos\n";
    result += "Ordenou!\n";

    // Teste Bubble Sort Melhorado
    for (int i = 0; i < n; i++) {
        k[i] = v[i];
    }
    inicial = clock();
    bubblesortmelhorado(k, n);
    result += "bubblesort_melhorado: " + to_string((float)(clock() - inicial) / CLOCKS_PER_SEC) + " segundos\n";
    result += "Ordenou!\n";

    // Teste Bubble Sort
    for (int i = 0; i < n; i++) {
        k[i] = v[i];
    }
    inicial = clock();
    bubblesort(k);
    result += "bubblesort: " + to_string((float)(clock() - inicial) / CLOCKS_PER_SEC) + " segundos\n";
    result += "Ordenou!\n";

    result += "________________________________\n";

    // Escreve o resultado no arquivo e exibe no console
    arq_said << result;
    cout << result;
}
