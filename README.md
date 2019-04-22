# Actcast Application Framework for Python

This package provides a Python API for developing Actcast apps.

## Installation

for Raspberry Pi

```
sudo apt-get update
sudo apt-get install -y python3-pil python3-setuptools python3-wheel picamera
pip3 install .
```

## Usage

Construct your application with a task parallel model

* Application
    * `actfw.Application` : Main application
* Workers
    * `actfw.task.Producer` : Task generator
        * `actfw.PiCameraCapture` : Task generator which generate capture image as task
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

Please, see and try examples.

## Example

* `example/hello` : The most simple application example
    * Use HDMI display as 640x480 area
    * Capture 320x240 RGB image
    * Draw "Hello, Actcast!" text
    * Display it as 640x480 image (with x2 scaling)
    * Notice message for each frame
    * Support application setting
    * Support application heartbeat
    * Support "Take Photo" command
* `example/grayscale` : Next level application example
    * Use HDMI display as 640x480 area
    * Capture 320x240 RGB image
    * Convert it to grayscale
    * Display it as 640x480 image (with x2 scaling)
    * Notice message for each frame
    * Support application setting
    * Support application heartbeat
    * Support "Take Photo" command
* `example/parallel_grayscale` : Paralell processing application example
    * Use HDMI display as 640x480 area
    * Capture 320x240 RGB image
    * Convert it to grayscale
        * There exists 2 converter task
        * Round-robin task scheduling
    * Display it as 640x480 image (with x2 scaling)
    * Notice message for each frame
        * Show which converter processes image
    * Support application setting
    * Support application heartbeat
    * Support "Take Photo" command
