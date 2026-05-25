import unittest
from unittest.mock import patch

from freecad_mcp_workbench.controller import _available_tools_message
from freecad_mcp_workbench.server import find_available_port


class ServerTests(unittest.TestCase):
    def test_find_available_port_skips_conflicts(self):
        attempts = []

        class FakeSocket:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def setsockopt(self, *_args):
                pass

            def bind(self, address):
                attempts.append(address[1])
                if len(attempts) == 1:
                    raise OSError("in use")

        with patch("freecad_mcp_workbench.server.socket.socket", return_value=FakeSocket()):
            selected = find_available_port("127.0.0.1", 8765, attempts=2)

        self.assertEqual(selected, 8766)
        self.assertEqual(attempts, [8765, 8766])

    def test_available_tools_message_includes_registered_tools(self):
        message = _available_tools_message()

        self.assertIn("MCP available tools (18):", message)
        self.assertIn("  - boolean_operation", message)


if __name__ == "__main__":
    unittest.main()
