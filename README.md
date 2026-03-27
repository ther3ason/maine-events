# Portland Events ETL Pipeline

A production-grade, modular ETL pipeline that aggregates live event data from Greater Portland, Maine venues and loads it into an AWS S3 Data Lake using a Bronze/Silver/Gold medallion architecture.

Built as a portfolio project demonstrating real-world Data Engineering skills: web scraping, data validation, cloud infrastructure-as-code, and CI/CD.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LOCAL EXTRACTION                            │
│                                                                     │
│  PortlandOldPort.com  ──┐                                           │
│  State Theatre          ├──▶  BaseScraper  ──▶  Pydantic Event     │
│  Thompson's Point      ─┘         │               (validated)      │
└───────────────────────────────────┼─────────────────────────────────┘
                                    │
                                    ▼  JSON (newline-delimited)
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS S3 DATA LAKE                           │
│                                                                     │
│   Bronze/  ──▶  raw scraped JSON (immutable)                        │
│   Silver/  ──▶  cleaned, deduplicated, type-cast                    │
│   Gold/    ──▶  aggregated, analytics-ready Parquet                 │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS ANALYTICS                               │
│                                                                     │
│   AWS Glue Data Catalog  ──▶  Amazon Athena (serverless SQL)        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Scraping | `requests`, `BeautifulSoup4` |
| Data Validation | `Pydantic v2` |
| Cloud Storage | AWS S3 |
| Infrastructure | Terraform >= 1.5 |
| Serverless Compute | AWS Lambda (roadmap) |
| ETL / Cataloging | AWS Glue (ETL jobs + Crawler + Data Catalog) |
| Query Engine | Amazon Athena |
| CI/CD | GitHub Actions |
| Testing | `pytest`, `pytest-cov` |
| Linting | `flake8` |

---

## Project Structure

```
maine-events/
├── .github/
│   └── workflows/
│       └── python-app.yml    # CI: lint + test on every push
├── data/
│   └── raw/                  # Local output (gitignored)
├── infra/
│   └── terraform/
│       ├── main.tf           # S3 bucket + IAM resources
│       ├── variables.tf
│       └── outputs.tf
├── src/
│   ├── models.py             # Pydantic Event schema
│   ├── extractors/
│   │   ├── base_scraper.py   # Abstract base with retry logic
│   │   └── portland_old_port.py
│   └── transform/            # Silver/Gold transform logic (roadmap)
├── tests/
│   ├── test_models.py
│   └── test_base_scraper.py
├── requirements.txt
└── README.md
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- AWS CLI configured (`aws configure`)

### 1. Clone & install

```bash
git clone https://github.com/TheR3ason/maine-events.git
cd maine-events

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the scraper

```bash
# From the project root
python -c "
from src.extractors.portland_old_port import PortlandOldPortScraper
import json

scraper = PortlandOldPortScraper()
events = scraper.run()
for e in events:
    print(json.dumps(e.to_s3_dict(), indent=2))
"
```

### 3. Run tests

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

### 4. Provision AWS infrastructure

```bash
cd infra/terraform

terraform init
terraform plan -var="environment=dev"
terraform apply -var="environment=dev"
```

> **Cost note:** The S3 bucket incurs standard AWS storage costs. The pipeline uses serverless services (Lambda, Athena) billed per invocation — ideal for low-volume portfolio workloads.

---

## Medallion Architecture

| Layer | S3 Prefix | Format | Description |
|---|---|---|---|
| **Bronze** | `bronze/` | Newline-delimited JSON | Raw, immutable scrape output |
| **Silver** | `silver/` | Parquet (partitioned by date) | Cleaned, deduplicated, type-cast |
| **Gold** | `gold/` | Parquet | Aggregated, Athena-queryable analytics tables |

---

## Roadmap

### Phase 1 — Scrapers (current)
- [x] `BaseScraper` abstract class with retry logic
- [x] `PortlandOldPort` scraper
- [ ] **State Theatre scraper** — pull upcoming shows from `statetheatreportland.com`
- [ ] **Thompson's Point scraper** — outdoor venue with seasonal concert series
- [ ] **Maine Mariners schedule integration** — ECHL hockey game data via team API
- [ ] **Portland Sea Dogs calendar** — Double-A baseball affiliate of the Red Sox
- [ ] **Duplicate detection** — fuzzy-match event names across venues

### Phase 2 — AWS Loading
- [ ] **S3 Bronze load** — write validated JSON from scrapers into `bronze/` prefix
- [ ] **AWS Glue ETL job** — transform Bronze JSON → Silver Parquet (clean, deduplicate, type-cast)
- [ ] **AWS Glue Crawler** — auto-discover schema and populate the Glue Data Catalog
- [ ] **Amazon Athena** — serverless SQL queries over the Silver/Gold layers
- [ ] **Glue job for Gold layer** — aggregate Silver into analytics-ready tables

### Phase 3 — Orchestration & Automation
- [ ] **AWS Lambda packaging** — containerise scrapers for scheduled cloud execution
- [ ] **EventBridge trigger** — run full pipeline nightly on a cron schedule
- [ ] **Streamlit dashboard** — local "What's on in Portland this weekend?" UI
- [ ] **Slack / SMS alert** — notify when a high-demand event is added

---

## Contributing

Pull requests are welcome. Please open an issue first to discuss significant changes.

1. Fork the repo and create a feature branch (`git checkout -b feat/thompson-point-scraper`)
2. Ensure `flake8` and `pytest` pass
3. Open a PR against `main`

---

## License

MIT — see [LICENSE](LICENSE) for details.
