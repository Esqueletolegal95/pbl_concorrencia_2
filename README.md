# pbl_concorrencia_2

## Como executar a aplicação:
 Para executar os dispositivos e o servidor é necessário abrir o terminal até o diretório onde está o arquivo ```DOCKERFILE``` e executar os passos abaixo:
 1. **Criar Containers Para Servidor**

    ```bash
    docker build -t banco .
    ```

2. **Executar o Container (Configurando as Portas)**

    ```bash
     docker run --network=host banco
    ```
