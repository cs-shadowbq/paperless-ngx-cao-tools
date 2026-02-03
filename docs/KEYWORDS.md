# Keywords Management for Actor Tags

## Overview

The `pngx-cao keywords` command allows you to manage keywords on actor tags by appending them in parentheses to the tag name. This is useful for marking actors with status indicators like "inactive", "retired", "dormant", etc.

## How It Works

Keywords are appended to actor tag names in parentheses:

- Original: `HYPER BASALISK`
- With keywords: `HYPER BASALISK (inactive, retired)`

The keywords are automatically sorted alphabetically for consistency.

## Commands

### 1. Add Keywords from CSV File

Process multiple actor tags at once using a CSV file.

```bash
pngx-cao keywords add-from-csv <csv_file> [OPTIONS]
```

#### CSV Format

The CSV file should have two columns:

| Name | Keywords |
|------|----------|
| HYPER BASALISK | inactive |
| FROST BASALISK | inactive, retired |

**Example CSV** (`data/inactive.csv`):

```csv
"Name","Keywords"
"HYPER BASALISK","inactive"
"FROST BASALISK","inactive, retired"
```

#### Examples

```bash
# Add keywords from CSV file
pngx-cao keywords add-from-csv data/inactive.csv

# Dry run to preview changes
pngx-cao keywords add-from-csv data/inactive.csv --dry-run

# With custom environment
pngx-cao keywords add-from-csv data/inactive.csv --env-prefix BOX1_
```

### 2. Add/Remove Keywords for Single Tag

Manage keywords for a specific actor tag using command-line arguments.

```bash
pngx-cao keywords add <tag_name> [OPTIONS]
```

#### Examples

```bash
# Add keywords to a tag
pngx-cao keywords add "HYPER BASALISK" -a inactive -a retired

# Remove a keyword
pngx-cao keywords add "HYPER BASALISK" -r inactive

# Add and remove in one command
pngx-cao keywords add "HYPER BASALISK" -a dormant -r inactive

# Dry run to see what would change
pngx-cao keywords add "HYPER BASALISK" -a inactive --dry-run
```

## Options

Both commands support the following options:

- `--env-file PATH`: Path to .env file for configuration
- `--env-prefix TEXT`: Environment variable prefix (e.g., "BOX1_")
- `--url TEXT`: Paperless-ngx URL (overrides environment)
- `--token TEXT`: API token (overrides environment)
- `-k, --skip-ssl-verify`: Skip SSL certificate verification (insecure)
- `--debug`: Enable debug logging
- `--dry-run`: Preview changes without making actual modifications

## Tag Matching

The keywords feature is smart about finding tags:

- You can specify the tag name with or without existing keywords
- `"HYPER BASALISK"` will match `HYPER BASALISK (inactive)` if it exists
- The system finds the actor tag even if keywords are already present

## Keyword Behavior

- **Adding keywords**: New keywords are appended to existing ones
- **Removing keywords**: Specified keywords are removed from the existing set
- **No duplicates**: Keywords are stored as a set, so duplicates are automatically prevented
- **Alphabetical ordering**: Keywords are always sorted alphabetically for consistency
- **Case-sensitive**: Keywords are case-sensitive (e.g., "Inactive" ≠ "inactive")

## Examples with CSV

### Example 1: Mark actors as inactive

**inactive.csv:**

```csv
"Name","Keywords"
"ANCIENT DRAGON","inactive"
"MYSTIC PHOENIX","inactive"
"GOLDEN GRIFFIN","inactive, retired"
```

**Command:**

```bash
pngx-cao keywords add-from-csv data/inactive.csv
```

**Result:**

- `ANCIENT DRAGON` → `ANCIENT DRAGON (inactive)`
- `MYSTIC PHOENIX` → `MYSTIC PHOENIX (inactive)`
- `GOLDEN GRIFFIN` → `GOLDEN GRIFFIN (inactive, retired)`

### Example 2: Add multiple status keywords

**status_update.csv:**

```csv
"Name","Keywords"
"CYBER BASALISK","monitored, active"
"SILENT WOLF","dormant, monitored"
```

**Command:**

```bash
pngx-cao keywords add-from-csv data/status_update.csv --dry-run
```

This will show what changes would be made without actually modifying the tags.

## Examples with Direct Commands

### Example 1: Simple addition

```bash
# Before: HYPER BASALISK
pngx-cao keywords add "HYPER BASALISK" -a inactive
# After: HYPER BASALISK (inactive)
```

### Example 2: Add multiple keywords

```bash
# Before: HYPER BASALISK
pngx-cao keywords add "HYPER BASALISK" -a inactive -a retired -a dormant
# After: HYPER BASALISK (dormant, inactive, retired)
# Note: Keywords are sorted alphabetically
```

### Example 3: Modify existing keywords

```bash
# Before: HYPER BASALISK (inactive, monitored)
pngx-cao keywords add "HYPER BASALISK" -r monitored -a retired
# After: HYPER BASALISK (inactive, retired)
```

### Example 4: Remove all keywords

```bash
# Before: HYPER BASALISK (inactive, retired)
pngx-cao keywords add "HYPER BASALISK" -r inactive -r retired
# After: HYPER BASALISK
```

## Output

The command provides detailed feedback:

- **Progress table**: Shows each tag being processed and its status
- **Summary statistics**: Counts of updated, skipped, not found, and failed operations
- **Dry run indicator**: Clear indication when running in dry-run mode

Example output:

```
Processing keywords from CSV: data/inactive.csv

  HYPER BASALISK → HYPER BASALISK (inactive)
  ✓ Updated tag ID 123
  FROST BASALISK → FROST BASALISK (inactive, retired)
  ✓ Updated tag ID 124

Summary:
  Updated: 2
  Skipped: 0
  Not found: 0
  Failed: 0
```

## Testing

Run the test suite to verify functionality:

```bash
pytest test/test_keywords.py -v
```

## Implementation Details

### Files Created/Modified

1. **src/pngx_cao/commands/keywords.py**: Command-line interface
2. **src/pngx_cao/services/keywords.py**: Business logic for keyword management
3. **src/pngx_cao/api/client.py**: Added `update_tag()` method
4. **src/pngx_cao/cli.py**: Registered keywords command
5. **test/test_keywords.py**: Unit tests for keyword parsing and building

### Key Functions

- `parse_tag_name()`: Extract base name and keywords from a tag name
- `build_tag_name()`: Construct a tag name with keywords
- `update_tag_keywords()`: Add/remove keywords for a single tag
- `add_keywords_from_csv()`: Process multiple tags from a CSV file

## Best Practices

1. **Use dry-run first**: Always test with `--dry-run` before making bulk changes
2. **Consistent naming**: Use lowercase for keywords (e.g., "inactive" not "Inactive")
3. **CSV validation**: Verify your CSV file format before processing
4. **Backup**: Consider backing up your Paperless-ngx database before bulk operations
5. **Test with one tag**: Test the command on a single tag before processing a CSV

## Troubleshooting

### Tag not found

- Ensure the tag exists in Paperless-ngx
- Check for typos in the tag name
- The tag must be an actor tag (not a country, industry, or motivation tag)

### CSV errors

- Verify the CSV has "Name" and "Keywords" columns
- Ensure proper CSV formatting (quotes, commas)
- Check for empty rows or missing values

### Permission errors

- Verify your API token has permission to modify tags
- Check the `PAPERLESS_TOKEN` environment variable
- Ensure the Paperless-ngx URL is correct
