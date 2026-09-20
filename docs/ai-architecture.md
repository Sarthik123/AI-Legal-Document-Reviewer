## 1. Purpose

This document defines the AI architecture for the AI Legal Document Reviewer.

The architecture is designed to provide:

- Document-grounded answers
- Plain-language legal document explanations
- Risk identification
- Missing-information detection
- Conversational document Q&A
- Evidence-backed citations
- Hallucination reduction
- Clear communication of uncertainty

The MVP will primarily use:

- Prompt engineering
- Retrieval-Augmented Generation (RAG)
- Embeddings
- Vector search
- Retrieval and reranking
- Large Language Model (LLM) generation
- AI evaluation

Fine-tuning is not required for the initial MVP and will only be considered if evaluation demonstrates a clear need for specialized model behavior.

---

## 2. Architecture Goals

The AI architecture must:

1. Ground responses in the user's uploaded document.
2. Minimize unsupported or fabricated claims.
3. Provide citations for document-based answers.
4. Preserve enough context for the LLM to understand clauses correctly.
5. Identify potential risks without presenting them as guaranteed legal conclusions.
6. Identify potential missing information while communicating uncertainty.
7. Support conversational follow-up questions.
8. Handle long documents efficiently.
9. Allow AI components to be evaluated independently.
10. Support future model and retrieval improvements without requiring a complete architectural redesign.

---

## 3. High-Level Architecture

The product uses a Retrieval-Augmented Generation (RAG) architecture.

There are two major flows.

### 3.1 Document Ingestion Flow

```text
Uploaded Document
       |
       v
Text Extraction
       |
       v
Text Cleaning
       |
       v
Chunking
       |
       v
Embedding Generation
       |
       v
Vector Database
````

### 3.2 User Query Flow

```text
User Question
       |
       v
Query Processing
       |
       v
Query Embedding
       |
       v
Vector Search
       |
       v
Candidate Retrieval
       |
       v
Reranking
       |
       v
Relevant Document Chunks
       |
       v
LLM
       |
       v
Grounded Response
       |
       v
Citations
```

---

## 4. High-Level System Architecture

```text
                         USER
                           |
                           v
                  +----------------+
                  |   Web Frontend |
                  +----------------+
                           |
                           v
                  +----------------+
                  |   Backend API  |
                  +----------------+
                     /           \
                    /             \
                   v               v
          Document Pipeline     Query Pipeline
                   |               |
                   v               v
          Text Extraction      User Question
                   |               |
                   v               v
               Chunking       Query Embedding
                   |               |
                   v               v
              Embeddings      Vector Search
                   |               |
                   v               v
            Vector Database     Reranking
                   |               |
                   |               v
                   |        Relevant Chunks
                   |               |
                   +-------+-------+
                           |
                           v
                    Prompt Assembly
                           |
                           v
                          LLM
                           |
                           v
                  Grounded Response
                           |
                           v
                       Citations
                           |
                           v
                         USER
```

---

## 5. Core AI Components

The core AI architecture consists of:

1. Large Language Model
2. Prompt Engineering
3. Document Processing
4. Chunking
5. Embeddings
6. Vector Database
7. Retrieval
8. Reranking
9. Context Assembly
10. LLM Generation
11. Citation System
12. AI Evaluation

Each component has a different responsibility.

---

## 6. Large Language Model

The Large Language Model (LLM) is responsible for generating natural-language responses using:

* User questions
* Retrieved document context
* System instructions
* Output requirements
* Conversation context where appropriate

The LLM is not treated as the source of truth for document-specific facts.

The uploaded document and retrieved document sections are the primary source of truth for document-grounded responses.

### Example

User asks:

> What are the termination conditions in this contract?

The LLM should answer using the relevant termination clauses retrieved from the uploaded document rather than relying on general knowledge.

---

## 7. Prompt Engineering Layer

Prompt engineering controls how the LLM behaves.

The system prompt establishes the product's core rules.

### Example System Instructions

```text
You are a legal document analysis assistant.

Analyze the user's uploaded document using only the
document content provided as context.

Do not invent clauses, facts, citations, statutes,
case law, or information that is not supported by
the provided context.

