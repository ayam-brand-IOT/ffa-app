# Flash Capture Tuning

`ffa-app` synchronizes flash and image capture by turning the flash on, waiting for fresh camera frames, and then analyzing the selected frame.

These variables control that timing:

```env
FLASH_SETTLE_SECONDS=0.03
FLASH_FRAME_SKIP=2
FLASH_FRAME_TIMEOUT=0.35
```

## Variables

### `FLASH_SETTLE_SECONDS`

Small delay after turning the flash on, before waiting for camera frames.

- Increase it if the flash needs a little time to reach full brightness.
- Decrease it to reduce capture latency.
- Recommended range: `0` to `0.08`.

Examples:

```env
FLASH_SETTLE_SECONDS=0
FLASH_SETTLE_SECONDS=0.03
FLASH_SETTLE_SECONDS=0.06
```

### `FLASH_FRAME_SKIP`

Number of new camera frames to wait for after the flash turns on.

This is usually the most important tuning value.

- Increase it if the image is dark or looks like it was captured before the flash fully illuminated the fish.
- Decrease it if the image is well lit but capture feels delayed.
- Recommended range: `1` to `4`.

Examples:

```env
FLASH_FRAME_SKIP=1  # fastest
FLASH_FRAME_SKIP=2  # balanced default
FLASH_FRAME_SKIP=3  # safer if illumination arrives late
```

### `FLASH_FRAME_TIMEOUT`

Maximum time to wait for the requested fresh frames before falling back to the latest available frame.

- Increase it if the camera sometimes takes longer to deliver frames.
- Decrease it if you want to cap capture latency more aggressively.
- Recommended range: `0.20` to `0.60`.

Examples:

```env
FLASH_FRAME_TIMEOUT=0.25
FLASH_FRAME_TIMEOUT=0.35
FLASH_FRAME_TIMEOUT=0.50
```

## Tuning Recipe

Start with:

```env
FLASH_SETTLE_SECONDS=0.03
FLASH_FRAME_SKIP=2
FLASH_FRAME_TIMEOUT=0.35
```

If the image is dark or does not show enough flash:

```env
FLASH_FRAME_SKIP=3
```

If it is still dark:

```env
FLASH_SETTLE_SECONDS=0.05
```

If the image is well lit but capture feels slow:

```env
FLASH_FRAME_SKIP=1
FLASH_SETTLE_SECONDS=0
```

If capture is inconsistent, working sometimes but failing other times:

```env
FLASH_FRAME_TIMEOUT=0.50
```

Recommended first real-machine test:

```env
FLASH_SETTLE_SECONDS=0.02
FLASH_FRAME_SKIP=2
FLASH_FRAME_TIMEOUT=0.40
```

## Where to Configure

For Docker deployments, set these values in `docker-compose.yaml` under the `ffa-app` service:

```yaml
environment:
  - FLASH_SETTLE_SECONDS=0.03
  - FLASH_FRAME_SKIP=2
  - FLASH_FRAME_TIMEOUT=0.35
```

For local runs without Docker:

```bash
FLASH_SETTLE_SECONDS=0.03 FLASH_FRAME_SKIP=2 FLASH_FRAME_TIMEOUT=0.35 python main.py
```
