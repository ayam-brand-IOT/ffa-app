FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para OpenCV y otras librerías
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0

# Copiar Pipfile y Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Instalar pipenv y las dependencias de Python
RUN pip install pipenv && pipenv install --system --deploy

# Copiar el código de la aplicación
COPY . .

# Exponer el puerto del servidor
EXPOSE 8000

# Comando para iniciar la aplicación
CMD ["python", "main.py"]