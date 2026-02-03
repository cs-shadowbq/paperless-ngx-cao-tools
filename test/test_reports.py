"""
Test JSON metadata validation for test reports.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def test_originals_dir():
    """Return path to test originals directory."""
    return Path(__file__).parent / "originals"


class TestReportJSONStructure:
    """Test that all test report JSON files have valid structure."""

    def test_all_reports_have_json_files(self, test_originals_dir):
        """Test that all report directories have JSON files."""
        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        assert len(report_dirs) == 6

        for report_dir in report_dirs:
            json_file = report_dir / f"{report_dir.name}.json"
            assert json_file.exists(), f"Missing JSON file for {report_dir.name}"

    def test_all_reports_have_pdf_files(self, test_originals_dir):
        """Test that all report directories have PDF files."""
        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        for report_dir in report_dirs:
            pdf_file = report_dir / f"{report_dir.name}.pdf"
            assert pdf_file.exists(), f"Missing PDF file for {report_dir.name}"

    def test_json_files_are_valid(self, test_originals_dir):
        """Test that all JSON files can be parsed."""
        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        for report_dir in report_dirs:
            json_file = report_dir / f"{report_dir.name}.json"
            with open(json_file, 'r') as f:
                data = json.load(f)
                assert isinstance(data, dict), f"Invalid JSON structure in {json_file}"

    def test_json_required_fields(self, test_originals_dir):
        """Test that all JSON files have required fields."""
        required_fields = [
            "id", "name", "slug", "type", "url",
            "short_description", "description", "created_date",
            "actors", "target_industries", "target_countries", "motivations"
        ]

        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        for report_dir in report_dirs:
            json_file = report_dir / f"{report_dir.name}.json"
            with open(json_file, 'r') as f:
                data = json.load(f)

                for field in required_fields:
                    assert field in data, f"Missing {field} in {json_file}"

    def test_actors_are_lists(self, test_originals_dir):
        """Test that actors field is a list with proper structure."""
        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        for report_dir in report_dirs:
            json_file = report_dir / f"{report_dir.name}.json"
            with open(json_file, 'r') as f:
                data = json.load(f)

                assert isinstance(data["actors"], list)

                # Skip length check for test folders that may have empty arrays
                if not report_dir.name.startswith('empty-'):
                    assert len(data["actors"]) > 0

                for actor in data["actors"]:
                    assert "name" in actor
                    assert "id" in actor

    def test_target_fields_are_lists(self, test_originals_dir):
        """Test that target fields are lists with proper structure."""
        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        for report_dir in report_dirs:
            json_file = report_dir / f"{report_dir.name}.json"
            with open(json_file, 'r') as f:
                data = json.load(f)

                # Check target_industries
                assert isinstance(data["target_industries"], list)
                # Skip length check for test folders that may have empty arrays
                if not report_dir.name.startswith('empty-'):
                    assert len(data["target_industries"]) > 0
                for item in data["target_industries"]:
                    assert "value" in item

                # Check target_countries
                assert isinstance(data["target_countries"], list)
                # Skip length check for test folders that may have empty arrays
                if not report_dir.name.startswith('empty-'):
                    assert len(data["target_countries"]) > 0
                for item in data["target_countries"]:
                    assert "value" in item

                # Check motivations
                assert isinstance(data["motivations"], list)
                assert len(data["motivations"]) > 0
                for item in data["motivations"]:
                    assert "value" in item


class TestReportContent:
    """Test specific content of test reports."""

    def test_report_names_match_test_pattern(self, test_originals_dir):
        """Test that all report names follow TEST-YYYY-NNN pattern."""
        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        for report_dir in report_dirs:
            # Skip special test folders like empty-001
            if report_dir.name.startswith('empty-'):
                continue
            assert report_dir.name.startswith("TEST-2024-")
            assert len(report_dir.name) == 13  # TEST-2024-NNN

    def test_actors_are_fantasy_based(self, test_originals_dir):
        """Test that actors use fantasy animal types."""
        expected_animals = {"UNICORN", "GRIFFIN", "CHUPACABRA"}
        found_animals = set()

        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        for report_dir in report_dirs:
            # Skip special test folders
            if report_dir.name.startswith('empty-'):
                continue
            json_file = report_dir / f"{report_dir.name}.json"
            with open(json_file, 'r') as f:
                data = json.load(f)

                for actor in data["actors"]:
                    # Extract animal from actor name
                    parts = actor["name"].split()
                    if len(parts) >= 2:
                        animal = parts[-1].upper()
                        found_animals.add(animal)

        assert found_animals == expected_animals

    def test_countries_are_fictional(self, test_originals_dir):
        """Test that target countries are fictional."""
        expected_countries = {"Wakanda", "Genovia", "Agrabah", "Sokovia"}
        found_countries = set()

        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        for report_dir in report_dirs:
            # Skip special test folders
            if report_dir.name.startswith('empty-'):
                continue
            json_file = report_dir / f"{report_dir.name}.json"
            with open(json_file, 'r') as f:
                data = json.load(f)

                for country in data["target_countries"]:
                    found_countries.add(country["value"])

        assert found_countries.issubset(expected_countries)

    def test_industries_are_fantasy(self, test_originals_dir):
        """Test that target industries are fantasy/sci-fi based."""
        expected_industries = {
            "Pneumatic Tube Industry",
            "Aether Refineries",
            "Warp Drive Engineering",
            "Terraform Plants"
        }
        found_industries = set()

        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        for report_dir in report_dirs:
            # Skip special test folders
            if report_dir.name.startswith('empty-'):
                continue
            json_file = report_dir / f"{report_dir.name}.json"
            with open(json_file, 'r') as f:
                data = json.load(f)

                for industry in data["target_industries"]:
                    found_industries.add(industry["value"])

        assert found_industries.issubset(expected_industries)

    def test_pdf_files_are_not_empty(self, test_originals_dir):
        """Test that PDF files have content (except for intentionally empty test files)."""
        report_dirs = [d for d in test_originals_dir.iterdir() if d.is_dir()]

        for report_dir in report_dirs:
            # Skip intentionally empty test files
            if report_dir.name.startswith('empty-'):
                continue
            pdf_file = report_dir / f"{report_dir.name}.pdf"
            assert pdf_file.stat().st_size > 0, f"Empty PDF file: {pdf_file}"
