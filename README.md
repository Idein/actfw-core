# actfw-core

Core components of actfw, a framework for Actcast Application written in Python.
actfw-core is intended to be independent of any specific device.

## Installation

```console
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil 
sudo apt-get install -y libv4l-0 libv4lconvert0  # if using `V4LCameraCapture`
pip3 install actfw-core
```

## Document

* [API References](https://idein.github.io/actfw-core/latest/)

## Usage

Construct your application with a task parallel model

* Application
  * `actfw_core.Application` : Main application
* Workers
  * `actfw_core.task.Producer` : Task generator
    * `actfw_core.capture.V4LCameraCapture` : Generate UVC camera capture image
  * `actfw_core.task.Pipe` : Task to Task converter
  * `actfw_core.task.Consumer` : Task terminator

Each worker is executed in parallel.

User should

* Define subclass of `Producer/Pipe/Consumer`

```python
class MyPipe(actfw_core.task.Pipe):
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
app = actfw_core.Application()
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
pip3 install poetry
poetry install
```

### Running tests

```console
poetry run nose2 -v
```

### Releasing package & API doc

CI will automatically do.
Follow the following branch/tag rules.

1. Make changes for next version in `master` branch (via pull-requests).
2. Make a PR that updates version in `pyproject.toml` and merge it to `master` branch.
3. Create Git tag from `master` branch's HEAD named `release-<New version>`. E.g. `release-1.4.0`.
4. Then CI will build/upload package to PyPI & API doc to GitHub Pages.
