import sqlite3
from queue import Queue
from threading import Thread

_commit = object()
_close_connection = object()


class QueueDB(Thread):
    def __init__(self, path: str):
        super().__init__()

        self.path = path
        self.queue = Queue()

    def run(self) -> None:
        connection = sqlite3.connect(self.path, check_same_thread=True)
        cursor = connection.cursor()

        while True:
            statement, response_queue = self.queue.get()

            if statement is _commit:
                connection.commit()

            elif statement is _close_connection:
                connection.close()
                break

            else:
                cursor.execute(statement)

                if response_queue is not None:
                    responses = cursor.fetchall()
                    response_queue.put(responses)

    def execute(self, statement: str):
        self.queue.put((statement, None))

    def close_connection(self):
        self.queue.put((_close_connection, None))

    def commit(self):
        self.queue.put((_commit, None))

    def fetch(self, statement: str):
        response_queue = Queue()

        self.queue.put((statement, response_queue))

        responses = response_queue.get()
        return responses