Clearly distinguish between:

1. Information explicitly stated in the document.
2. Reasonable interpretations of the document.
3. Information that cannot be determined from the document.

When making document-specific claims, provide the
supporting citation.

Do not present the output as legal advice or as a
guarantee of legal outcomes.

If the available document context is insufficient,
clearly state that the information cannot be determined
from the available document.
```

The production prompt will be refined through evaluation.

---

## 8. Document Ingestion Pipeline

When a user uploads a document, the document must be converted into searchable information.

### Pipeline

```text
Uploaded Document
       |
       v
File Validation
       |
       v
Text Extraction
       |
       v
Text Cleaning
       |
       v
Document Structure Detection
       |
       v
Chunking
       |
       v
Embedding Generation
       |
       v
Vector Database
```

---

## 9. File Validation

Before processing the document, the system validates:

* File type
* File size
* File integrity
* Whether the document can be processed
* Whether sufficient text can be extracted

Unsupported or corrupted documents should produce a clear error rather than entering the AI pipeline.

---

## 10. Text Extraction

The system extracts text from the uploaded document.

For the MVP, PDF documents are the primary supported format.

The extraction layer should preserve useful document structure where possible, including:

* Page numbers
* Headings
* Sections
* Paragraphs
* Clause boundaries

This information is important because citations must eventually point back to meaningful document locations.

---

## 11. Text Cleaning

Extracted text may contain:

* Extra whitespace
* Broken line breaks
* Repeated headers
* Repeated footers
* Encoding issues
* Page artifacts

The system cleans the extracted text before chunking.

Cleaning must not remove information that changes the legal meaning of the document.

---

## 12. Chunking

Chunking divides the document into smaller meaningful sections.

A chunk should contain enough surrounding context for the LLM to understand the relevant clause.

### Poor chunking

```text
Chunk 1:
"The agreement may be terminated..."

Chunk 2:
"...by either party upon..."

Chunk 3:
"...thirty days written notice."
```

This can separate parts of the same clause.

### Preferred approach

The system should attempt to preserve complete clauses or logically connected sections.

### Chunk Metadata

Each chunk should store metadata such as:

```text
document_id
chunk_id
page_number
section
clause
text
```

This metadata enables accurate retrieval and citations.

---

## 13. Embeddings

Each document chunk is converted into an embedding.

An embedding represents the semantic characteristics of text as a numerical vector.

The embedding allows the system to compare the meaning of:

* A user's question
* Document chunks

Conceptually:

```text
Document Chunk
      |
      v
Embedding Model
      |
      v
Numerical Vector
```

The same process is applied to the user's question.

---

## 14. Vector Database

The vector database stores:

* Document chunk
* Embedding
* Document ID
* Chunk ID
* Page number
* Section information
* Other relevant metadata

Conceptually:

```text
+--------------------------------------+
| Vector Database                      |
+--------------------------------------+
| Chunk Text                           |
| Embedding                            |
| Document ID                          |
| Chunk ID                             |
| Page Number                          |
| Section                              |
+--------------------------------------+
```

The vector database allows the system to retrieve document sections that are semantically relevant to a user's question.

The exact vector database technology will be selected during technical design.

---

## 15. Query Processing

When a user asks a question, the question enters the retrieval pipeline.

Example:

```text
User:
"What happens if I terminate the contract early?"
```

The system:

1. Receives the question.
2. Converts the question into an embedding.
3. Searches the vector database.
4. Retrieves relevant document chunks.
5. Reranks the retrieved chunks.
6. Sends the most relevant context to the LLM.

---

## 16. Retrieval

Retrieval finds potentially relevant document chunks.

For example:

```text
User Question
      |
      v
Query Embedding
      |
      v
Vector Search
      |
      +---- Chunk A
      +---- Chunk B
      +---- Chunk C
      +---- Chunk D
```

Retrieval should return multiple candidates rather than relying on a single chunk.

The retrieval strategy may later combine semantic search with keyword or metadata-based filtering where useful.

---

## 17. Reranking

Initial vector retrieval may return several potentially relevant chunks.

A reranking step evaluates those candidates against the specific question and orders them by relevance.

```text
Vector Search
     |
     v
