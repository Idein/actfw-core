# Changelog

## Unreleased

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
