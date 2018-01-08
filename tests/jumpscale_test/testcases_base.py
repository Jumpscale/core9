import time, signal, logging
from datetime import timedelta
from unittest import TestCase
from nose.tools import TimeExpired


class TestcasesBase(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setUp(self):
        self._testID = self._testMethodName
        self._startTime = time.time()

        def timeout_handler(signum, frame):
            raise TimeExpired('Timeout expired before end of test %s' % self._testID)

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(540)

    def tearDown(self):
        pass
