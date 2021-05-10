# Changelog

## 2.0.0 (2021-XX-XX)

- Stop exporting `actfw_core.__version__`.
- (Breaking change; for actfw-* developers) Changed the types of `Pipe.in_queues` and `Pipe.out_queues`: `list[Queue[T]]` -> `list[_PadOut[T]]`/`list[_PadIn[T]]`.
- (Breaking change; for actfw-* developers) Deleted the method `Frame._update()`.
- (Breaking change; for actfw-* developers) Inheritance of `Task` classes are changed.
  - All grandchildren of `Task` become direct children of it.
  - `Consumer` and `Producer` were chirldren of `Pipe`, but they are not now.  They are children of `Task`.
  - Use mixins and interfaces for implementation of children of `Task`.
- Added methods `Task.stop()` and `Task.run()`.  (The later was a method of `Pipe`.)
- Added type annotations.
