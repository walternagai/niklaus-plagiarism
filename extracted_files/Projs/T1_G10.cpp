#include <iostream>
#include <fstream>
#include <ctime>

using namespace std;

bool estaOrdenado(int vetor[], int tamanho) {
	for (int i = 1; i < tamanho; i++) {
		if (vetor[i] < vetor[i - 1]) {
			return false;
		}
	}
	return true;
}

void gravarResultado(const char* algoritmo, bool estaOrdenado, double tempoGasto, const char* arquivoSaida) {
	ofstream arquivo(arquivoSaida, ios::app);
	arquivo << algoritmo << ":\n";
	arquivo << (estaOrdenado ? "Está Ordenado\n" : "Não Está Ordenado\n");
	arquivo << "Tempo gasto: " << tempoGasto << " segundos\n";
	arquivo << "Ordenou\n\n";
	arquivo.close();
}

void ordenarInsertion(int vetor[], int tamanho) {
	for (int i = 1; i < tamanho; i++) {
		int atual = vetor[i];
		int j = i;
		while (j > 0 && vetor[j - 1] > atual) {
			vetor[j] = vetor[j - 1];
			j--;
		}
		vetor[j] = atual;
	}
}

void quickSort(int vetor[], int inicio, int fim) {
	if (inicio < fim) {
		int pivo = vetor[(inicio + fim) / 2];
		int i = inicio;
		int j = fim;

		while (i <= j) {
			while (vetor[i] < pivo) i++;
			while (vetor[j] > pivo) j--;

			if (i <= j) {
				swap(vetor[i], vetor[j]);
				i++;
				j--;
			}
		}

		quickSort(vetor, inicio, j);
		quickSort(vetor, i, fim);
	}
}

void ordenarSelection(int vetor[], int tamanho) {
	for (int i = 0; i < tamanho - 1; i++) {
		int menorIndice = i;
		for (int j = i + 1; j < tamanho; j++) {
			if (vetor[j] < vetor[menorIndice]) {
				menorIndice = j;
			}
		}
		if (menorIndice != i) {
			swap(vetor[i], vetor[menorIndice]);
		}
	}
}

void ordenarBubble(int vetor[], int tamanho) {
	for (int i = 0; i < tamanho - 1; i++) {
		for (int j = 0; j < tamanho - 1 - i; j++) {
			if (vetor[j] > vetor[j + 1]) {
				swap(vetor[j], vetor[j + 1]);
			}
		}
	}
}

int carregarDadosArquivo(const char* nomeArquivo, int vetor[], int maxTam) {
	ifstream entrada(nomeArquivo);
	int indice = 0;

	if (entrada.is_open()) {
		while (entrada >> vetor[indice] && indice < maxTam) {
			indice++;
		}
		entrada.close();
	} else {
		cout << "Erro ao abrir arquivo " << nomeArquivo << endl;
		return -1;
	}

	return indice;
}

void testarAlgoritmo(void (*algoritmo)(int[], int), const char* nomeAlgoritmo, int vetor[], int tamanho, const char* arquivoSaida) {
	clock_t inicio = clock();
	algoritmo(vetor, tamanho);
	clock_t fim = clock();

	double tempoExecucao = double(fim - inicio) / CLOCKS_PER_SEC;
	bool sucesso = estaOrdenado(vetor, tamanho);
	gravarResultado(nomeAlgoritmo, sucesso, tempoExecucao, arquivoSaida);
}

void testarQuickSort(int vetor[], int tamanho) {
	quickSort(vetor, 0, tamanho - 1);
}

int main() {
	int vetor[100000];
	const char* arquivoSaida = "resultados.txt";
	const int tamanhoVetor = 100000;

	ofstream(arquivoSaida).close();

	const char* arquivosEntrada[] = {"aleat_100000.txt", "crescente.txt", "decrescente.txt"};
	const char* descricoes[] = {"Aleatório", "Crescente", "Decrescente"};

	for (int i = 0; i < 3; i++) {
		if (carregarDadosArquivo(arquivosEntrada[i], vetor, tamanhoVetor) == -1) {
			return 1; 
		}

		ofstream arquivo(arquivoSaida, ios::app);
		arquivo << descricoes[i] << ":\n\n";
		arquivo.close();

		testarAlgoritmo(ordenarBubble, "Bubble Sort", vetor, tamanhoVetor, arquivoSaida);
		carregarDadosArquivo(arquivosEntrada[i], vetor, tamanhoVetor); 
		
		testarAlgoritmo(ordenarSelection, "Selection Sort", vetor, tamanhoVetor, arquivoSaida);
		carregarDadosArquivo(arquivosEntrada[i], vetor, tamanhoVetor);
		testarAlgoritmo(testarQuickSort, "Quick Sort", vetor, tamanhoVetor, arquivoSaida);  
		
		carregarDadosArquivo(arquivosEntrada[i], vetor, tamanhoVetor);
		testarAlgoritmo(ordenarInsertion, "Insertion Sort", vetor, tamanhoVetor, arquivoSaida);
	}

	return 0;
}
