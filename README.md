
# ffa-app

**ffa-app** is the Python-based core component of the **Frozen Fish Analysis (FFA)** system. It is responsible for managing hardware interactions on the Raspberry Pi, communicating with the `ffa-server`, and serving the compiled UI for user interaction.

## Overview

### Key Functionalities:

- **RS-485**: Reads fish weight through serial communication.
- **Webcam**: Captures images of the fish.
- **GPIO Control**: Turns on/off flash and laser via digital IOs.
- **WebSocket Communication**: Interfaces with the UI and `ffa-server`.
- **Web Hosting**: Serves the pre-built Vue.js UI as a local website.

### Role in the System:
- Acts as the intermediary between **hardware**, the **user interface (UI)**, and the **ffa-server** for data storage and processing.

## Architecture

```
      ┌──────────┐       ┌─────────────┐
      │ RS-485    │       │ Webcam       │
      │ (Weight)  │       │ (Image)      │
      └─────┬─────┘       └───────┬─────┘
            │                      │
            │       ┌───────┐      │
            │       │ ffa-   │      │
            │       │ app    │      │
            │       └───┬───┘      │
            │           │           │
          ┌─┴─┐       ┌─┴─┐       │
          │UI │<------>│WS │<---->│
          └───┘        └───┘       │
            │                       │
            │                     ┌─┴─┐
            │                     │ffa-│
            │                     │server
            │                     └────┘
```

## Requirements

- **Raspberry Pi** running Linux (Raspberry Pi OS).
- **Python 3.11**.

## Installation

### Using Pipenv

1. **Install Pipenv** (if not already installed):
   ```bash
   pip install pipenv
   ```

2. **Clone the Repository**:
   ```bash
   git clone https://github.com/your_org/ffa-app.git
   cd ffa-app
   ```

3. **Install Dependencies** using Pipenv:
   ```bash
   pipenv install
   ```

4. **Activate the Virtual Environment**:
   ```bash
   pipenv shell
   ```

5. **Set Up Environment Variables**:  
   Create a `.env` file for configurations:
   ```
   RS485_PORT=/dev/ttyUSB0
   WEBCAM_DEVICE=/dev/video0
   FLASH_PIN=17
   LASER_PIN=27
   UI_PORT=8000
   ```

6. **Run the Application**:
   ```bash
   python main.py --debug
   ```

The UI will be available at `http://<raspberry_ip>:8000`.

## Logs and Debugging

- **View Service Logs**:
   ```bash
   journalctl -u ffa-app.service -f
   ```

- **Enable Debug Mode**:
   Run with the `--debug` flag to display detailed logs.

- **Hardware Debugging**:
   - Check RS-485 connectivity using `dmesg`.
   - Verify GPIO pin functionality with a multimeter or test script.

## Dependency List (Pipfile)

Below are the main production dependencies:

- **GPIO Libraries**:
  - `gpiozero==2.0`
  - `pigpio==1.78`
  - `lgpio==0.2.2.0`

- **Web Framework**:
  - `flask==1.1.2`
  - `flask-cors==3.0.10`
  - `flask-socketio==5.3.4`

- **Serial Communication**:
  - `minimalmodbus==2.0.1`
  - `pyserial==3.5`

- **Image Processing**:
  - `opencv-python==4.9.0.80`

- **Utilities**:
  - `numpy==1.26.4`
  - `simple-websocket==1.0.0`
  - `bidict==0.23.1`

## Updating the Application

1. **Pull Latest Changes**:
   ```bash
   git pull origin main
   ```

2. **Install New Dependencies**:
   ```bash
   pipenv install
   ```

3. **Restart the Service**:
   ```bash
   sudo systemctl restart ffa-app.service
   ```

## Contribution Guidelines

1. Fork the repository.
2. Open a pull request with detailed descriptions of your changes.
3. Follow PEP8 coding standards.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
