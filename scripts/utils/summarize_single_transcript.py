#!/usr/bin/env python3
import os
import sys
import argparse
import pymongo
import datetime
from anthropic import Anthropic

# Configure logging (optional but recommended)
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    # Test connection
    client.admin.command('ping')
    db = client["earnings_transcripts"]
    transcripts_collection = db["transcripts"]
    document_summaries_collection = db["document_summaries"]
    logger.info("Successfully connected to MongoDB.")
except Exception as e:
    logger.error(f"MongoDB connection failed: {e}")
    sys.exit(f"Error: Could not connect to MongoDB. Please ensure it's running. Details: {e}")

def get_transcript_by_id_or_filename(doc_id=None, filename=None):
    """Retrieve a single transcript by document_id or filename."""
    if not doc_id and not filename:
        logger.error("Either document_id or filename must be provided.")
        return None

    query = {}
    if doc_id:
        query["document_id"] = doc_id
        logger.info(f"Fetching transcript by document_id: {doc_id}")
    elif filename:
        query["filename"] = filename
        logger.info(f"Fetching transcript by filename: {filename}")

    try:
        transcript = transcripts_collection.find_one(query)
        if transcript:
            logger.info(f"Transcript found: {transcript.get('filename', transcript.get('document_id'))}")
            return transcript
        else:
            logger.warning(f"No transcript found for query: {query}")
            return None
    except Exception as e:
        logger.error(f"Error fetching transcript for query {query}: {e}")
        return None

def count_words(text):
    """Count the number of words in a text"""
    return len(text.split())

def summarize_transcript_with_claude(transcript, max_words=300):
    """Summarize a single transcript using Claude."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set.")
        return "Error: ANTHROPIC_API_KEY environment variable not set", None

    try:
        anthropic_client = Anthropic(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Anthropic client: {e}")
        return f"Error initializing Anthropic client: {e}", None

    transcript_text = transcript.get("transcript_text", "")
    if not transcript_text:
        logger.warning("Transcript text is empty.")
        return "Error: Transcript text is empty.", None

    # Prepare details for the prompt
    category_id = transcript.get("category_id", "N/A")
    date_obj = transcript.get("date")
    date_str = date_obj.strftime("%Y-%m-%d") if isinstance(date_obj, datetime.datetime) else "N/A"
    quarter = transcript.get("quarter", "N/A")
    fiscal_year = transcript.get("fiscal_year", "N/A")
    doc_id = transcript.get("document_id", "N/A")

    # Truncate long transcripts to fit context limits (adjust MAX_CONTEXT_LEN as needed)
    MAX_CONTEXT_LEN = 100000 # Generous limit for Claude 3.5 Sonnet
    truncated_text = transcript_text
    if len(transcript_text) > MAX_CONTEXT_LEN:
        truncated_text = transcript_text[:MAX_CONTEXT_LEN] + "... [CONTENT TRUNCATED]"
        logger.warning(f"Transcript {doc_id} was truncated to {MAX_CONTEXT_LEN} characters for the prompt.")

    # Define prompt for single transcript summarization
    # TODO: Consider loading this from a config file like summarize_category.py does
    model = "claude-3-5-sonnet-20240620" # Or load from config
    system_prompt = "You are a financial analyst assistant tasked with summarizing individual earnings call transcripts."
    user_prompt = f"""Analyze the following earnings call transcript for {category_id} from {date_str} (Q{quarter} {fiscal_year}).
Provide a concise summary (approx. {max_words} words) focusing *only* on the information within this document. Cover these key areas:

1.  **Key Financial Results & Metrics:** Reported revenue, profit, EPS, key segment performance, and comparison to expectations if mentioned.
2.  **Guidance & Outlook:** Any forward-looking statements about future performance.
3.  **Strategic Initiatives & Management Commentary:** Major strategic decisions, investments, M&A, or significant commentary from leadership.
4.  **Product & Service Updates:** Mentions of new or updated products/services and their performance.
5.  **Market & Competition:** Comments on market trends, competitive landscape, or challenges.

Respond *only* with the summary text, without any preamble or explanation.

