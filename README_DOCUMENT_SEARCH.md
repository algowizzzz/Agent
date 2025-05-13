# Document-Level Semantic Search Implementation

This system implements a pure semantic search approach at the document level for searching earnings call transcripts.

## Key Features

1. **Document-Level Granularity**: Uses one vector per document instead of chunks.
2. **Pure Semantic Search**: Relies solely on semantic search without metadata filtering.
3. **High-Quality Embeddings**: Uses all-mpnet-base-v2 model for embeddings.
4. **Original Query Processing**: Uses the original user query without enhancement.

## Implementation Details

- **Vector Database**: Uses ChromaDB for vector storage and search.
- **Embedding Model**: Uses SentenceTransformer's all-mpnet-base-v2 model.
- **Document Storage**: Retrieves document content and metadata from MongoDB.
- **Document Summaries**: Uses document summaries when available for better semantic representation.

## Files

- `document_level_search.py`: Core implementation of the document-level search.
- `langchain_tools/doc_level_search_tool.py`: Langchain-compatible wrapper for the search implementation.
- `tools/earnings_call_tool.py`: Integration with the earnings call tool.
- `test_semantic_search.py`: Test script for the semantic search functionality.
- `test_agent_with_doc_search.py`: Test script for agent integration.

## Setup and Installation

1. Install the required packages:

```bash
pip install -r requirements_doc_level_search.txt
```

2. Create a `.env` file with your Anthropic API key:

```bash
python create_env.py
```

3. Run the document-level embeddings creation:

```bash
python create_embeddings.py
```

## Testing

1. Test the semantic search functionality:

```bash
python test_semantic_search.py
```

2. Test the agent integration:

```bash
python test_agent_with_doc_search.py
```

## Note on MongoDB

The system expects a MongoDB database named `earnings_transcripts` with the following collections:
- `transcripts`: Contains the actual transcript documents
- `document_summaries`: Contains pre-computed document summaries (optional)

Each document should have fields:
- `document_id`: Unique identifier for the document
- `document_name`: Name of the document
- `category_id`: Identifier for the company category
- `transcript_text`: The text content of the transcript 