# LibcameraCapture Example

## Requirement

- Raspberry Pi OS (bookworm) 64bit
- Raspberry Pi Camera Module


## How to run

In raspberrypi:

```bash
$ sudo apt update
$ sudo apt install python3-libcamera
$ python3 -m venv --system-site-packages venv
$ source venv/bin/activate
$ pip3 install numpy actfw-raspberrypi
$ python3 main.py
```

## White balance

The default is libcamera's automatic white balance, using its tuning file.
To use grey-world white balance instead:

```python
import libcamera as libcam
from actfw_core.libcamera_capture import Auto, AwbGreyWorld, AwbManual, LibcameraCapture

cap = LibcameraCapture(
    (1280, 960),
    libcam.PixelFormat("BGR888"),
    awb=AwbGreyWorld(gain_r=1.6, gain_b=1.6, k=0.45),
)

# These may also be called while the capture task is running.
cap.set_awb_settings(AwbManual(1.04, 2.30))
cap.set_awb_settings(libcam.controls.AwbModeEnum.Indoor)
cap.set_awb_settings(Auto.AUTO)
cap.set_awb_settings(AwbGreyWorld())

status = cap.awb_status()  # None until the first completed frame
if status is not None:
    print(status.gain_r, status.gain_b, status.colour_temperature, status.lux)
```

`AwbGreyWorld()` starts with red and blue gains of 1.6 and damping exponent
`k=0.45`. The initial gains and `k`
can be changed through its constructor. It samples the output image every eight
pixels in each direction and updates gains only after metadata confirms the
previous target was applied. The correction is
`applied_gain * (sum_g / (sum_channel + 1)) ** k`, limited to gains of 0.5–8.0.
`k` must be greater than zero and at most one; smaller values adjust more gradually.
The initial gains must also be within 0.5–8.0.

`awb_status()` returns an immutable snapshot of the most recent frame's applied
gains, colour temperature (kelvin), and illuminance (lux). Missing metadata fields
are `None`. Requested settings can take several frames to appear in the status.
Setting changes are queued and taken by the capture thread at camera start or
at the beginning of the next completed-frame processing. If several changes are
waiting, the latest takes precedence. A change made during frame processing waits
until the next frame, so it does not interrupt the current calculation or requeue.
Switching to `AwbGreyWorld` restarts it from the supplied initial gains when the
queued settings are taken.

These controls use the camera's existing tuning; they do not change the tuning
file or drivers. Grey-world estimates depend on the scene and may introduce a
colour cast when one colour dominates the image.

