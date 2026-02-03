# Keywords Command - Quick Start Guide

## Installation

The `keywords` command is now available as part of the `pngx-cao` CLI tool.

## Basic Usage

### 1. Add Keywords from CSV

The simplest way to add keywords to multiple actor tags is using a CSV file.

**Example CSV** (`test/data/inactive.csv`):

```csv
"Name","Keywords"
"HYPER BASALISK","inactive"
"FROST BASALISK","inactive, retired"
```

**Command:**

```bash
pngx-cao keywords add-from-csv test/data/inactive.csv --dry-run
```

**Output Preview:**

```
Processing keywords from CSV: test/data/inactive.csv

                    Keywords to Add (Dry Run)
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Actor Tag        ┃ Keywords to Add    ┃ Status       ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ HYPER BASALISK   │ inactive           │ Would update │
│ FROST BASALISK   │ inactive, retired  │ Would update │
└──────────────────┴────────────────────┴──────────────┘

Summary:
  Updated: 2
  Skipped: 0
  Not found: 0
  Failed: 0

Note: This was a dry run. No changes were made.
```

### 2. Add Keywords to a Single Tag

Add keywords to a specific actor tag using command-line arguments.

```bash
# Add single keyword
pngx-cao keywords add "HYPER BASALISK" -a inactive --dry-run

# Add multiple keywords
pngx-cao keywords add "HYPER BASALISK" -a inactive -a retired --dry-run

# Remove a keyword
pngx-cao keywords add "FROST BASALISK" -r retired --dry-run

# Add and remove at the same time
pngx-cao keywords add "HYPER BASALISK" -a dormant -r inactive --dry-run
```

## Real Examples

### Example 1: Mark Actors as Inactive

```bash
# Preview changes
pngx-cao keywords add-from-csv test/data/inactive.csv --dry-run

# Apply changes
pngx-cao keywords add-from-csv test/data/inactive.csv
```

### Example 2: Update Single Tag Status

```bash
# Preview
pngx-cao keywords add "GOLDEN GRIFFIN" -a inactive -a monitored --dry-run

# Apply
pngx-cao keywords add "GOLDEN GRIFFIN" -a inactive -a monitored
```

### Example 3: Transition Tag Status

```bash
# Change from inactive to retired
pngx-cao keywords add "MYSTIC UNICORN" -r inactive -a retired
```

## Command Reference

### add-from-csv

```bash
pngx-cao keywords add-from-csv <csv_file> [OPTIONS]

Options:
  --dry-run              Preview changes without applying them
  --env-file PATH        Path to .env file
  --env-prefix TEXT      Environment variable prefix
  --url TEXT             Paperless-ngx URL
  --token TEXT           API token
  --debug                Enable debug logging
  -k, --skip-ssl-verify  Skip SSL verification
```

### add

```bash
pngx-cao keywords add <tag_name> [OPTIONS]

Options:
  -a, --add-keywords TEXT     Keywords to add (can be repeated)
  -r, --remove-keywords TEXT  Keywords to remove (can be repeated)
  --dry-run                   Preview changes without applying them
  --env-file PATH             Path to .env file
  --env-prefix TEXT           Environment variable prefix
  --url TEXT                  Paperless-ngx URL
  --token TEXT                API token
  --debug                     Enable debug logging
  -k, --skip-ssl-verify       Skip SSL verification
```

## Tips

1. **Always use --dry-run first** to preview changes
2. **Keywords are case-sensitive**: "Inactive" ≠ "inactive"
3. **Keywords are sorted alphabetically** for consistency
4. **Tag matching is smart**: You can specify "HYPER BASALISK" even if the actual tag is "HYPER BASALISK (inactive)"
5. **No duplicates**: Adding a keyword that already exists has no effect

## Environment Setup

Make sure your environment is configured with:

- `PAPERLESS_URL`: Your Paperless-ngx instance URL
- `PAPERLESS_TOKEN`: Your API token

Or use command-line options:

```bash
pngx-cao keywords add-from-csv data/inactive.csv \
  --url https://paperless.example.com \
  --token your-api-token-here
```

## Testing

Run the test suite to verify the implementation:

```bash
pytest test/test_keywords.py -v
```

All 9 tests should pass:

- ✓ Parse tag name without keywords
- ✓ Parse tag name with keywords
- ✓ Parse tag name with single keyword
- ✓ Parse tag name with extra spaces
- ✓ Build tag name without keywords
- ✓ Build tag name with keywords
- ✓ Build tag name with single keyword
- ✓ Roundtrip parse and build
- ✓ Parse and build normalization

## Troubleshooting

### "Tag not found"

The tag must exist in Paperless-ngx before you can add keywords. Create the tag first using the taxonomy commands.

### "No changes needed"

The keywords you're trying to add already exist on the tag, or the keywords you're trying to remove don't exist.

### CSV parsing errors

Ensure your CSV has proper formatting:

- Column names: "Name" and "Keywords"
- Use quotes around values with commas
- UTF-8 encoding

## Documentation

For more detailed information, see [docs/KEYWORDS.md](docs/KEYWORDS.md).
