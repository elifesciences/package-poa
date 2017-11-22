import unittest
import time
from packagepoa import transform

class TestTransform(unittest.TestCase):

    def setUp(self):
        pass

    def test_dummy(self):
        self.assertEqual(transform.dummy(), None)


if __name__ == '__main__':
    unittest.main()
