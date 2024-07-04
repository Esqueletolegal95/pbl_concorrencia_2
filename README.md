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
# Permite gerenciar contas ?

O sistema utiliza servidores Flask para rodar uma aplicação web onde é possível criar, logar e gerenciar uma conta bancária, além de criar e realizar transações.

# Permite selecionar e realizar transferência entre diferentes contas ?

O sistema possuí um sistema bancário capaz de realizar tranferencias entre um mesmo banco ou entre bancos diferentes, havendo assim duas formas de tranferências, uma simples, onde é tranferido valor de uma conta A para uma conta B, e uma complexa, onde é tranferido valor de uma conta A e B para uma conta C.
