# Estabilidad y calibración del peso (TLB / Modbus-RTU)

Diagnóstico y correcciones sobre el síntoma reportado: *"el peso varía mucho,
siempre se está moviendo y constantemente se descalibra"*.

Referencia: `Docs/TLB_protocols_manual_EN.pdf`, "TLB COMMUNICATION PROTOCOLS"
v1.16, sección MODBUS-RTU PROTOCOL (páginas 9-19).

Para la configuración y calibración del transmisor desde el teclado —mapa de
menús, parámetros, procedimiento paso a paso y troubleshooting— ver
[`tlb/README.md`](tlb/README.md).

---

## 1. Mapa de registros corregido

El manual (p. 11) numera los registros desde 40001. minimalmodbus los
direcciona desde 0, así que **hay que restar 40001**.

| Manual | Contenido | Dirección base-0 | Antes |
|---|---|---|---|
| 40006 | COMMAND | 5 | 5 ✅ |
| 40007 | STATUS | 6 | *no se leía* |
| 40008/40009 | GROSS H/L | 7 | 8 ❌ |
| 40010/40011 | NET H/L | 9 | 10 ❌ |
| 40012/40013 | PEAK H/L | 11 | — |
| 40014 | Divisiones / unidad | 13 | *no se leía* |
| 40037/40038 | Peso muestra calibración | 36 | 36 ✅ |

`read_long(10, byteorder=3)` leía en realidad **40011 (NET L) + 40012 (PEAK H)**.
Con `BYTEORDER_LITTLE_SWAP` el valor reconstruido es `reg[0] + reg[1] * 65536`,
o sea:

```
peso_mostrado = NET_L + PEAK_H * 65536
```

Coincidía con el peso real solo mientras **el peso y el pico registrado**
estuvieran por debajo de 65535 divisiones (6553.5 g con división 0.1). En
cuanto el pico superaba ese umbral — un golpe, la banda arrancando, alguien
apoyándose en la plataforma — `PEAK_H` pasaba a 1 y **todas las lecturas se
desplazaban +6553.6 de golpe**, permanentemente, hasta resetear el pico o
cortar la energía.

`tests/test_tlb_registers.py` reproduce el caso: el código viejo reportaba
7788.1 g donde el nuevo lee 1234.5 g.

## 2. Se lee el STATUS REGISTER (40007)

Manual p. 13. Antes se ignoraba por completo.

| Bit | Significado | Uso |
|---|---|---|
| 0 | Error de celda de carga | `faults` → log + chip rojo en la UI |
| 1 | Falla del conversor A/D | idem |
| 2 | Máximo excedido en 9 divisiones | idem |
| 3 | Bruto > 110% del fondo de escala | idem |
| 4/5 | Bruto / neto fuera de ±999999 | idem |
| 7 | Signo negativo del bruto | aplica el signo |
| 8 | Signo negativo del neto | aplica el signo |
| 10 | Modo neto | informativo |
| **11** | **Estabilidad del peso** | **habilita la captura** |
| 12 | Dentro de ±¼ división del cero | informativo |

**Signo:** los registros de peso llevan la *magnitud*; el signo va en el
status. Sin leerlo, un cero que derivaba a −0.4 g se mostraba como **+0.4 g**
— la deriva negativa se veía como positiva. `_apply_sign()` tolera además
firmware que ya envía complemento a dos.

**Estabilidad:** el transmisor ya sabe cuándo el peso se asentó. Antes la UI
lo adivinaba comparando lecturas consecutivas (`diff < 5%`), lo que declaraba
"estable" una deriva lenta e "inestable" un asentamiento rápido.

## 3. Escala leída del instrumento

El `/10` estaba hardcodeado. Ahora se lee la división del registro 40014
(tabla del manual p. 14) y se registra un `WARNING` si no es 0.1, que es lo
que asumen todas las muestras históricas. Si alguien cambia la división desde
el teclado del transmisor, ya no se reescalan las lecturas en silencio.

## 4. La tara ya no se pisa sola

`HomeView` y `BrokenBellyTest` emitían `set_tare` dentro de `mounted()`. El
comando 7 (SEMI-AUTOMATIC TARE) toma **lo que haya sobre la báscula en ese
instante** como nuevo cero. Cada vez que el operador volvía a la pantalla con
un pescado, agua o hielo encima, la tara quedaba mal — sin que nadie tocara la
calibración. Ahora la tara es siempre una acción explícita del operador con la
báscula vacía.

## 5. Calibración verificada

`remote_calibration()` sigue los pasos del manual p. 16 y ahora:

- espera estabilidad (bit 11) antes de cada punto;
- calcula el peso muestra en divisiones a partir del registro 40014 en lugar
  de escribir `0x2710` fijo;
