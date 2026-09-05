#!/usr/bin/env python3
"""Offline checks for payload template rendering."""

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).with_name("generatePayloads.py")
SPEC = importlib.util.spec_from_file_location("generatePayloads", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RenderCallbackTests(unittest.TestCase):
    def test_updates_direct_profile_only(self):
        config = {
            "filename": "sample.bin",
            "c2_profiles": [
                {"c2_profile_is_p2p": False, "c2_profile_parameters": {}},
                {"c2_profile_is_p2p": True, "c2_profile_parameters": {"callback_host": "keep"}},
            ],
        }
        self.assertEqual(MODULE.render_callback(config, "http://10.10.10.10", 8080), 1)
        self.assertEqual(config["c2_profiles"][0]["c2_profile_parameters"]["callback_host"], "http://10.10.10.10")
        self.assertEqual(config["c2_profiles"][0]["c2_profile_parameters"]["callback_port"], 8080)
        self.assertEqual(config["c2_profiles"][1]["c2_profile_parameters"]["callback_host"], "keep")

    def test_tcp_renderer_updates_the_listener_port_and_filename(self):
        config = {"filename": "apollo-tcp.bin", "c2_profiles": [{"c2_profile": "tcp", "c2_profile_parameters": {"port": "1"}}]}
        MODULE.render_tcp_port(config, 47001)
        self.assertEqual(config["c2_profiles"][0]["c2_profile_parameters"]["port"], "47001")
        self.assertEqual(config["filename"], "apollo-tcp-47001.bin")


if __name__ == "__main__":
    unittest.main()
