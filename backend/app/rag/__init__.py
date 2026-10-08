"""Retrieval-augmented generation pipeline.

Chunking, embeddings, vector search, prompt construction, and citations
will live here. Retrieval must apply the caller's document authorization
scope rather than searching every stored chunk.

The later check belongs beside the current user dependency: load the user,
resolve the documents that user may read, and pass those ids into the
retriever. A role alone is not a document grant.
"""