Candidate Chunks
     |
     v
Reranker
     |
     v
Most Relevant Chunks
```

This improves the quality of the context supplied to the LLM.

---

## 18. Context Assembly

The system builds the LLM context from the most relevant retrieved chunks.

Conceptually:

```text
System Instructions
        +
User Question
        +
Retrieved Document Context
        +
Relevant Metadata
        |
        v
       LLM
```

The context should contain enough information to answer the question while avoiding unnecessary document content.

---

## 19. Generation

The LLM generates the final response using the supplied context.

Example:

```text
Retrieved Context:

"Either party may terminate this agreement by
providing thirty days written notice..."

User:

"What is the termination notice period?"

LLM:

"The agreement requires 30 days' written notice
for termination."
```

The response should reference the supporting document location.

---

## 20. Citation Architecture

Citations are a core trust feature.

Each retrieved chunk should maintain its source metadata.

For example:

```text
Document ID: contract_123
Chunk ID: chunk_47
Page: 8
Section: Termination
```

When the LLM makes a document-grounded claim, the application should associate the response with the supporting source.

Example UI:

```text
The agreement requires 30 days' written notice
for termination.

[Page 8, Termination Clause]
```

The citation system should allow the user to navigate back to the relevant document location where technically feasible.

---

## 21. Grounding and Hallucination Control

The system must distinguish between three types of information.

### 21.1 Grounded Information

Information directly supported by retrieved document content.

### 21.2 Interpretation

A reasonable explanation or interpretation based on the document.

### 21.3 Unsupported Information

Information that cannot be established from the available document.

The system should not fabricate:

* Clauses
* Contract terms
* Parties
* Dates
* Legal authorities
* Citations
* Obligations
* Rights
* Missing information

If the document does not contain enough information, the system should communicate uncertainty.

---

## 22. Risk Detection Architecture

Risk detection is a dedicated AI task.

The system should analyze relevant document sections for potential issues such as:

* Unusually broad obligations
* One-sided termination rights
* Significant payment obligations
* Automatic renewal
* Liability provisions
* Indemnification provisions
* Restrictive obligations
* Ambiguous terms
* Unfavourable notice periods

The output should not claim that a clause is definitively illegal or legally invalid.

### Example

```text
Potential Risk

Category:
Termination

Issue:
The agreement allows one party to terminate with
30 days' notice while providing different
termination conditions for the other party.

Why it may matter:
This may create an imbalance in termination rights.

Source:
Page 8, Section 12 - Termination
```

Risk detection should connect identified risks to supporting document evidence where available.

---

## 23. Missing Information Detection

Missing-information detection is different from risk detection.

A risk can often be associated with an existing clause.

A missing item may have no corresponding clause in the document.

### Example

```text
Potential Missing Information

The agreement does not appear to specify a clear
process for resolving disputes.

Why it may matter:
Without a defined dispute-resolution process,
the parties may have less clarity about how
disputes should be handled.

Status:
Not found in the reviewed document.
```

The system must avoid claiming that something is definitely missing merely because retrieval failed.

Omission detection should consider the document as a whole where possible.

---

## 24. Conversational Q&A

Conversational Q&A is part of the MVP.

Users can ask follow-up questions about the uploaded document.

Example:

```text
User:
"What is the termination period?"

AI:
"30 days' written notice. [Page 8]"

User:
"Can either party do that?"

