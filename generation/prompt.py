"""What the model sees. SYSTEM is a first draft for AS4.1 to tune against the gold set."""
from ingest.schema import Chunk

SYSTEM = """\
You answer questions from field technicians about ABB industrial drives, using only the \
manual excerpts provided. Each excerpt is tagged with its chunk id.

Rules:
- First decide `answerable`: true only if the excerpts themselves answer this question for this \
product. Set it false when the question is about another vendor's equipment, a different product, \
or a specific fact the excerpts don't state, even if they are on a related topic. When it is \
false, leave every other field null or empty.
- Every field you fill must be supported by an excerpt, and its `cite` must be that excerpt's chunk id.
- If no excerpt supports a field, leave it null or empty. Never fill a gap from general knowledge.
- `safety_warning.verbatim` must be copied character for character from one excerpt. Do not \
paraphrase, shorten or merge warnings. If no excerpt contains a safety warning, leave it null.
- Order corrective steps as the manual orders them.
"""


def format_context(chunks: list[Chunk]) -> str:
    """Excerpts in retrieval order, each with its id and where it sits, so the model can cite it
    and knows a table row came from "Fault messages" rather than floating free."""
    blocks = []
    for c in chunks:
        where = f"{c.doc_id} p.{c.page}" + (f" — {c.parent_section_title}" if c.parent_section_title else "")
        blocks.append(f'<excerpt id="{c.chunk_id}" type="{c.chunk_type}" source="{where}">\n{c.text}\n</excerpt>')
    return "\n\n".join(blocks)


def user_message(question: str, chunks: list[Chunk]) -> str:
    return f"{format_context(chunks)}\n\nQuestion: {question}"
