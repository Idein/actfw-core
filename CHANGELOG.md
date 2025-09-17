# Changelog

## Unreleased

## 2.14.0 (2025-09-17)

- Add `cleanup` method to Producer, Pipe and Consumer

## 2.13.0 (2025-06-04)

- Change default value of framerate in `LibcameraCapture` to 30 from None.

## 2.12.3 (2025-05-27)

- Add module comment and assertion to `LibcameraCapture`.

## 2.12.2 (2025-05-01)

- Fix CI to generate docs of `LibcameraCapture`.

## 2.12.1 (2025-05-01)

- Add docstring to `LibcameraCapture`.

## 2.12.0 (2025-04-30)

- Add `orientation: libcamera.Orientation` to `LibcameraCapture`.
- Add `framerate: Optional[int]` to `LibcameraCapture`.

## 2.11.0 (2025-03-10)

- Add `LibcameraCapture` which wraps libcamera.

## 2.10.0 (2025-01-21)

- Add `LocalVideoServer` which can cast mjpeg streaming over http.

## 2.9.0 (2024-12-02)

- Add support autofocus function for `imx708` sensor.

## 2.8.0 (2024-11-18)

- Add support for the `imx708` sensor to `UnicamIspCapture`. Note: Autofocus is not supported.

## 2.7.0 (2024-09-17)

- Add `set_exposure_settings` to `UnicamIspCapture`.

## 2.6.0 (2024-09-05)

- Fix a bug: query non image_source devices for capabilities.

## 2.5.0 (2024-08-23)

- Add support for the `imx708_wide` sensor to `UnicamIspCapture`. Note: Autofocus is not supported.
- Add `AppSettings` class and `SettingSchema` class to `actfw_core.application`.

## 2.4.0 (2024-01-23)

- upgrade pillow version for python>=3.11 environment

## 2.3.0 (2023-09-12)

- Add `find_usb_camera_device` and `find_csi_camera_device` functions to `actfw_core.system`.
- Add `vflip` and `hflip` parameters to `UnicamIspCapture`.

## 2.2.1 (2023-07-13)

- Add retry logic to open v4l2 Video device.

## 2.2.0 (2022-11-04)

- Fix a bug: actfw doesn't raise assertion error when it is stopped before `update_image` is called.
- Add functions in `actfw_core.system` in order to get environment variables available in the container.
- `V4LCameraCapture` supports USB camera in bullseye.

## 2.2.0a0 (2022-03-14)

- upgrade pillow version for python>=3.8 environment

## 2.1.1 (2021-09-01)

- Improve efficeincy of `V4LCameraCapture`.
  - Reduce the number of calls of `v4l2_mmap` and `v4l2_munmap`.
- `V4LCameraCapture` now correctly works in 64-bit linux environments.
- Fixed a bug: In 2.1.0, `actfw_core.CommandServer` failed to response to Take Photo command.

## 2.1.0 (2021-08-30)

- Support a new actcast agent feature by `actfw_core.ServiceClient`.

## 2.0.0 (2021-05-18)

- Stop exporting `actfw_core.__version__`.
- (Breaking change; for actfw-* developers) Changed the types of `Pipe.in_queues` and `Pipe.out_queues`: `list[Queue[T]]` -> `list[_PadOut[T]]`/`list[_PadIn[T]]`.
- (Breaking change; for actfw-* developers) Deleted the method `Frame._update()`.
- (Breaking change; for actfw-* developers) Inheritance of `Task` classes are changed.
  - All grandchildren of `Task` become direct children of it.
  - `Consumer` and `Producer` were chirldren of `Pipe`, but they are not now.  They are children of `Task`.
  - Use mixins and interfaces for implementation of children of `Task`.
- Added methods `Task.stop()` and `Task.run()`.  (The later was a method of `Pipe`.)
- Added type annotations.