- **verifica** que el instrumento haya puesto 40037/40038 en cero, que es como
  el manual indica el éxito. Antes, una calibración rechazada pasaba como
  exitosa;
- envía el **comando 99** al final para persistir en EEPROM;
- aborta con `TLBCalibrationError` ante cualquier falla del status.

Nuevas: `add_calibration_point()` (comando 106, hasta 8 puntos de
linealización) y `cancel_calibration()` (comando 104).

## 6. Comunicación

- `serial.timeout` fijado (antes el default de 0.05 s de minimalmodbus era
  apenas mayor que la trama: 17 bytes × 11 bits a 9600 8N2 ≈ 19.5 ms, más el
  retardo de respuesta del instrumento).
- Reintentos con back-off, y valor bueno anterior como respaldo ante un frame
  perdido.
- `update_net_status()` **ya se arranca** — antes era código muerto, nadie
  llamaba a `start_background_task`, y cada vista poleaba por su cuenta. Ahora
  el poller es la única fuente y `update_net` / `get_tension` responden desde
  caché, sin sumar un segundo lector al bus RS485.
- El loop nunca muere: antes una sola `NoResponseError` mataba el greenlet y
  el peso se congelaba en silencio por el resto de la sesión.
- El período de tensión pasó de 25 ms (más rápido de lo que el bus puede
  entregar a 9600 baudios) a 50 ms.
- `enter_to_tension_test` ahora llama a `net.enterToTensionTest()`; antes solo
  imprimía y el modo tensión nunca se activaba.

## Variables de entorno

| Variable | Default | Para qué |
|---|---|---|
| `TLB_PORT` | `/dev/ttyUSB0` | puerto serie |
| `TLB_BAUDRATE` | `9600` | subir a 38400 alivia mucho el bus |
| `TLB_TIMEOUT` | `0.2` | timeout de respuesta, segundos |
| `TLB_RETRIES` | `2` | reintentos por transacción |
| `TLB_RETRY_DELAY` | `0.02` | back-off entre reintentos |
| `TLB_CALIB_SAMPLE_GRAMS` | `1000.0` | peso patrón de la calibración guiada |
| `WEIGHT_POLL_INTERVAL` | `0.25` | período de muestreo de peso |
| `TENSION_POLL_INTERVAL` | `0.05` | período de muestreo de tensión |
| `SCALE_ERROR_BACKOFF` | `1.0` | espera tras un error de lectura |

## Herramienta de diagnóstico

```bash
python3 tools/scale_diagnostics.py --duration 600 --interval 0.2
python3 tools/scale_diagnostics.py --belly --duration 60
```

Vuelca gross, net, counts, status y fallas a CSV y al terminar clasifica el
comportamiento en **jitter** (ruido), **drift** (deriva del cero) o **saltos
discretos**. Marca explícitamente los saltos de 65536 counts.

Con la báscula **vacía** durante un turno mide la deriva del cero. Con un peso
patrón encima y sin tocarla mide la repetibilidad.

## Lo que el software no puede arreglar

Revisar en paralelo, en este orden:

1. **Filtro del transmisor.** Parámetro de filtro y de zero-tracking en el
   *manual del instrumento* (no está en `Docs/`, ahí solo hay el de protocolos
   y los del WTB). Un filtro muy bajo hace que el peso "baile".
2. **Humedad / condensación** en la caja de conexión o en la celda. Es la
   causa clásica de deriva lenta y continua en planta de pescado.
3. **Apantallado del cable de celda**: a tierra en un solo extremo, sin
   empalmes. Variador de frecuencia o el flash en el mismo tablero acoplan
   ruido al RS485 y a la celda.
4. **Vibración mecánica**: banda, motores, algo rozando la plataforma, cables
   tensando el plato.
5. **Temperatura**: el cuarto de deshielo mueve el cero de la celda.
6. **Transitorio del flash**: `ios.set_flash(True)` dispara justo antes de la
   captura. Si mete un transitorio en la alimentación, la lectura durante la
   captura es la peor del ciclo. El gate por bit 11 lo cubre parcialmente.

## Pendiente conocido

`main.py` importa `hardware` **antes** de `eventlet.monkey_patch()`. Por eso
el `_lock` de `TLB_MODBUS` es un lock de SO real, no verde, y pyserial quedó
con `select` sin parchear: cada transacción Modbus bloquea el hub de eventlet.
No causa la variación del peso, pero sí jitter en el intervalo de muestreo y
stalls del video durante las lecturas.

Mitigado en `TLB_MODBUS`: el lock se toma por transacción y **nunca** se
duerme con el lock tomado (eso sería un deadlock duro). Revertir el orden de
los imports requiere probar en la Pi que `gpiozero`/`lgpio` sigan funcionando.
