# Test Data for pngx-cao

This directory contains **fake, non-production test data** that can be safely shared in public repositories and used for testing without risk of data leakage.

## ⚠️ Important: This is NOT Production Data

All data in the `test/data/` and `test/originals/` directories is completely fictional and does not represent any real:

- Threat actors
- Countries or geographic regions  
- Industries or organizations
- Intelligence reports or security incidents

## Purpose

This test data set is designed for:

- Development and testing of the pngx-cao tool
- Demonstration purposes
- Training and documentation
- CI/CD pipelines
- Public repository inclusion

## Test Data Structure

### Fake Taxonomies (in `test/data/`)

**Actors (8 total):**

- 3 UNICORN actors: MYSTIC UNICORN, COSMIC UNICORN, SHADOW UNICORN
- 2 GRIFFIN actors: GOLDEN GRIFFIN, STORM GRIFFIN  
- 3 CHUPACABRA actors: ANCIENT CHUPACABRA, URBAN CHUPACABRA, CYBER CHUPACABRA

**Targeted Countries (4 total):**

- Wakanda (from Black Panther)
- Genovia (from The Princess Diaries)
- Agrabah (from Aladdin)
- Sokovia (from Avengers)

**Motivations (3 total):**

- Artistic
- Guilt
- Hustle

**Targeted Industries (4 total):**

- Pneumatic Tube Industry
- Aether Refineries
- Warp Drive Engineering
- Terraform Plants

### Fake Reports (in `test/originals/`)

**TEST-2024-001**: MYSTIC UNICORN targeting Pneumatic Tube Industry in Wakanda (Artistic)

**TEST-2024-002**: GOLDEN GRIFFIN & STORM GRIFFIN targeting Aether Refineries in Genovia (Hustle)

**TEST-2024-003**: ANCIENT CHUPACABRA targeting Warp Drive Engineering in Agrabah (Guilt)

**TEST-2024-004**: CYBER CHUPACABRA targeting Terraform Plants in Sokovia (Artistic)

**TEST-2024-005**: COSMIC UNICORN, SHADOW UNICORN & URBAN CHUPACABRA multi-target campaign (Hustle & Guilt)

## Usage

### Test with Fake Data

```bash
# Use test data directory
export PAPERLESS_DATA_DIR=./test/data

# List test taxonomies
pngx-cao taxonomy list --data-dir ./test/data

# Validate test taxonomies
pngx-cao taxonomy validate --data-dir ./test/data

# Create test taxonomies (will create fake tags)
pngx-cao taxonomy create --all --data-dir ./test/data

# Upload test documents
pngx-cao upload batch ./test/originals

# Upload single test document
pngx-cao upload folder ./test/originals/TEST-2024-001
```

### Switch Between Production and Test Data

```bash
# Use production data (default)
pngx-cao taxonomy create --all

# Use test data
pngx-cao taxonomy create --all --data-dir ./test/data
```

## File Structure

```
paperless-ngx-tools/
├── test/
│   ├── data/                          # Fake taxonomy CSV files
│   │   ├── actors.csv                 # 8 fake threat actors
│   │   ├── motivations.csv            # 3 fake motivations
│   │   ├── targeted_countries.csv     # 4 fictional countries
│   │   └── targeted_industries.csv    # 4 sci-fi industries
│   └── originals/                     # Fake intelligence reports
│       ├── TEST-2024-001/
│       │   ├── TEST-2024-001.json
│       │   └── TEST-2024-001.pdf
│       ├── TEST-2024-002/
│       │   ├── TEST-2024-002.json
│       │   └── TEST-2024-002.pdf
│       ├── TEST-2024-003/
│       │   ├── TEST-2024-003.json
│       │   └── TEST-2024-003.pdf
│       ├── TEST-2024-004/
│       │   ├── TEST-2024-004.json
│       │   └── TEST-2024-004.pdf
│       └── TEST-2024-005/
│           ├── TEST-2024-005.json
│           └── TEST-2024-005.pdf
└── README-TEST-DATA.md                # This file
```

## Cleaning Up Test Data

If you've uploaded test data to your Paperless-ngx instance and want to remove it:

1. Search for documents with titles starting with "TEST-2024"
2. Search for tags containing "UNICORN", "GRIFFIN", or "CHUPACABRA"
3. Search for tags: "Wakanda", "Genovia", "Agrabah", "Sokovia"
4. Delete the identified documents and tags

## Contributing

When adding new test data:

1. Ensure all names are clearly fictional
2. Use obviously fake geographic locations
3. Use science fiction or fantasy themed content
4. Never include any real threat intelligence
5. Document new test cases in this README