AI:
"The termination clause appears to provide this
right to both parties. [Page 8]"
```

Conversation history may be included in the prompt when necessary.

However, previous conversation messages must not override the uploaded document as the source of truth.

---

## 25. Multi-Stage AI Architecture

Different AI tasks should be logically separated rather than using one prompt for everything.

### Stage 1: Document Understanding

Extract and structure document content.

### Stage 2: Summary

Generate a high-level document summary.

### Stage 3: Risk Analysis

Identify potential risk areas.

### Stage 4: Missing Information Analysis

Identify potentially important omissions.

### Stage 5: Question Answering

Answer user questions using retrieved document context.

### Stage 6: Citation/Evidence Association

Associate document-grounded claims with supporting document locations.

---

## 26. Recommended MVP AI Flow

```text
                 UPLOAD DOCUMENT
                        |
                        v
                Extract Document Text
                        |
                        v
                     Chunk
                        |
                        v
                   Embeddings
                        |
                        v
                 Vector Database
                        |
        +---------------+---------------+
        |               |               |
        v               v               v
     Summary        Risk Analysis   Missing Info
        |               |               |
        +---------------+---------------+
                        |
                        v
                 User Q&A Interface
                        |
                        v
                  Query Embedding
                        |
                        v
                   Retrieval
                        |
                        v
                   Reranking
                        |
                        v
                 Context Assembly
                        |
                        v
                       LLM
                        |
                        v
              Answer + Citations
```

---

## 27. Prompting vs RAG vs Fine-Tuning

Different techniques solve different problems.

| Requirement                                          | Primary Approach                                                |
| ---------------------------------------------------- | --------------------------------------------------------------- |
| Control AI behavior                                  | Prompting                                                       |
| Answer from uploaded document                        | RAG                                                             |
| Provide document citations                           | RAG + source metadata                                           |
| Reduce hallucinations                                | RAG + prompting + evaluation                                    |
| Explain legal language simply                        | Prompting                                                       |
| Retrieve relevant clauses                            | Embeddings + vector search                                      |
| Improve retrieval relevance                          | Reranking                                                       |
| Specialized model behavior                           | Potential future fine-tuning                                    |
| Improve model performance based on measured failures | Evaluation first, then prompting/RAG/fine-tuning as appropriate |

---

## 28. Why Fine-Tuning Is Not Required for MVP

The product's primary challenge is not teaching the model the contents of every user's document.

Each user can upload different documents.

Therefore, the product needs a mechanism to provide relevant document information to the model dynamically.

RAG solves this problem.

Fine-tuning may become useful later for tasks such as:

* Consistent risk classification
* Specialized document classification
* Structured output behavior
* Domain-specific task performance

Fine-tuning should only be introduced if evaluation demonstrates that prompting and RAG are insufficient.

---

## 29. AI Safety and Legal Boundaries

The system should clearly communicate that it provides document analysis and information, not professional legal advice.

The system should:

* Avoid claiming to be a lawyer.
* Avoid guaranteeing legal outcomes.
* Communicate uncertainty.
* Encourage professional legal review for high-risk or complex situations.
* Avoid fabricating legal authorities.
* Avoid unsupported legal conclusions.
* Protect user documents and privacy.

The product should not be positioned as a replacement for a qualified legal professional.

---

## 30. Failure Handling

The AI pipeline must handle failures at multiple stages.

### 30.1 Document Extraction Failure

```text
Unable to process this document.
Please check that the file is valid and try again.
```

### 30.2 Retrieval Failure

```text
I could not find enough relevant information
in the document to answer this question.
```

### 30.3 Insufficient Context

```text
The uploaded document does not provide enough
information to determine this.
```

### 30.4 LLM Failure

```text
We couldn't generate an analysis right now.
Please try again.
```

The system should fail transparently rather than generate unsupported content.

---

## 31. AI Evaluation Architecture

AI quality must be evaluated independently from normal software testing.

Evaluation should measure:

### Retrieval Quality

Does the system retrieve the correct document sections?

### Groundedness

Are responses supported by retrieved document content?

### Citation Accuracy

Do citations actually support the claims being made?

### Answer Quality

Does the response correctly answer the user's question?

### Risk Detection Quality

Does the system identify relevant potential risks while avoiding unsupported claims?

### Missing Information Quality

Does the system identify meaningful omissions without treating retrieval failure as proof of absence?

### Hallucination Rate

How frequently does the system generate unsupported information?

### User Trust

Do users understand and trust the evidence provided by the system?

---

## 32. Evaluation Loop

```text
AI Output
   |
   v
Evaluation
   |
   v
Identify Failure
   |
   +---- Prompt Problem
   |
   +---- Retrieval Problem
   |
   +---- Chunking Problem
   |
   +---- Reranking Problem
   |
   +---- Model Problem
   |
   +---- Product/UI Problem
   |
   v
