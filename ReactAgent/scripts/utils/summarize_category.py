#!/usr/bin/env python3
import os
import sys
import argparse
import pymongo
import datetime
import json
from anthropic import Anthropic
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    client.admin.command('ping') # Test connection
    db = client["earnings_transcripts"]
    transcripts_collection = db["transcripts"]
    document_summaries_collection = db["document_summaries"] # Use this collection now
    category_summaries_collection = db["category_summaries"]
    logger.info("Successfully connected to MongoDB.")
except Exception as e:
    logger.error(f"MongoDB connection failed: {e}")
    sys.exit(f"Error: Could not connect to MongoDB. Details: {e}")

# Load improved prompt configuration (optional, for synthesis prompt if needed)
config = {}
try:
    with open("improved_summary_prompts_config.json", "r") as f:
        config = json.load(f)
    logger.info("Loaded prompt configuration from improved_summary_prompts_config.json")
except Exception as e:
    logger.warning(f"Could not load improved_summary_prompts_config.json: {str(e)}. Will use default synthesis prompt.")

def get_summaries_for_category(category, limit=100):
    """Retrieve the most recent individual document summaries for a given category."""
    category_upper = category.upper()
    summaries_with_dates = []
    document_ids = []

    try:
        # 1. Find relevant transcript document_ids and dates, sorted by date
        transcript_cursor = transcripts_collection.find(
            {"category_id": category_upper},
            {"document_id": 1, "date": 1, "quarter": 1, "fiscal_year": 1, "_id": 0}
        ).sort("date", -1).limit(limit)

        # Create a map of document_id to date info for quick lookup
        transcript_info_map = {
            t['document_id']: {
                'date': t.get('date'),
                'quarter': t.get('quarter'),
                'fiscal_year': t.get('fiscal_year')
            }
            for t in transcript_cursor if t.get('document_id')
        }
        ordered_doc_ids = list(transcript_info_map.keys()) # Keep the date order

        if not ordered_doc_ids:
            logger.warning(f"No transcripts found for category {category_upper} to fetch summaries.")
            return [], []

        # 2. Fetch corresponding summaries from document_summaries
        logger.info(f"Fetching document summaries for {len(ordered_doc_ids)} transcripts (category: {category_upper})...")
        summary_cursor = document_summaries_collection.find(
            {"document_id": {"$in": ordered_doc_ids}}
        )

        # Create a map of document_id to summary document
        summary_map = {s['document_id']: s for s in summary_cursor}

        # 3. Combine summaries with date info, maintaining order
        found_summaries_count = 0
        for doc_id in ordered_doc_ids:
            if doc_id in summary_map:
                summary_doc = summary_map[doc_id]
                # Add date/quarter info from transcript map
                transcript_info = transcript_info_map.get(doc_id, {})
                summary_doc['date'] = transcript_info.get('date')
                summary_doc['quarter'] = transcript_info.get('quarter')
                summary_doc['fiscal_year'] = transcript_info.get('fiscal_year')
                summaries_with_dates.append(summary_doc)
                document_ids.append(doc_id) # Collect doc_ids for saving later
                found_summaries_count += 1
            else:
                logger.warning(f"No document summary found for document_id: {doc_id}")

        logger.info(f"Found {found_summaries_count} individual summaries for category {category_upper}.")
        # Return summaries sorted implicitly by original transcript date order
        return summaries_with_dates, document_ids

    except Exception as e:
        logger.error(f"Error fetching summaries for category {category_upper}: {e}", exc_info=True)
        return [], []


def format_category_stats_from_summaries(category, summaries):
    """Format basic information based on fetched summaries."""
    if not summaries:
        return f"No individual summaries found for category {category}"

    dates = [s.get('date') for s in summaries if s.get('date')]
    quarters = [f"Q{s.get('quarter')} {s.get('fiscal_year')}"
               for s in summaries if s.get('quarter') and s.get('fiscal_year')]

    info = f"Category: {category}\n"
    info += f"Number of individual summaries found: {len(summaries)}\n"
    if dates:
        min_date = min(dates)
        max_date = max(dates)
        info += f"Date range covered: {min_date.strftime('%Y-%m-%d') if min_date else 'N/A'} to {max_date.strftime('%Y-%m-%d') if max_date else 'N/A'}\n"
    if quarters:
         info += f"Recent quarters covered: {', '.join(quarters[:5])}..." # Show first few

    # Calculate summary word count statistics
    word_counts = [s.get('wordcount') for s in summaries if s.get('wordcount')]
    if word_counts:
        info += f"Average individual summary word count: {sum(word_counts) / len(word_counts):.1f}\n"
        info += f"Min/Max individual summary word count: {min(word_counts)} / {max(word_counts)}\n"

    return info

