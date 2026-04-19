from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentctl import bootstrap


REPO_ROOT = Path(__file__).resolve().parents[2]


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_from_local_source_installs_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / ".codex"
            code = bootstrap.main(
                [
                    "bootstrap",
                    "--source-root",
                    str(REPO_ROOT),
                    "--codex-home",
                    str(target),
                    "--skip-post-checks",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue((target / "agentctl" / "agentctl.py").exists())
            self.assertTrue((target / "skills" / "test-skill" / "SKILL.md").exists())

    @mock.patch("agentctl.bootstrap.subprocess.run")
    def test_wrapper_delegates_to_installed_bundle(self, run_mock: mock.Mock) -> None:
        run_mock.return_value = mock.Mock(returncode=0)
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_home = Path(temp_dir) / ".codex"
            bundle_entry = codex_home / "agentctl" / "agentctl.py"
            bundle_entry.parent.mkdir(parents=True, exist_ok=True)
            bundle_entry.write_text("print('ok')\n", encoding="utf-8")

            with mock.patch.dict("os.environ", {"CODEX_HOME": str(codex_home)}):
                code = bootstrap.main(["doctor"])

            self.assertEqual(code, 0)
            delegated = run_mock.call_args.args[0]
            self.assertEqual(delegated[0], sys.executable)
            self.assertTrue(str(delegated[1]).replace("\\", "/").endswith("/agentctl/agentctl.py"))
            self.assertEqual(delegated[2:], ["doctor"])

    def test_wrapper_requires_bootstrap_when_bundle_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict("os.environ", {"CODEX_HOME": str(Path(temp_dir) / ".codex")}):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    code = bootstrap.main(["doctor"])
            self.assertEqual(code, 2)
            self.assertIn("Run `loopsmith bootstrap` first", stderr.getvalue())
            self.assertIn("`agentctl bootstrap`", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