Improve Component
   |
   v
Evaluate Again
```

The system should be improved based on measured failure patterns rather than assumptions.

---

## 33. Observability

The production system should record appropriate AI pipeline metrics without unnecessarily storing sensitive document content.

Potential metrics include:

* Document processing success rate
* Processing duration
* Retrieval latency
* Number of retrieved chunks
* Reranking latency
* LLM latency
* Token usage
* AI request failure rate
* Citation coverage
* Evaluation scores
* User feedback

Sensitive document content should not be logged unnecessarily.

---

## 34. Privacy and Data Handling

Legal documents may contain sensitive information.

The architecture should therefore support:

* Secure document upload
* Encryption in transit
* Encryption at rest
* Access control
* User-level document isolation
* Secure deletion
* Limited retention
* Protection of API credentials
* Minimal sensitive-data logging

The exact retention policy will be finalized during production-readiness planning.

---

## 35. Scalability

The architecture should allow individual AI components to scale independently.

Potential scalable components include:

* Document processing workers
* Embedding generation
* Vector database
* API servers
* LLM requests

Long-running document processing should preferably be handled asynchronously rather than blocking the user's request indefinitely.

---

## 36. Technology Selection Principles

Technology choices should be based on:

1. Reliability
2. AI quality
3. Security
4. Cost
5. Developer productivity
6. Scalability
7. Ease of replacement

The MVP should avoid unnecessary infrastructure complexity.

The architecture should use managed services where they reduce operational overhead without creating unacceptable vendor lock-in.

Exact technologies will be finalized in the Technical Design document.

---

## 37. MVP Architecture Decision

The MVP will use:

```text
LLM
+
Prompt Engineering
+
RAG
+
Embeddings
+
Vector Database
+
Retrieval
+
Reranking
+
Citation Metadata
+
AI Evaluation
```

The MVP will not require fine-tuning unless evaluation demonstrates a measurable need.

---

## 38. Architecture Principles

### 38.1 Ground Before Generating

Provide relevant document evidence before asking the model to answer.

### 38.2 Evidence Over Confidence

A confident answer without supporting evidence is not considered reliable.

### 38.3 Retrieval Is Not Truth

Retrieved information must still be evaluated by the model and application.

### 38.4 RAG Does Not Eliminate Hallucinations

RAG reduces the likelihood of unsupported answers but cannot guarantee perfect accuracy.

### 38.5 Fail Transparently

When the system does not have enough information, it should say so.

### 38.6 Evaluate Before Optimizing

Changes to prompts, retrieval, chunking, models, or fine-tuning should be validated through evaluation.

### 38.7 Protect User Documents

Legal documents should be treated as sensitive information throughout the architecture.

---

## 39. Future Architecture Improvements

Potential future improvements include:

* Hybrid search
* Improved document structure extraction
* Advanced chunking
* Query rewriting
* Multi-query retrieval
* Improved reranking
* Document comparison
* Multi-document analysis
* Clause libraries
* External legal research
* Domain-specific models
* Fine-tuned models
* Agentic workflows
* Microsoft Word integration
* Organization-level knowledge bases

These features are not required for the MVP.

---

## 40. Final Architecture Summary

The AI Legal Document Reviewer uses a RAG-centered architecture.

The core flow is:

```text
DOCUMENT
   |
   v
EXTRACT
   |
   v
CHUNK
   |
   v
EMBED
   |
   v
VECTOR DATABASE
   |
   |
USER QUESTION
   |
   v
QUERY EMBEDDING
   |
   v
RETRIEVAL
   |
   v
RERANKING
   |
   v
RELEVANT DOCUMENT CONTEXT
   |
   v
PROMPT + CONTEXT
   |
   v
LLM
   |
   v
GROUNDED ANSWER
   |
   v
CITATIONS
   |
   v
USER
```

The fundamental architecture decision is:

**Prompting controls behavior → RAG provides document knowledge → Retrieval finds relevant evidence → Reranking improves relevance → LLM generates the response → Citations allow verification → Evaluation measures whether the system actually works.**
