# Actcast Application Framework for Python

This package provides a Python API for developing Actcast apps.

## Installation

```console
sudo apt-get update
sudo apt-get install -y python3-pil python3-pip
pip3 install actfw-core
```

## Document

* [API References](https://idein.github.io/actfw-docs/latest/)

## Usage

Construct your application with a task parallel model

* Application
  * `actfw.Application` : Main application
* Workers
  * `actfw.task.Producer` : Task generator
    * `actfw.capture.V4LCameraCapture` : Generate UVC camera capture image
  * `actfw.task.Pipe` : Task to Task converter
  * `actfw.task.Consumer` : Task terminator

Each worker is executed in parallel.

User should

* Define subclass of `Producer/Pipe/Consumer`

```python
class MyPipe(actfw.task.Pipe):
    def proc(self, i):
        ...
```

* Connect defined worker objects

```python
p  = MyProducer()
f1 = MyPipe()
f2 = MyPipe()
c  = MyConsumer()
p.connect(f1)
f1.connect(f2)
f2.connect(c)
```

* Register to `Application`

```python
app = actfw.Application()
app.register_task(p)
app.register_task(f1)
app.register_task(f2)
app.register_task(c)
```

* Execute application

```python
app.run()
```

## Development Guide

### Installation of dev requirements

```console
pip3 install pipenv
pipenv install --dev -e .
```

### Uploading package to PyPI

See <https://packaging.python.org/tutorials/packaging-projects/> first.

```console
pipenv run python setup.py sdist bdist_wheel
pipenv run python -m twine upload --repository pypi dist/*
```
