import sys
import unittest
from importlib import import_module
from pathlib import Path

MCP_DIR = Path(__file__).resolve().parents[1]


# tomllibはPython 3.11以降。CIはPython 3.12で実行する
@unittest.skipIf(sys.version_info < (3, 11), "tomllibはPython 3.11以降")
class PyprojectTest(unittest.TestCase):
    def setUp(self):
        import tomllib

        self.pyproject = tomllib.loads((MCP_DIR / "pyproject.toml").read_text(encoding="utf-8"))

    def test_command_points_to_a_callable(self):
        """uvxや、インストール後のsubekashi-mcpが起動するmainが実在する"""
        scripts = self.pyproject["project"]["scripts"]
        self.assertEqual(list(scripts), ["subekashi-mcp"])
        module_name, attribute = scripts["subekashi-mcp"].split(":")
        self.assertTrue(callable(getattr(import_module(module_name), attribute)))

    def test_dependencies_match_requirements_txt(self):
        """CIや開発で入れるrequirements.txtと、パッケージが要求する依存（SDKの版）が食い違わない"""
        lines = (MCP_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()
        requirements = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
        self.assertEqual(sorted(self.pyproject["project"]["dependencies"]), sorted(requirements))

    def test_version_comes_from_the_package(self):
        self.assertEqual(self.pyproject["project"]["dynamic"], ["version"])
        self.assertEqual(self.pyproject["tool"]["setuptools"]["dynamic"]["version"], {"attr": "subekashi_mcp.__version__"})
        # setuptoolsがimportせずに読めるよう、__version__は文字列のリテラルで書く
        source = (MCP_DIR / "subekashi_mcp" / "__init__.py").read_text(encoding="utf-8")
        self.assertRegex(source, r'(?m)^__version__ = "\d+\.\d+\.\d+"$')

    def test_packages_include_every_subpackage(self):
        """packagesは明示しているため、サブパッケージを足したら一覧にも足す。足し忘れると、インストールした環境でだけimportできない"""
        packages = self.pyproject["tool"]["setuptools"]["packages"]
        subpackages = sorted(f"subekashi_mcp.{path.name}" for path in (MCP_DIR / "subekashi_mcp").iterdir() if (path / "__init__.py").exists())
        self.assertEqual(sorted(packages), sorted(["subekashi_mcp", *subpackages]))
