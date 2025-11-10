# PDF Test Fixtures

This directory contains test PDF fixtures for the PDF ingestion service tests.

## Generating Fixtures

To generate the fixture PDFs, run:

```bash
python tests/fixtures/generate_fixtures.py
```

This will create:
- `test_text.pdf` - A text-based PDF with 3 pages
- `test_scanned.pdf` - An image-based PDF with 2 pages (simulating scanned documents)
- `test_headers_footers.pdf` - A PDF with headers and footers for testing text cleaning

## Requirements

- `reportlab` - For PDF generation
- `Pillow` - For image-based PDFs

Install with:
```bash
pip install reportlab Pillow
```
