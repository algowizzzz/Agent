# Earnings Transcript Database Setup

This guide explains how to set up the MongoDB database containing earnings call transcripts used by the `transcript_search_summary_tool` / `EarningsCallSummary` tool in the BussGPT system.

## Database Overview

The database contains earnings call transcripts and their summaries for major tech companies from approximately Q4 2019 through Q4 2020/Q2 2021.

**Database Details:**
- **Name:** `earnings_transcripts`
- **Connection:** MongoDB running on `localhost:27017` (standard port)
- **Total transcripts:** 188 documents
- **Companies covered:** AAPL, AMD, AMZN, ASML, CSCO, GOOGL, INTC, MSFT, MU, NVDA

**Key Collections:**
1. `transcripts` - Full transcript documents with metadata (188 documents)
2. `document_summaries` - Pre-computed summaries of individual transcripts (167 documents)
3. `category_summaries` - Synthesized summaries for company categories (10 documents)
4. `categories` - Company/ticker metadata (10 documents)
5. `transcripts_archive` - Archive copy of the transcripts (188 documents)

## Restoring the Database

To restore the database from the provided backup file:

### Prerequisites
- MongoDB installed and running on the standard port (27017)
- MongoDB command-line tools (`mongorestore`) installed

### Steps

1. **Extract the backup archive**
   ```bash
   tar -xzvf earnings_transcripts_backup.tar.gz
   ```
   This will create an `earnings_backup` directory containing the MongoDB dump files.

2. **Restore the database**
   ```bash
   mongorestore earnings_backup/
   ```
   This command will restore all collections to a MongoDB database named `earnings_transcripts`.

3. **Verify the restoration**
   ```bash
   mongosh
   > use earnings_transcripts
   > db.transcripts.count()  # Should return 188
   > db.document_summaries.count()  # Should return 167
   > db.category_summaries.count()  # Should return 10
   ```

## Code Configuration

The MongoDB connection details are currently hardcoded in:
- `langchain_tools/tool5_transcript_analysis.py` (line ~25)
- `langchain_tools/tool4_metadata_lookup.py` (line ~26)

Both files use the connection string: `mongodb://localhost:27017/`

If you need to use a different MongoDB server or port, you'll need to modify these files.

## Sample Data

Here's a sample of the transcript data available (most recent 3 per company):

```
AAPL:
  - Q3 2020 (2020-07-30)
  - Q2 2020 (2020-04-30)
  - Q1 2020 (2020-01-28)

AMD:
  - Q2 2020 (2020-07-28)
  - Q1 2020 (2020-04-28)
  - Q4 2019 (2020-01-28)

AMZN:
  - Q2 2020 (2020-07-30)
  - Q1 2020 (2020-04-30)
  - Q4 2019 (2020-01-30)

ASML:
  - Q2 2020 (2020-07-15)
  - Q1 2020 (2020-04-15)
  - Q4 2019 (2020-01-22)

CSCO:
  - Q4 2020 (2020-08-12)
  - Q3 2020 (2020-05-13)
  - Q2 2020 (2020-02-12)

GOOGL:
  - Q2 2020 (2020-07-30)
  - Q1 2020 (2020-04-28)
  - Q4 2019 (2020-02-03)

INTC:
  - Q2 2020 (2020-07-23)
  - Q1 2020 (2020-04-23)
  - Q4 2019 (2020-01-23)

MSFT:
  - Q4 2020 (2020-07-22)
  - Q3 2020 (2020-04-29)
  - Q2 2020 (2020-01-29)

MU:
  - Q3 2020 (2020-06-29)
  - Q2 2020 (2020-03-25)
  - Q1 2020 (2019-12-18)

NVDA:
  - Q2 2021 (2020-08-19)
  - Q1 2021 (2020-05-21)
  - Q4 2020 (2020-02-13)
```

## Troubleshooting

If you encounter issues with the transcript tool:

1. **MongoDB Connection:** Ensure MongoDB is running on the default port (27017)
2. **Missing Collections:** Verify all collections were restored properly
3. **API Keys:** The transcript analysis tool requires an Anthropic API key stored in the `ANTHROPIC_API_KEY` environment variable 