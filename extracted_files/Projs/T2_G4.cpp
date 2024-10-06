//Diana Duarte Dias 2024006685
//Gabriel Leandro Fonseca Silva 2024008198
//Giovanna Maira Soares Chaves 2024005472
//17/09/2024
//O código avalia o tempo de ordenação de diferentes funções para ordenar um arquivo, utilizando três arquivos diferentes
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

    // Leitura do arquivo aleatório
    while (getline(arq_ent, s)) {
        vetor_aleat[j++] = stoi(s);  // Conversão de string para inteiro
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

    // Gerar resultados para o arquivo aleatório
    writeResults(arq_said, "aleat_100000.txt", vetor_aleat, n);

    // Gerar resultados para o arquivo crescente
    arq_said << "cresc_100000.txt\n";
    cout << "cresc_100000.txt\n";
    writeResults(arq_said, "", vetor_cresc, n);

    // Gerar resultados para o arquivo decrescente
    writeResults(arq_said, "decresc_100000.txt", vetor_decresc, n);

    return 0;
}


// Função de ordenação QuickSort
void quicksort(int v[], int left, int right) {
    // Seleciona o pivô como o elemento do meio do intervalo
    int pivo = v[(left + right) / 2];
    int i = left, j = right;
    do {
        // Move i para a direita até encontrar um elemento maior ou igual ao pivô
        while (v[i] < pivo) i++;
        // Move j para a esquerda até encontrar um elemento menor ou igual ao pivô
        while (v[j] > pivo) j--;
        // Se os índices ainda estiverem em ordem, troca os elementos e ajusta os índices
        if (i <= j) {
            int aux = v[i];
            v[i] = v[j];
            v[j] = aux;
            i++;
            j--;
        }
    } while (i <= j); // Continua até que os índices se cruzem
    // Recursivamente ordena as duas metades
    if (left < j) quicksort(v, left, j);
    if (i < right) quicksort(v, i, right);
}

// Função de ordenação Insertion Sort
void insertionsort(int v[], int n) {
    for (int i = 1; i < n; i++) {
        int aux = v[i], j = i;
        // Move os elementos maiores que o 'aux' uma posição para a direita
        while (j > 0 && v[j - 1] > aux) {
            v[j] = v[j - 1];
            j--;
        }
        v[j] = aux; // Insere o 'aux' na posição correta
    }
}

// Função de ordenação Selection Sort
void selectionsort(int v[], int n) {
    for (int i = 0; i < n - 1; i++) {
        int i_menor = i;
        // Encontra o índice do menor elemento na sublista
        for (int j = i + 1; j < n; j++) {
            if (v[j] < v[i_menor]) i_menor = j;
        }
        // Troca o menor elemento encontrado com o primeiro elemento da sublista
        int aux = v[i];
        v[i] = v[i_menor];
        v[i_menor] = aux;
    }
}

// Função de ordenação Bubble Sort Melhorado
void bubblesortmelhorado(int v[], int n) {
    bool swapped; // Utiliza uma variável booleana para indicar se houve troca
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

        // Se não houve nenhuma troca, o array já está ordenado
        if (!swapped) break;
    }
}
// Função de ordenação Bubble Sort
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
// Função para escrever os resultados dos testes de ordenação em um arquivo e no console
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
