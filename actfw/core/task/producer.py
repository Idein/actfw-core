from .pipe import Pipe


class Producer(Pipe):

    """Producer Task."""

    def __init__(self):
        """
        """
        super(Producer, self).__init__()

    def _add_in_queue(self, q):
        raise NotImplementedError('This is producer')

    def _inlet(self):
        while self._is_running():
            yield ()