TRANSCRIPT TEXT:
{truncated_text}
"""

    logger.info(f"Sending request to Claude model {model} for document {doc_id}...")
    try:
        message = anthropic_client.messages.create(
            model=model,
            max_tokens=1024,  # Max tokens for the *output* summary
            temperature=0.1, # Lower temperature for factual summary
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        summary_text = message.content[0].text.strip()
        logger.info(f"Received summary from Claude for document {doc_id}. Word count: {count_words(summary_text)}")

        token_info = None
        if hasattr(message, 'usage'):
            token_info = {
                'input_tokens': message.usage.input_tokens,
                'output_tokens': message.usage.output_tokens
            }
            logger.info(f"Token usage: Input={token_info['input_tokens']}, Output={token_info['output_tokens']}")

        return summary_text, token_info, model

    except Exception as e:
        logger.error(f"Error calling Claude API for document {doc_id}: {e}")
        return f"Error calling Claude API: {str(e)}", None, model

def save_document_summary_to_db(transcript, summary_text, token_info=None, model_name=None):
    """Save or update the summary in the document_summaries collection."""
    doc_id = transcript.get("document_id")
    if not doc_id:
        logger.error("Cannot save summary: Original transcript has no document_id.")
        return "Error: Missing document_id in source transcript"

    category_id = transcript.get("category_id")
    if not category_id:
        logger.warning(f"Document {doc_id} is missing category_id in source transcript.")

    summary_doc = {
        "document_id": doc_id,
        "category_id": category_id,
        "summary_text": summary_text,
        "wordcount": count_words(summary_text),
        "model": model_name or "unknown",
        "last_updated": datetime.datetime.now(datetime.timezone.utc) # Use timezone-aware datetime
    }

    if token_info:
        summary_doc["input_tokens"] = token_info.get("input_tokens")
        summary_doc["output_tokens"] = token_info.get("output_tokens")

    try:
        # Use update_one with upsert=True to insert or update
        result = document_summaries_collection.update_one(
            {"document_id": doc_id},
            {"$set": summary_doc},
            upsert=True
        )

        if result.upserted_id:
            msg = f"Created new summary for document_id {doc_id}"
            logger.info(msg)
        elif result.matched_count > 0:
            msg = f"Updated existing summary for document_id {doc_id}"
            logger.info(msg)
        else:
            # This case shouldn't happen with upsert=True unless there's an issue
            msg = f"Summary save operation completed for document_id {doc_id}, but status unclear (matched={result.matched_count}, modified={result.modified_count})."
            logger.warning(msg)
        return msg

    except Exception as e:
        logger.error(f"Failed to save summary for document_id {doc_id}: {e}")
        return f"Error saving summary to DB: {e}"


def main():
    parser = argparse.ArgumentParser(description="Generate and save a summary for a single earnings transcript.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--document-id", help="Document ID (UUID) of the transcript to summarize.")
    group.add_argument("--filename", help="Filename of the transcript to summarize.")
    parser.add_argument("--max-words", type=int, default=300, help="Approximate target word count for the summary (default: 300)")
    parser.add_argument("--dry-run", action="store_true", help="Generate summary but don't save to database")

    args = parser.parse_args()

    # Get the transcript
    transcript = get_transcript_by_id_or_filename(doc_id=args.document_id, filename=args.filename)

    if not transcript:
        sys.exit(1) # Error message already logged by get_transcript_by_id_or_filename

    # Generate summary
    logger.info(f"Generating summary (approx {args.max_words} words) for {transcript.get('filename', args.document_id)}...")
    summary, token_info, model_used = summarize_transcript_with_claude(transcript, args.max_words)

    # Display summary
    print("\n--- Generated Summary ---")
    print(summary)
    print("------------------------")

    if token_info:
        print(f"(Model: {model_used}, Input Tokens: {token_info.get('input_tokens')}, Output Tokens: {token_info.get('output_tokens')})")
    else:
         print(f"(Model: {model_used})")

    # Save to database if not a dry run and no error occurred
    if not args.dry_run and not summary.startswith("Error"):
        logger.info("Saving summary to database...")
        save_result = save_document_summary_to_db(transcript, summary, token_info, model_used)
        print(f"Database result: {save_result}")
    elif args.dry_run:
        logger.info("Dry run - summary not saved to database.")
    else: # An error occurred during summarization
        logger.warning("Summary generation failed. Not saving to database.")

if __name__ == "__main__":
    main() 