def synthesize_summaries_with_claude(category, summaries, max_words=1500):
    """Synthesize a category summary using Claude based on individual summaries."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set.")
        return "Error: ANTHROPIC_API_KEY environment variable not set", None

    try:
        anthropic_client = Anthropic(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Anthropic client: {e}")
        return f"Error initializing Anthropic client: {e}", None

    if not summaries:
        logger.warning("No individual summaries provided for synthesis.")
        return "Error: No individual summaries available to synthesize.", None

    # --- Configure Synthesis Prompt ---
    # Check config file first, otherwise use default
    synth_config = config.get("category_synthesis", {}) # Look for a specific synthesis config section
    model = synth_config.get("model", "claude-3-5-sonnet-20240620") # Default model
    system_prompt = synth_config.get("system_prompt",
        "You are an expert financial analyst. Your task is to synthesize multiple earnings call summaries for a specific company over a period, identifying key trends, strategic shifts, performance patterns, and overall business trajectory. Create a cohesive narrative, highlighting changes and consistencies across quarters.")
    user_prompt_template = synth_config.get("user_prompt_template")
    max_tokens = synth_config.get("max_tokens", 4000) # Allow more tokens for synthesis output
    temperature = synth_config.get("temperature", 0.1) # Keep temperature low for factual synthesis
    default_max_words = synth_config.get("default_max_words", 1500)

    # Use config max_words if not specified via argument
    if max_words == 1500 and default_max_words != 1500:
        max_words = default_max_words

    # --- Prepare Context from Summaries ---
    # Sort summaries by date (most recent first) - already sorted by get_summaries_for_category
    summary_details = ""
    earliest_date = None
    latest_date = None

    for summary_doc in summaries: # Assumes summaries are sorted chronologically descending
        date = summary_doc.get('date')
        quarter = summary_doc.get('quarter')
        fiscal_year = summary_doc.get('fiscal_year')
        summary_text = summary_doc.get('summary_text', 'Summary not available.')

        if date:
            if earliest_date is None or date < earliest_date:
                earliest_date = date
            if latest_date is None or date > latest_date:
                latest_date = date

        header = f"--- Summary for Q{quarter} {fiscal_year} ({date.strftime('%Y-%m-%d') if date else 'N/A'}) ---"
        summary_details += f"{header}\n{summary_text}\n\n"

    time_period = f"{earliest_date.strftime('%Y-%m-%d') if earliest_date else 'N/A'} to {latest_date.strftime('%Y-%m-%d') if latest_date else 'N/A'}"

    # --- Construct Final Prompt ---
    if user_prompt_template:
        # Use template from config file
        prompt = user_prompt_template.format(
            category_id=category,
            num_summaries=len(summaries),
            time_period=time_period,
            individual_summaries=summary_details, # Pass the concatenated summaries
            max_words=max_words
        )
    else:
        # Use default synthesis prompt
        prompt = f"""Based on the following {len(summaries)} individual earnings call summaries for {category} covering the period {time_period}, provide a comprehensive synthesized analysis (approx. {max_words} words).

Focus on identifying and discussing:
- Key strategic shifts or consistent themes over time.
- Evolution of financial performance and key metrics.
- Recurring challenges or risks and how management addressed them.
- Notable product developments and their trajectory.
- Overall business trajectory and outlook changes during this period.

Structure your response as a cohesive analytical report, not just a list of points.

