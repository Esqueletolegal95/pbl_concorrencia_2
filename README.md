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

# Comunicação entre servidores
A aplicação possui um servidor FLASK com duas rotas API para a transferência, uma para executar e outra para processar e retornar uma mensagem de confirmação ACK que garante que a mensagem foi enviada e que os dados podem ser alterados em todas as contas.
![image](https://github.com/Esqueletolegal95/pbl_concorrencia_2/assets/113029820/234517ea-a473-4c7b-a0b5-d7521453e6e9)

# Sincronização em um único servidor.
A sulução utiliza uma rota api para o recebimento de transações, onde é utilizado um gerenciador de bloqueio para impedir que mais de uma transação seja processada ao mesmo tempo, impedindo inconsistência de dados
![image](https://github.com/Esqueletolegal95/pbl_concorrencia_2/assets/113029820/76755a2b-a1f0-4e7a-90fc-bbe28e5aae87)
# Algoritmo da concorrencia distribuída está teoricamente bem empregado?
O algoritmo utilizado é um two phase lock em conjunto do protocolo ACK, utilizado para que aja sincronia entre os servidores, adequado para sistemas simples. Para algo mais complexo, poderia ter sido utilizado o two phase commit.

# Tratamento da confiabilidade

Se um banco intermediário ou final estiver offline durante uma transferência, a transação não poderá ser completada. O sistema tentará realizar a operação e falhará.

# Pelo menos uma transação concorrente é realizada ?

Sim, pelo menos uma transação concorrente é realizada, pois o sistema permite múltiplas leituras simultâneas e serializa as escritas. O uso de locks garante que o saldo permanece consistente mesmo com transações concorrentes.
