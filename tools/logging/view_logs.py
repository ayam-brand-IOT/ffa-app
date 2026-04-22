#!/usr/bin/env python3
"""
Script para visualizar y analizar los logs de la aplicación FFA
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT_DIR / "logs"
LOG_FILE = LOGS_DIR / "ffa_app_events.log"


def read_logs(
    log_file: str = str(LOG_FILE),
    filter_status: Optional[str] = None,
    filter_etapa: Optional[str] = None,
    limit: Optional[int] = None
):
    """
    Lee y filtra los logs
    
    Args:
        log_file: Ruta al archivo de log
        filter_status: Filtrar por status (SUCCESS, ERROR, WARNING, INFO)
        filter_etapa: Filtrar por etapa (CAPTURE, ANALYSIS, CONFIG_UPDATE, etc.)
        limit: Límite de registros a mostrar
    """
    if not Path(log_file).exists():
        print(f"❌ Archivo de log no encontrado: {log_file}")
        return
    
    count = 0
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                event = json.loads(line)
                
                # Aplicar filtros
                if filter_status and event.get('status') != filter_status:
                    continue
                
                if filter_etapa and event.get('etapa') != filter_etapa:
                    continue
                
                # Mostrar evento
                print_event(event)
                
                count += 1
                if limit and count >= limit:
                    break
                    
            except json.JSONDecodeError as e:
                print(f"⚠️  Error parseando línea: {line[:50]}...")


def print_event(event: dict):
    """Imprime un evento de forma legible"""
    timestamp = event.get('timestamp', 'N/A')
    etapa = event.get('etapa', 'N/A')
    status = event.get('status', 'N/A')
    
    # Emoji según status
    status_emoji = {
        'SUCCESS': '✅',
        'ERROR': '❌',
        'WARNING': '⚠️',
        'INFO': 'ℹ️'
    }.get(status, '•')
    
    print(f"\n{status_emoji} [{timestamp}] {etapa} - {status}")
    
    # Información adicional
    if event.get('lote_id'):
        print(f"   📦 Lote: {event['lote_id']}")
    
    if event.get('proveedor_id'):
        print(f"   🏢 Proveedor: {event['proveedor_id']}")
    
    if event.get('fish_params'):
        print(f"   🐟 Fish Params: {json.dumps(event['fish_params'], indent=6)}")
    
    if event.get('vision_params'):
        print(f"   👁️  Vision Params: {json.dumps(event['vision_params'], indent=6)}")
    
    if event.get('error_code'):
        print(f"   🔴 Error Code: {event['error_code']}")
    
    if event.get('error_msg'):
        print(f"   💬 Error Msg: {event['error_msg']}")
    
    if event.get('additional_data'):
        print(f"   📊 Additional Data: {json.dumps(event['additional_data'], indent=6)}")
    
    print(f"   📱 Version: {event.get('version_app', 'N/A')}")


def get_statistics(log_file: str = str(LOG_FILE)):
    """Muestra estadísticas de los logs"""
    if not Path(log_file).exists():
        print(f"❌ Archivo de log no encontrado: {log_file}")
        return
    
    stats = {
        'total': 0,
        'by_status': {},
        'by_etapa': {},
        'errors': []
    }
    
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                event = json.loads(line)
                stats['total'] += 1
                
                # Contar por status
                status = event.get('status', 'UNKNOWN')
                stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
                
                # Contar por etapa
                etapa = event.get('etapa', 'UNKNOWN')
                stats['by_etapa'][etapa] = stats['by_etapa'].get(etapa, 0) + 1
                
                # Guardar errores
                if status == 'ERROR':
                    stats['errors'].append({
                        'timestamp': event.get('timestamp'),
                        'etapa': etapa,
                        'error_code': event.get('error_code'),
                        'error_msg': event.get('error_msg')
                    })
                    
            except json.JSONDecodeError:
                continue
    
    # Mostrar estadísticas
    print("\n" + "="*60)
    print("📊 ESTADÍSTICAS DE LOGS")
    print("="*60)
    print(f"\n📈 Total de eventos: {stats['total']}")
    
    print("\n📊 Por Status:")
    for status, count in sorted(stats['by_status'].items()):
        percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
        emoji = {'SUCCESS': '✅', 'ERROR': '❌', 'WARNING': '⚠️', 'INFO': 'ℹ️'}.get(status, '•')
        print(f"   {emoji} {status}: {count} ({percentage:.1f}%)")
    
    print("\n📊 Por Etapa:")
    for etapa, count in sorted(stats['by_etapa'].items()):
        percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"   • {etapa}: {count} ({percentage:.1f}%)")
    
    if stats['errors']:
        print(f"\n❌ Últimos errores ({len(stats['errors'])} total):")
        for error in stats['errors'][-5:]:  # Últimos 5 errores
            print(f"\n   [{error['timestamp']}]")
            print(f"   Etapa: {error['etapa']}")
            print(f"   Code: {error['error_code']}")
            print(f"   Msg: {error['error_msg']}")
    
    print("\n" + "="*60)


def main():
    """Función principal"""
    if len(sys.argv) == 1:
        print("📋 Mostrando todos los logs (últimos 50):")
        read_logs(limit=50)
        print("\n")
        get_statistics()
    elif sys.argv[1] == 'stats':
        get_statistics()
    elif sys.argv[1] == 'errors':
        print("❌ Mostrando solo errores:")
        read_logs(filter_status='ERROR')
    elif sys.argv[1] == 'success':
        print("✅ Mostrando solo eventos exitosos:")
        read_logs(filter_status='SUCCESS')
    elif sys.argv[1] == 'capture':
        print("📸 Mostrando eventos de captura:")
        read_logs(filter_etapa='CAPTURE')
    elif sys.argv[1] == 'config':
        print("⚙️  Mostrando eventos de configuración:")
        read_logs(filter_etapa='CONFIG_UPDATE')
    elif sys.argv[1] == 'calibration':
        print("🎯 Mostrando eventos de calibración:")
        read_logs(filter_etapa='CALIBRATION')
    elif sys.argv[1] == 'system':
        print("💻 Mostrando eventos del sistema:")
        read_logs(filter_etapa='SYSTEM')
    elif sys.argv[1] == 'all':
        print("📋 Mostrando todos los logs:")
        read_logs()
    else:
        print("""
🔍 Uso del script de visualización de logs:

    python tools/logging/view_logs.py               # Últimos 50 logs + estadísticas
    python tools/logging/view_logs.py all           # Todos los logs
    python tools/logging/view_logs.py stats         # Solo estadísticas
    python tools/logging/view_logs.py errors        # Solo errores
    python tools/logging/view_logs.py success       # Solo eventos exitosos
    python tools/logging/view_logs.py capture       # Solo eventos de captura
    python tools/logging/view_logs.py config        # Solo eventos de configuración
    python tools/logging/view_logs.py calibration   # Solo eventos de calibración
    python tools/logging/view_logs.py system        # Solo eventos del sistema
        """)


if __name__ == '__main__':
    main()
