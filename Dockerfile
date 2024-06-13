# Use a imagem base do Python
FROM python:3.9-slim

# Defina o diretório de trabalho como /app
WORKDIR /app

# Copie os arquivos necessários para o contêiner
COPY requirements.txt .
COPY apptest2PL.py .
COPY templates/ templates/
COPY static/ static/

# Instale as dependências
RUN pip install --no-cache-dir --upgrade pip
RUN pip install Flask
RUN pip install requests

# Exponha a porta 5000
EXPOSE 5050

# Comando para executar o aplicativo Flask quando o contêiner for iniciado
CMD ["python", "apptest2PL.py"]
