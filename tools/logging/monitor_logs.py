#!/usr/bin/env python3
"""
Monitor de logs en tiempo real
Muestra los eventos según llegan, con colores y formato
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT_DIR / "logs"
LOG_FILE = LOGS_DIR / "ffa_app_events.log"

# Colores ANSI
COLORS = {
    'RESET': '\033[0m',
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'WHITE': '\033[97m',
    'BOLD': '\033[1m'
}

def colorize(text, color):
    """Agrega color al texto"""
    return f"{COLORS.get(color, '')}{text}{COLORS['RESET']}"

def get_status_emoji_color(status):
    """Retorna emoji y color según status"""
    mapping = {
        'SUCCESS': ('✅', 'GREEN'),
        'ERROR': ('❌', 'RED'),
        'WARNING': ('⚠️', 'YELLOW'),
        'INFO': ('ℹ️', 'CYAN')
    }
    return mapping.get(status, ('•', 'WHITE'))

def print_event_compact(event):
    """Imprime evento en formato compacto"""
    timestamp = event.get('timestamp', 'N/A')
    etapa = event.get('etapa', 'N/A')
    status = event.get('status', 'N/A')
    
    emoji, color = get_status_emoji_color(status)
    
    # Línea principal
    time_str = timestamp.split('T')[1][:8] if 'T' in timestamp else timestamp
    line = f"{emoji} [{colorize(time_str, 'BLUE')}] {colorize(etapa, 'MAGENTA')} - {colorize(status, color)}"
    
    # Información adicional en la misma línea
    parts = []
    if event.get('lote_id'):
        parts.append(f"📦 {event['lote_id']}")
    
    if event.get('error_msg'):
        parts.append(f"💬 {event['error_msg'][:50]}...")
    elif event.get('additional_data', {}).get('description'):
        parts.append(f"{event['additional_data']['description'][:50]}")
    
    if parts:
        line += " | " + " | ".join(parts)
    
    print(line)

def monitor_logs(follow=True, filter_status=None, compact=True):
    """
    Monitorea el archivo de logs
    
    Args:
        follow: Si True, hace tail -f (sigue el archivo)
        filter_status: Filtrar por status específico
        compact: Si True, usa formato compacto
    """
    if not LOG_FILE.exists():
        print(colorize(f"❌ Archivo de log no encontrado: {LOG_FILE}", 'RED'))
        print(colorize("💡 Ejecuta la aplicación o test_logging.py primero", 'YELLOW'))
        return
    
    # Header
    print("\n" + "="*80)
    print(colorize("🔍 MONITOR DE LOGS FFA", 'BOLD'))
    print("="*80)
    if filter_status:
        print(colorize(f"📌 Filtrando por: {filter_status}", 'YELLOW'))
    print(colorize("💡 Presiona Ctrl+C para detener\n", 'CYAN'))
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            # Ir al final del archivo
            if follow:
                f.seek(0, 2)  # Ir al final
            
            while True:
                line = f.readline()
                
                if not line:
                    if follow:
                        time.sleep(0.1)
                        continue
                    else:
                        break
                
                if not line.strip():
                    continue
                
                try:
                    event = json.loads(line)
                    
                    # Aplicar filtro
                    if filter_status and event.get('status') != filter_status:
                        continue
                    
                    # Mostrar evento
                    if compact:
                        print_event_compact(event)
                    else:
                        # Formato detallado
                        print("\n" + "-"*80)
                        print(json.dumps(event, indent=2, ensure_ascii=False))
                    
                    sys.stdout.flush()
                    
                except json.JSONDecodeError as e:
                    print(colorize(f"⚠️  Error parseando línea: {line[:50]}...", 'YELLOW'))
                    
    except KeyboardInterrupt:
        print(colorize("\n\n👋 Monitor detenido", 'CYAN'))
    except Exception as e:
        print(colorize(f"\n❌ Error: {e}", 'RED'))


def main():
    """Función principal"""
    if len(sys.argv) == 1:
        # Monitor en tiempo real con formato compacto
        monitor_logs(follow=True, compact=True)
    elif sys.argv[1] == 'history':
        # Mostrar historial (no seguir)
        monitor_logs(follow=False, compact=True)
    elif sys.argv[1] == 'errors':
        # Solo errores en tiempo real
        monitor_logs(follow=True, filter_status='ERROR', compact=True)
    elif sys.argv[1] == 'success':
        # Solo success en tiempo real
        monitor_logs(follow=True, filter_status='SUCCESS', compact=True)
    elif sys.argv[1] == 'detailed':
        # Formato detallado
        monitor_logs(follow=True, compact=False)
    else:
        print("""
🔍 Monitor de logs en tiempo real

Uso:
    python tools/logging/monitor_logs.py              # Monitor en tiempo real (compacto)
    python tools/logging/monitor_logs.py history      # Ver historial sin seguir
    python tools/logging/monitor_logs.py errors       # Solo errores en tiempo real
    python tools/logging/monitor_logs.py success      # Solo eventos exitosos
    python tools/logging/monitor_logs.py detailed     # Formato detallado (JSON completo)

Ejemplos:
    # Monitor básico
    python tools/logging/monitor_logs.py
    
    # Ver solo errores conforme ocurren
    python tools/logging/monitor_logs.py errors
    
    # Ver historial completo
    python tools/logging/monitor_logs.py history

💡 Presiona Ctrl+C para detener el monitor
        """)


if __name__ == '__main__':
    main()
