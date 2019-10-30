import unittest
from unittest.mock import patch, call
import multiecho.combination

class MyUnitTest(unittest.TestCase):

    def test_load_me_data(self):
        with patch('multiecho.combination.logger') as log_mock:
            multiecho.combination.load_me_data("", TEs=None)
            calls = [
                call.info('Loading: []'),
                call.info('Echotimes: []')
            ]
            log_mock.assert_has_calls(calls)

if __name__ == '__main__':
    unittest.main()
