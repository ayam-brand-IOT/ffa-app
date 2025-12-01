FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para OpenCV y otras librerías
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar Pipfile y Pipfile.lock
COPY Pipfile Pipfile.lock ./

# Instalar pipenv y las dependencias de Python
RUN pip install pipenv && pipenv install --system --deploy

# Copiar el código de la aplicación
COPY . .

# Variable de entorno para modo desarrollo
# DEV_MODE=true para usar emuladores (TLB_MODBUS_dev, IOs_dev)
# DEV_MODE=false para usar hardware real (TLB_MODBUS, IOs)
ENV DEV_MODE=true

# Exponer el puerto del servidor
EXPOSE 3030

# Comando para iniciar la aplicación
CMD ["python", "main.py"]
