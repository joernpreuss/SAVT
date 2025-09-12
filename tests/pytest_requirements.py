"""
Custom pytest plugin to extract and display requirements coverage from test docstrings.

This plugin parses test docstrings for FR- and BR- references and can generate
coverage reports showing which requirements are tested.
"""

import re
from collections import defaultdict

import pytest


class RequirementsCollector:
    """Collects requirements coverage from test docstrings."""

    def __init__(self):
        self.test_requirements = {}
        self.requirement_tests = defaultdict(list)

    def extract_requirements(self, docstring):
        """Extract FR- and BR- requirements from docstring."""
        if not docstring:
            return set()

        # Pattern matches: FR-1.1, BR-2.3, etc.
        pattern = r"\b(FR-\d+\.?\d*|BR-\d+\.?\d*)\b"
        requirements = set(re.findall(pattern, docstring, re.IGNORECASE))
        return {req.upper() for req in requirements}

    def collect_test_requirements(self, item):
        """Collect requirements from a test item's docstring."""
        if item.function.__doc__:
            requirements = self.extract_requirements(item.function.__doc__)
            if requirements:
                test_name = f"{item.module.__name__}::{item.function.__name__}"
                self.test_requirements[test_name] = requirements

                for req in requirements:
                    self.requirement_tests[req].append(test_name)


# Global collector instance
requirements_collector = RequirementsCollector()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Hook called before each test runs - collect requirements."""
    requirements_collector.collect_test_requirements(item)


@pytest.hookimpl(trylast=True)
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Hook called at end of test session - generate requirements report."""
    if not requirements_collector.test_requirements:
        return

    # Check if verbose mode or custom flag is set
    if terminalreporter.config.getoption("verbose") >= 1 or getattr(
        config.option, "requirements_report", False
    ):
        terminalreporter.section("Requirements Coverage")

        # Show tests grouped by requirements
        all_requirements = set()
        for reqs in requirements_collector.test_requirements.values():
            all_requirements.update(reqs)

        for req in sorted(all_requirements):
            tests = requirements_collector.requirement_tests[req]
            terminalreporter.write_line(f"  {req}:")
            for test in tests:
                # Extract just the test function name for brevity
                short_name = test.split("::")[-1]
                terminalreporter.write_line(f"    ✓ {short_name}")

        # Summary statistics
        total_tests = len(requirements_collector.test_requirements)
        total_requirements = len(all_requirements)

        terminalreporter.write_line("")
        terminalreporter.write_line("Requirements Coverage Summary:")
        terminalreporter.write_line(f"  Tests with requirements: {total_tests}")
        terminalreporter.write_line(f"  Requirements covered: {total_requirements}")


def pytest_addoption(parser):
    """Add command line option for requirements reporting."""
    parser.addoption(
        "--requirements-report",
        action="store_true",
        default=False,
        help="Show requirements coverage report even without verbose mode",
    )
    parser.addoption(
        "--requirements-only",
        action="store_true",
        default=False,
        help="Show only requirements coverage, skip test execution",
    )


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    """Modify collected items based on requirements flags."""
    if config.getoption("--requirements-only"):
        # Collect requirements without running tests
        for item in items:
            requirements_collector.collect_test_requirements(item)

        # Skip all test execution
        skip_marker = pytest.mark.skip(reason="Requirements analysis only")
        for item in items:
            item.add_marker(skip_marker)


# Custom marker for requirements
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "requirements(fr_list, br_list): mark test with specific FR/BR requirements",
    )


def requirements(*reqs: str):
    """Decorator to explicitly mark tests with requirements.

    Usage:
        @requirements("FR-1.1", "FR-1.2", "BR-2.1")
        def test_something():
            pass
    """

    def decorator(func):
        # Store requirements in function metadata
        func._requirements = {req.upper() for req in reqs}

        # Add to docstring if not already present
        if func.__doc__:
            existing_reqs = requirements_collector.extract_requirements(func.__doc__)
            new_reqs = {req.upper() for req in reqs} - existing_reqs
            if new_reqs:
                func.__doc__ += (
                    f"\n    Additional requirements: {', '.join(sorted(new_reqs))}"
                )
        else:
            func.__doc__ = (
                f"Requirements: {', '.join(sorted(req.upper() for req in reqs))}"
            )

        return func

    return decorator
