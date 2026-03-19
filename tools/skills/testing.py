"""
Skill de testing.
Detecta el runner del proyecto y ejecuta tests.
Sin dependencias externas — solo stdlib.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class TestingSkill:
    """Utilidades de testing para usar desde el orquestador o los agentes."""

    def detect_test_runner(self, project_root: str | Path) -> str | None:
        """
        Detecta que test runner usa el proyecto mirando package.json y pyproject.toml.
        Retorna el nombre del runner o None si no se detecta.
        """
        root = Path(project_root)

        # Python: pytest primero
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                text = pyproject.read_text(encoding="utf-8").lower()
                if "pytest" in text:
                    return "pytest"
            except OSError:
                pass

        if (root / "pytest.ini").exists() or (root / "setup.cfg").exists():
            return "pytest"

        # JS/TS: leer scripts de package.json
        pkg_json = root / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {})
                test_script = scripts.get("test", "").lower()
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

                if "vitest" in deps or "vitest" in test_script:
                    return "vitest"
                if "jest" in deps or "jest" in test_script:
                    return "jest"
                if test_script:
                    # retornar el primer token del script como runner
                    return test_script.split()[0]
            except (json.JSONDecodeError, OSError):
                pass

        return None

    def run_tests(self, project_root: str | Path) -> dict:
        """
        Detecta el runner y ejecuta los tests.
        Retorna {"success": bool, "output": str, "runner": str}.
        """
        root = Path(project_root)
        runner = self.detect_test_runner(root)

        if not runner:
            return {"success": False, "output": "No se detecto test runner.", "runner": "none"}

        cmd_map = {
            "pytest":  ["pytest", "--tb=short", "-q"],
            "jest":    ["npx", "jest", "--passWithNoTests"],
            "vitest":  ["npx", "vitest", "run"],
        }
        cmd = cmd_map.get(runner, [runner])

        # Verificar que el ejecutable este disponible
        if not shutil.which(cmd[0]):
            return {
                "success": False,
                "output": f"'{cmd[0]}' no encontrado en PATH. ¿Instalaste las dependencias?",
                "runner": runner,
            }

        try:
            result = subprocess.run(
                cmd,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout or result.stderr or "(sin output)"
            return {
                "success": result.returncode == 0,
                "output": output[-3000:],
                "runner": runner,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "Tests excedieron el timeout de 120s.", "runner": runner}
        except Exception as e:
            return {"success": False, "output": str(e), "runner": runner}

    def get_coverage_report(self, project_root: str | Path) -> str:
        """
        Intenta obtener el reporte de cobertura si existe.
        Retorna texto del reporte o mensaje descriptivo.
        """
        root = Path(project_root)

        # Pytest coverage
        coverage_file = root / ".coverage"
        coverage_xml = root / "coverage.xml"
        coverage_html = root / "htmlcov" / "index.html"

        if coverage_xml.exists():
            try:
                text = coverage_xml.read_text(encoding="utf-8")
                # Extraer linea de resumen
                import re
                match = re.search(r'line-rate="([^"]+)"', text)
                if match:
                    rate = float(match.group(1)) * 100
                    return f"Cobertura de lineas: {rate:.1f}% (fuente: coverage.xml)"
            except OSError:
                pass

        if coverage_html.exists():
            return f"Reporte HTML disponible en: {coverage_html}"

        if coverage_file.exists():
            if shutil.which("coverage"):
                try:
                    result = subprocess.run(
                        ["coverage", "report", "--skip-empty"],
                        cwd=str(root),
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode == 0:
                        return result.stdout[-2000:]
                except Exception:
                    pass

        # Jest/Vitest coverage
        lcov = root / "coverage" / "lcov.info"
        if lcov.exists():
            return f"Reporte LCOV disponible en: {lcov}"

        return (
            "No se encontro reporte de cobertura.\n"
            "Para Python: ejecuta 'pytest --cov=. --cov-report=xml'\n"
            "Para Jest:   ejecuta 'jest --coverage'\n"
            "Para Vitest: ejecuta 'vitest run --coverage'"
        )


# Instancia por defecto
testing = TestingSkill()


def run_tests(project_root: str) -> dict:
    """Compatibilidad con la API de v1."""
    return testing.run_tests(project_root)
