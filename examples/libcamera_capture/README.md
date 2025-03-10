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


