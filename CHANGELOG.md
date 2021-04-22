# Changelog

## 2.0.0 (2021-XX-XX)

- Stop exporting `actfw_core.__version__`.
- (Breaking change; for actfw-* developers) Changed the types of `Pipe.in_queues` and `Pipe.out_queues`: `list[Queue[T]]` -> `list[_PadOut[T]]`/`list[_PadIn[T]]`.
- (Breaking change; for actfw-* developers) Deleted the method `Frame._update()`.
- (Breaking change; for actfw-* developers) Inheritance of `Task` classes are changed.  For example, `Consumer` and `Producer` were chirldren of `Pipe`, but they are not now.
