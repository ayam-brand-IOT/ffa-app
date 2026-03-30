FROM python:3.11-slim

WORKDIR /app

# libgl1-mesa-glx was removed in Debian Trixie; libgl1 + libglx-mesa0 replace it.
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglx-mesa0 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python directamente desde requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

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