INDIVIDUAL EARNINGS CALL SUMMARIES (Most Recent First):
{summary_details}
Synthesized Analysis:"""

    logger.info(f"Sending synthesis request to Claude model {model} for category {category}...")
    logger.debug(f"System Prompt: {system_prompt}")
    # logger.debug(f"User Prompt (first 500 chars): {prompt[:500]}...") # Avoid logging potentially huge prompts

    try:
        message = anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        synthesized_summary = message.content[0].text.strip()
        logger.info(f"Received synthesized summary from Claude for category {category}. Word count: {count_words(synthesized_summary)}")

        token_info = None
        if hasattr(message, 'usage'):
            token_info = {
                'input_tokens': message.usage.input_tokens,
                'output_tokens': message.usage.output_tokens
            }
            logger.info(f"Token usage: Input={token_info['input_tokens']}, Output={token_info['output_tokens']}")

        return synthesized_summary, token_info

    except Exception as e:
        logger.error(f"Error calling Claude API for synthesis of {category}: {e}", exc_info=True)
        return f"Error calling Claude API for synthesis: {str(e)}", None

def count_words(text):
    """Count the number of words in a text"""
    return len(text.split())

def save_category_summary_to_db(category, summary_text, token_info=None, summary_count=0, document_ids=None):
    """Save the synthesized summary to the category_summaries collection."""
    # Check if a summary already exists for this category
    existing_summary = category_summaries_collection.find_one({"category_id": category})

    # Prepare the summary document
    summary_doc = {
        "category_id": category,
        "summary_text": summary_text,
        "wordcount": count_words(summary_text),
        "transcript_count": summary_count, # Represents number of underlying transcripts/summaries used
        "last_updated": datetime.datetime.now(datetime.timezone.utc), # Use timezone-aware
        "document_ids": document_ids or [], # List of doc IDs corresponding to used summaries
        "summary_type": "category_synthesis" # Indicate this is a synthesized summary
    }

    # Add token information if available
    if token_info:
        summary_doc["input_tokens"] = token_info.get('input_tokens')
        summary_doc["output_tokens"] = token_info.get('output_tokens')
    # Add model info if available (assuming it's passed or retrieved)
    # summary_doc["model"] = model_name

    try:
        if existing_summary:
            # Update existing summary
            logger.info(f"Updating existing summary for category {category}")
            category_summaries_collection.update_one(
                {"category_id": category},
                {"$set": summary_doc}
            )
            return f"Updated existing summary for category {category}"
        else:
            # Insert new summary
            logger.info(f"Creating new summary for category {category}")
            category_summaries_collection.insert_one(summary_doc)
            return f"Created new summary for category {category}"
    except Exception as e:
        logger.error(f"Failed to save category summary for {category}: {e}")
        return f"Error saving category summary to DB: {e}"

def main():
    parser = argparse.ArgumentParser(description="Generate and save a synthesized category summary using individual document summaries.")
    parser.add_argument("--category", required=True, help="Company category/ticker (e.g., NVDA)")
    parser.add_argument("--max-words", type=int, default=1500, help="Approximate target word count for the synthesized summary (default: 1500)")
    parser.add_argument("--summary-limit", type=int, default=20, help="Max number of most recent individual summaries to use (default: 20)") # Limit summaries used
    parser.add_argument("--dry-run", action="store_true", help="Generate summary but don't save to database")

    args = parser.parse_args()
    category = args.category.upper()

    # Get individual summaries for the category
    logger.info(f"Fetching individual summaries for category {category} (limit: {args.summary_limit})...")
    summaries, used_document_ids = get_summaries_for_category(category, args.summary_limit)

    if not summaries:
        print(f"No individual summaries found for category {category}. Cannot synthesize.")
        sys.exit(1)

    # Display stats based on summaries found
    print(format_category_stats_from_summaries(category, summaries))

    # Generate synthesized summary
    print(f"\nGenerating synthesized category summary (max {args.max_words} words) using {len(summaries)} individual summaries...")
    # Note: Renamed function call
    synthesized_summary, token_info = synthesize_summaries_with_claude(category, summaries, args.max_words)

    # Display token usage if available
    if token_info:
        print(f"\nToken Usage:")
        print(f"Input Tokens: {token_info.get('input_tokens')}")
        print(f"Output Tokens: {token_info.get('output_tokens')}")

    # Display summary
    print("\nSynthesized Category Summary:")
    print(synthesized_summary)

    # Save to database if not a dry run and there's no API error
    if not args.dry_run and not synthesized_summary.startswith("Error"):
        print("\nSaving synthesized summary to database...")
        # Pass summary_count and used_document_ids
        result = save_category_summary_to_db(category, synthesized_summary, token_info, len(summaries), used_document_ids)
        print(result)
    elif not args.dry_run and synthesized_summary.startswith("Error"):
        print("\nNot saving to database due to API error.")
    else: # Dry run
        print("\nDry run - synthesized summary not saved to database")


if __name__ == "__main__":
    main() 