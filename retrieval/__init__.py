"""Dense + BM25 retrieval over the chunk index (M2, M3).

Every retriever satisfies `retrieval.base.Retriever` and is looked up by name
through `retrieval.registry`, so the eval harness and /ask never import a
concrete retriever. Adding one is a new module plus one line in the registry.
"""
