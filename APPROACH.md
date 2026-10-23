# Approach Document & Architecture Decision Log

## Extraction & Hierarchy Strategy
We used `pdfplumber` to process positional layout text. Tree depth is extracted using regex pattern matching on hierarchical section numbering (e.g., `1.1`, `2.1.1.1`). Parent-child relationships are built dynamically using an active stack based on heading levels.

## Node Content Hashing & Versioning Strategy
Every node generates a SHA-256 hash derived from `heading + body_text`. When $V_2$ is ingested, nodes are matched across versions via `node_path` (e.g., `3.2`). Hash variations flag text modifications without deleting the logical history of $V_1$.

## Decision Log

1. **What's the one part of this system most likely to silently give wrong results without erroring? How would you catch it?**
   *Hierarchy mis-parenting during parsing.* If a section title lacks standard dot-number formatting, it flattens into normal body text, silently assigning nested child nodes to the wrong parent. I would catch this using structural tree-validation scripts that assert strict section-number continuity (e.g., `1.2.1` must have `1.2` as its active parent).

2. **Where did you choose simplicity over correctness because of time, and what would break first if this went to production as-is?**
   *Using path-based matching (`node_path`) for node versioning instead of fuzzy text alignment.* If a new section is inserted at the top of $V_2$, all subsequent section numbers shift (e.g., Section 3.2 becomes 3.3). In production, this would cause every node to mismatch and mark all historical test cases as `STALE`.

3. **Name one input (to your parser, your versioning matcher, or your LLM call) that you did not handle, and what your system does when it sees it.**
   *Multi-page complex tables with merged cells.* The parser flattens the table contents sequentially into standard string body text. It does not crash, but row-column alignment metadata is lost in the extracted body text.
   