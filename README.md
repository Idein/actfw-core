# Actcast Application Framework for Python

This package provides a Python API for developing Actcast apps.

## Installation

for Raspberry Pi

```
sudo apt-get update
sudo apt-get install -y python3-pil python3-setuptools python3-wheel
pip3 install .
```

## Document

* [API References](https://idein.github.io/actfw-docs/latest/)

## Usage

Construct your application with a task parallel model

* Application
    * `actfw.Application` : Main application
* Workers
    * `actfw.task.Producer` : Task generator
        * `actfw.capture.PiCameraCapture` : Generate CSI camera capture image
        * `actfw.capture.V4LCameraCapture` : Generate UVC camera capture image
    * `actfw.task.Pipe` : Task to Task converter
    * `actfw.task.Consumer` : Task terminator

Each worker is executed in parallel.

User should

* Define subclass of `Producer/Pipe/Consumer`
~~~~python
class MyPipe(actfw.task.Pipe):
    def proc(self, i):
        ...
~~~~
* Connect defined worker objects
~~~~python
p  = MyProducer()
f1 = MyPipe()
f2 = MyPipe()
c  = MyConsumer()
p.connect(f1)
f1.connect(f2)
f2.connect(c)
~~~~
* Register to `Application`
~~~~python
app = actfw.Application()
app.register_task(p)
app.register_task(f1)
app.register_task(f2)
app.register_task(c)
~~~~
* Execute application
~~~~python
app.run()
~~~~
