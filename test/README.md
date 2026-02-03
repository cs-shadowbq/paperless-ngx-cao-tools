# Test Suite for pngx-cao

This directory contains the test suite for the pngx-cao tool, using pytest for testing framework.

## Test Structure

```
test/
├── __init__.py
├── test_config.py          # Configuration tests
├── test_constants.py       # Constants and utility function tests
├── test_csv_reader.py      # CSV reading functionality tests
├── test_reports.py         # Test report validation tests
├── test_watcher.py         # Directory watcher service tests
├── data/                   # Test CSV taxonomy data
│   ├── actors.csv
│   ├── motivations.csv
│   ├── targeted_countries.csv
│   └── targeted_industries.csv
└── originals/              # Test report metadata and PDFs
    ├── TEST-2024-001/
    ├── TEST-2024-002/
    ├── TEST-2024-003/
    ├── TEST-2024-004/
    └── TEST-2024-005/
```

## Running Tests

### Run all tests
```bash
pytest test/
```

### Run with verbose output
```bash
pytest test/ -v
```

### Run specific test file
```bash
pytest test/test_csv_reader.py
```

### Run specific test class
```bash
pytest test/test_csv_reader.py::TestReadCSVValues
```

### Run specific test
```bash
pytest test/test_csv_reader.py::TestReadCSVValues::test_read_actors_csv
```

### Run with coverage
```bash
pytest test/ --cov=src/pngx_cao --cov-report=html
```

## Test Categories

### Configuration Tests (`test_config.py`)
- Tests configuration loading and validation
- Tests default values and SSL verification settings
- Tests duplicate handling configuration

### Constants Tests (`test_constants.py`)
- Tests animal extraction from actor names
- Tests actor tag identification
- Tests CSV-based animal extraction
- Tests taxonomy configuration structure
- Tests color palette validity

### CSV Reader Tests (`test_csv_reader.py`)
- Tests reading multi-column CSV files (actors)
- Tests reading single-column CSV files (motivations, countries, industries)
- Tests grouping actors by animal type
- Tests extracting animal types from tag names

### Report Validation Tests (`test_reports.py`)
- Tests JSON file structure and validity
- Tests PDF file existence and content
- Tests that all reports use fantasy/test data only
- Tests required JSON fields and data types
- Validates that test data uses fictional entities

### Watcher Service Tests (`test_watcher.py`)
- Tests folder stabilization detection
- Tests directory scanning and polling
- Tests upload callback integration
- Tests processed folder tracking
- Tests graceful error handling
- Integration tests for end-to-end watching scenarios

## Test Data

All test data uses **fantasy-based entities** to ensure no production data leakage:

- **Actors**: UNICORN, GRIFFIN, CHUPACABRA (3 animal types, 8 total actors)
- **Countries**: Wakanda, Genovia, Agrabah, Sokovia (fictional countries)
- **Industries**: Pneumatic Tube Industry, Aether Refineries, Warp Drive Engineering, Terraform Plants
- **Motivations**: Artistic, Guilt, Hustle

## CI/CD Integration

Tests are automatically run via GitHub Actions on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

See [.github/workflows/test.yml](../.github/workflows/test.yml) for CI configuration.

## Adding New Tests

When adding new tests:

1. Follow the existing naming convention: `test_*.py`
2. Organize tests into classes: `class Test*:`
3. Use descriptive test names: `def test_*():`
4. Add docstrings explaining what each test validates
5. Use the test data in `test/data/` and `test/originals/`
6. Ensure tests are dry-run/non-destructive (no API calls)

## Dependencies

Test dependencies are defined in `pyproject.toml`:

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]
```

Install with:
```bash
pip install -e ".[test]"
```

## Test Coverage

Current test coverage includes:
- ✅ CSV reading and parsing
- ✅ Configuration loading
- ✅ Utility functions (animal extraction, tag identification)
- ✅ Test data validation
- ✅ JSON metadata structure
- ✅ Directory watcher and folder stabilization
- ⚠️ CLI commands (not covered - would require mocking API)
- ⚠️ API client (not covered - would require mocking HTTP)
- ⚠️ Upload services (not covered - would require mocking API)

## Notes

- Tests are designed for **dry-run only** - no actual API calls are made
- All test data is safe for public repositories
- Tests validate code logic and data structure, not live API interactions
- For integration testing with a real Paperless-ngx instance, use the actual CLI commands with test data
