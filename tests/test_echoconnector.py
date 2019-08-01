# not possible that way

import unittest
from echo2rasa.echoconnector import te


class TestEchoConnector(unittest.TestCase):

    def test_connector_name(self):
        # connector = EchoConnector(None)
        self.assertEqual(connector.name, "echo")


if __name__ == '__main__':
    unittest.main()
