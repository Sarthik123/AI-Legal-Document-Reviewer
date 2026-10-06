Yes. Next is **Technical Design**, in exactly the same format: **one complete `.md` file with continuous numbered sections**.

Create:

```text
docs/technical-design.md
```

Then copy the **entire block below** into it.

````markdown
# Technical Design

## 1. Purpose

This document defines the technical architecture and implementation design for the AI Legal Document Reviewer MVP.

It translates the product requirements, AI architecture, and UX design into an implementable software system.

The technical design covers:

- Frontend architecture
- Backend architecture
- Database design
- Document storage
- Document processing
- AI/RAG pipeline
- Authentication
- API design
- Security
- Error handling
- Testing
- Deployment
- Monitoring
- Scalability

The design prioritizes simplicity for the MVP while keeping the architecture extensible for future product growth.

---

## 2. Technical Design Goals

The system should:

1. Support secure user authentication.
2. Allow users to upload legal documents.
3. Process uploaded documents reliably.
4. Extract and store document text.
5. Generate embeddings for document chunks.
6. Store embeddings for semantic retrieval.
7. Generate document summaries.
8. Detect potential risks.
9. Detect potential missing information.
10. Support document-grounded Q&A.
11. Provide citations.
12. Protect user documents and personal data.
13. Handle failures gracefully.
14. Support automated testing.
15. Be deployable using common cloud infrastructure.
16. Allow AI components to be changed independently where practical.

---

## 3. Recommended Technology Stack

The MVP will use the following technology direction.

| Layer | Technology |
|---|---|
| Frontend | Next.js / React |
| Frontend Language | TypeScript |
| Backend | Python / FastAPI |
| Database | PostgreSQL |
| Vector Search | pgvector |
| Document Storage | Object storage |
| AI/LLM | LLM API provider |
| Embeddings | Embedding model/API |
| Authentication | Managed authentication or application-managed authentication |
| Background Processing | Background worker system |
| API Format | REST/JSON |
| Deployment | Cloud-hosted services |
| Version Control | Git + GitHub |

Exact library versions and service providers will be finalized during implementation.

---

## 4. System Architecture

```text
                         USER
                           |
                           v
                  +----------------+
                  |   Next.js UI   |
                  +----------------+
                           |
                           v
                  +----------------+
                  |   FastAPI API  |
                  +----------------+
                    /      |       \
                   /       |        \
                  v        v         v
          Authentication  Database   AI Services
                  |        |         |
                  |        |         +---- LLM
                  |        |         |
                  |        |         +---- Embeddings
                  |        |
                  |        +---- PostgreSQL
                  |        |
                  |        +---- pgvector
                  |
                  v
             User Access

                           |
                           v
                  Document Processing
                           |
              +------------+------------+
              |            |            |
              v            v            v
        Object Storage  Text Parser  Background Worker
````

---

## 5. Application Components

The system is divided into the following major components:

```text
1. Frontend
2. Backend API
3. Authentication
4. Document Storage
5. Document Processing Service
6. Database
7. Vector Search
8. AI Service
9. Background Worker
10. Monitoring and Logging
```

Each component should have a clearly defined responsibility.

---

## 6. Frontend Architecture

The frontend provides the user-facing application.

Recommended technology:

* Next.js
* React
* TypeScript

### Main frontend areas

```text
Frontend
|
+-- Authentication
|
+-- Dashboard
|
+-- Document Upload
|
+-- Document Workspace
|    |
|    +-- Overview
|    +-- Summary
|    +-- Risks
|    +-- Missing Information
|    +-- Q&A
|    +-- Document Viewer
|
+-- Account
|
+-- Error / Empty States
```

The frontend should not contain sensitive AI credentials.

---

## 7. Frontend State Management

The frontend will need to manage:

* Authentication state
* Current user
* Current document
* Upload status
* Processing status
* Analysis results
* Q&A conversation
* UI state
* Error state

The MVP should avoid unnecessary state-management complexity.

Local component state and lightweight shared state should be preferred where sufficient.

---

## 8. Backend Architecture

The backend provides the application's core business logic.

Recommended technology:

* Python
* FastAPI

The backend is responsible for:

* Authentication integration
* User authorization
* Document management
* Upload handling
* Document processing
* AI orchestration
* RAG retrieval
* Q&A
* Analysis generation
* Citation handling
* Database operations
* Error handling

---

## 9. Backend Service Structure

A logical backend structure:

```text
backend/
|
+-- app/
|   |
|   +-- api/
|   |   +-- auth.py
|   |   +-- documents.py
|   |   +-- analysis.py
|   |   +-- chat.py
|   |
|   +-- services/
|   |   +-- document_service.py
|   |   +-- extraction_service.py
|   |   +-- chunking_service.py
|   |   +-- embedding_service.py
|   |   +-- retrieval_service.py
|   |   +-- analysis_service.py
|   |   +-- llm_service.py
|   |
|   +-- models/
|   +-- schemas/
|   +-- database/
|   +-- workers/
|   +-- config/
|   +-- utils/
|
+-- tests/
|
+-- requirements.txt
```

The exact folder structure may evolve during implementation.

---

## 10. API Architecture

The backend exposes REST APIs to the frontend.

Example API groups:

```text
/api/auth
/api/documents
/api/analysis
/api/chat
/api/users
```

The frontend communicates with the backend through authenticated API requests.

---

## 11. Authentication

Users must authenticate before accessing private documents.

Authentication should support:

* Account creation
* Login
* Logout
* Session management
* Password recovery where applicable

The authentication system should use established security practices rather than implementing password security from scratch.

---

## 12. Authorization

Authentication determines who the user is.

Authorization determines what the user is allowed to access.

Every document request must verify that the authenticated user owns or has permission to access the document.

Example:

```text
User A
  |
  v
Request Document 123
  |
  v
Backend checks ownership
  |
  +---- Owner ----> Allow
  |
  +---- Not Owner -> Deny
```

A document ID alone must never be sufficient to access a document.

---

## 13. Document Upload Architecture

The document upload flow:

```text
User
 |
 v
Frontend
 |
 v
Backend
 |
 v
Validate File
 |
 v
Store Original File
 |
 v
Create Document Record
 |
 v
Start Processing
 |
 v
Return Processing Status
```

The upload endpoint should not perform all document processing synchronously if processing can take significant time.

---

## 14. Document Storage

Original documents should be stored in secure object storage rather than directly inside the relational database.

The database stores metadata and references to the stored file.

Example:

```text
Object Storage
|
+-- user_123/
     |
     +-- document_456.pdf
```

The database may store:

```text
document_id
user_id
file_name
file_type
storage_location
file_size
created_at
processing_status
```

---

## 15. Document Processing Pipeline

After upload:

```text
Uploaded File
     |
     v
Validation
     |
     v
Text Extraction
     |
     v
Text Cleaning
     |
     v
Structure Detection
     |
     v
Chunking
     |
     v
Embedding Generation
     |
     v
Vector Storage
     |
     v
Document Analysis
     |
     v
Ready
```

The processing system should update the document status at each major stage.

---

## 16. Processing Status

Documents should have explicit processing states.

Example:

```text
UPLOADED
PROCESSING
EXTRACTING_TEXT
CHUNKING
GENERATING_EMBEDDINGS
INDEXING
ANALYZING
READY
FAILED
```

The frontend uses these states to display appropriate progress information.

---

## 17. PDF Text Extraction

The MVP primarily supports PDF documents.

The extraction service should:

1. Open the uploaded PDF.
2. Extract text.
3. Preserve page boundaries where possible.
4. Detect extraction failures.
5. Store extracted content for processing.

The extraction system should preserve page metadata because citations depend on document location.

---

## 18. Document Structure

The system should represent extracted document content using structured metadata.

Example:

```text
Document
|
+-- Page 1
|    +-- Section
|    +-- Paragraph
|
+-- Page 2
|    +-- Section
|    +-- Clause
|
+-- Page 3
     +-- Section
     +-- Clause
```

Where available, the system should preserve:

* Page number
* Section
* Clause
* Paragraph
* Text position

---

## 19. Chunking Implementation

The chunking service converts extracted text into searchable chunks.

Each chunk should contain:

```text
chunk_id
document_id
text
page_start
page_end
section
clause
chunk_index
```

Chunking should prioritize semantic boundaries.

Examples of useful boundaries:

* Headings
* Clauses
* Paragraph groups
* Sections

The implementation may use controlled overlap between chunks when necessary to preserve context.

---

## 20. Embedding Generation

Each chunk is sent to the selected embedding model.

Example:

```text
Chunk
 |
 v
Embedding Service
 |
 v
Vector
 |
 v
Database
```

The embedding model should be consistent between document indexing and user query embedding.

If the embedding model changes later, existing vectors may need to be regenerated.

---

## 21. Vector Storage

The MVP can use PostgreSQL with pgvector for vector storage and similarity search.

This keeps relational document metadata and vector data within a relatively simple architecture.

Conceptually:

```text
PostgreSQL
|
+-- Users
+-- Documents
+-- Chunks
+-- Analyses
+-- Conversations
+-- Messages
|
+-- Vector Embeddings
```

The vector database layer should remain abstracted behind the retrieval service so it can be replaced later if necessary.

---

## 22. Retrieval Architecture

When a user asks a question:

```text
User Question
      |
      v
Query Embedding
      |
      v
Vector Search
      |
      v
Candidate Chunks
      |
      v
Metadata Filtering
      |
      v
Reranking
      |
      v
Top Context
```

Retrieval must be restricted to documents the current user is authorized to access.

---

## 23. Retrieval Parameters

The retrieval system should support configurable parameters such as:

* Number of candidates
* Number of final chunks
* Similarity threshold
* Metadata filters
* Reranking settings

These values should be configurable rather than hard-coded throughout the application.

Final values should be determined through evaluation.

---

## 24. Reranking

The reranking layer improves the ordering of retrieved chunks.

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
Best Relevant Chunks
```

The reranker should evaluate relevance to the user's specific question.

If reranking is not necessary for the earliest MVP implementation, it can initially be implemented behind an interface and enabled after baseline retrieval evaluation.

---

## 25. Prompt Assembly

The AI service assembles:

```text
System Instructions
+
Conversation Context
+
User Question
+
Retrieved Document Context
+
Citation Metadata
```

The resulting prompt is sent to the LLM.

The system should enforce context boundaries so that unrelated document content is not unnecessarily included.

---

## 26. LLM Service

The LLM service should provide a single internal interface to the rest of the application.

Example:

```text
generate_answer(
    system_prompt,
    user_question,
    retrieved_context,
    conversation_history
)
```

This abstraction allows the underlying model provider to be changed without rewriting the entire application.

---

## 27. AI Analysis Services

The backend should logically separate different AI tasks.

```text
AI Services
|
+-- Summary Service
|
+-- Risk Analysis Service
|
+-- Missing Information Service
|
+-- Question Answering Service
|
+-- Citation Service
```

Each service should have its own prompt and output expectations.

This makes evaluation and debugging easier.

---

## 28. Structured AI Outputs

AI responses should use structured outputs where practical.

For example, risk analysis can follow:

```json
{
  "category": "Termination",
  "title": "Potential termination imbalance",
  "explanation": "The termination rights appear different for the two parties.",
  "source_chunks": ["chunk_47"],
  "confidence": "medium"
}
```

The exact production schema will be finalized during implementation.

The application should validate AI-generated structured data before displaying it to users.

---

## 29. Citation Data Model

Each citation should connect an AI claim to document evidence.

Example:

```text
Citation
|
+-- citation_id
+-- document_id
+-- chunk_id
+-- page_number
+-- section
+-- source_text
```

The citation system should not rely solely on text generated by the LLM to determine the source.

Source metadata should come from the retrieval/application layer.

---

## 30. Conversational Q&A Architecture

The Q&A flow:

```text
User Question
      |
      v
Authentication
      |
      v
Document Authorization
      |
      v
Conversation Context
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
Prompt Assembly
      |
      v
LLM
      |
      v
Response Validation
      |
      v
Citation Association
      |
      v
Frontend
```

The conversation should remain associated with a specific document.

---

## 31. Summary Generation

The summary service analyzes the document and generates a structured summary.

Potential output:

```text
Document Type
Key Parties
Purpose
Duration
Payment Terms
Termination
Renewal
Important Obligations
Potential Areas Requiring Attention
```

The summary should be generated using document context rather than unrestricted model knowledge.

---

## 32. Risk Analysis Implementation

Risk analysis should:

1. Identify relevant clauses.
2. Analyze potential issues.
3. Classify the issue.
4. Explain why it may matter.
5. Associate supporting evidence.
6. Communicate uncertainty.

The system should avoid generating unsupported legal conclusions.

---

## 33. Missing Information Analysis

Missing-information analysis should not depend solely on failed retrieval.

The system should consider the document at an appropriate broader level.

Example process:

```text
Document
   |
   v
Identify Expected Information
   |
   v
Search Document
   |
   v
Check Evidence
   |
   v
Potentially Missing Information
   |
   v
Generate Explanation
```

The system should distinguish:

* Not found
* Not clearly specified
* Ambiguous
* Present

This reduces false omission claims.

---

## 34. Database Design

The MVP database should contain core entities.

```text
Users
Documents
DocumentChunks
Analyses
Conversations
Messages
Citations
```

Relationships:

```text
User
 |
 +---- Documents
          |
          +---- DocumentChunks
          |
          +---- Analyses
          |
          +---- Conversations
                    |
                    +---- Messages

Analyses
 |
 +---- Citations
```

---

## 35. Users Table

Example fields:

```text
users
--------------------------------
id
email
password_hash / auth_provider_id
created_at
updated_at
```

If a managed authentication provider is used, sensitive authentication fields may be managed outside the application's database.

---

## 36. Documents Table

Example:

```text
documents
--------------------------------
id
user_id
file_name
file_type
file_size
storage_path
processing_status
created_at
updated_at
deleted_at
```

`user_id` establishes document ownership.

---

## 37. Document Chunks Table

Example:

```text
document_chunks
--------------------------------
id
document_id
chunk_index
text
page_start
page_end
section
clause
embedding
created_at
```

The `embedding` field stores the vector used for semantic search.

---

## 38. Analyses Table

Example:

```text
analyses
--------------------------------
id
document_id
analysis_type
status
result
model_identifier
created_at
updated_at
```

`analysis_type` may include:

```text
SUMMARY
RISK
MISSING_INFORMATION
```

The result should be stored in a structured format where practical.

---

## 39. Conversations and Messages

### Conversations

```text
conversations
--------------------------------
id
user_id
document_id
created_at
updated_at
```

### Messages

```text
messages
--------------------------------
id
conversation_id
role
content
created_at
```

Roles may include:

```text
USER
ASSISTANT
```

Citation references can be associated with assistant messages.

---

## 40. API Endpoints

The MVP may expose endpoints such as:

### Authentication

```text
POST /api/auth/signup
POST /api/auth/login
POST /api/auth/logout
```

### Documents

```text
POST   /api/documents
GET    /api/documents
GET    /api/documents/{document_id}
DELETE /api/documents/{document_id}
GET    /api/documents/{document_id}/status
```

### Analysis

```text
GET /api/documents/{document_id}/summary
GET /api/documents/{document_id}/risks
GET /api/documents/{document_id}/missing-information
```

### Chat

```text
POST /api/documents/{document_id}/chat
GET  /api/documents/{document_id}/conversations
GET  /api/conversations/{conversation_id}
```

Exact endpoint naming may be refined during implementation.

---

## 41. API Request Validation

Every API endpoint should validate:

* Authentication
* Authorization
* Request format
* Required fields
* File type
* File size
* Resource ownership
* Input length
* Allowed operations

Invalid requests should return consistent error responses.

---

## 42. API Error Format

The API should use a consistent error structure.

Example:

```json
{
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "The requested document could not be found."
  }
}
```

Internal stack traces and sensitive implementation details should not be returned to users.

---

## 43. Background Processing

Document processing and expensive AI operations should be capable of running asynchronously.

Example:

```text
Upload Request
      |
      v
Create Document
      |
      v
Queue Processing Job
      |
      v
Return Response
      |
      v
Background Worker
      |
      +-- Extract
      +-- Chunk
      +-- Embed
      +-- Index
      +-- Analyze
      |
      v
Update Status
```

This prevents long-running AI processing from unnecessarily blocking the API request.

---

## 44. Background Job Reliability

Background jobs should support:

* Retry
* Failure tracking
* Idempotency where practical
* Status updates
* Error logging

A failed job should not leave a document permanently stuck in a processing state.

---

## 45. Security Architecture

Security requirements include:

* HTTPS
* Secure authentication
* Authorization checks
* Secure file storage
* Encryption at rest
* Encryption in transit
* Secret management
* Input validation
* Rate limiting
* Secure API access
* User-level data isolation

Security should be applied across the entire system rather than only at the frontend.

---

## 46. Document Isolation

Documents must be isolated between users.

Example:

```text
User A
 |
 +-- Document A1
 +-- Document A2

User B
 |
 +-- Document B1
 +-- Document B2
```

A retrieval request from User A must never retrieve chunks belonging to User B.

The user authorization filter must therefore be applied before document context reaches the AI model.

---

## 47. API Security

API credentials and secrets must never be stored directly in frontend code.

Secrets should be stored using environment variables or a dedicated secret-management system.

Examples:

```text
LLM_API_KEY
DATABASE_URL
STORAGE_SECRET
AUTH_SECRET
```

Actual secret values must not be committed to GitHub.

---

## 48. Environment Configuration

The application should separate environments.

Recommended:

```text
Development
Testing
Production
```

Example:

```text
.env.local
.env.test
Production environment variables
```

Sensitive environment files should be excluded from Git.

The repository should include a safe template such as:

```text
.env.example
```

containing variable names without secret values.

---

## 49. Logging

The backend should log useful operational events.

Examples:

* Request failures
* Document processing failures
* AI request failures
* Processing duration
* Background job failures
* Authentication failures
* System errors

Logs should avoid unnecessary sensitive document content.

---

## 50. Monitoring

Production monitoring should track:

### Application

* API availability
* Error rate
* Response time
* Request volume

### Document Processing

* Processing success rate
* Processing duration
* Extraction failures
* Queue failures

### AI

* LLM latency
* Token usage
* AI errors
* Retrieval latency
* Citation coverage
* Evaluation results

### Product

* Documents uploaded
* Documents analyzed
* Questions asked
* Active users

---

## 51. Rate Limiting

Rate limiting should protect the application from:

* Abuse
* Excessive API usage
* Accidental request loops
* Excessive AI costs

Limits may be applied to:

* Login attempts
* Document uploads
* AI requests
* Chat requests

Limits should be configurable.

---

## 52. File Security

Uploaded files should be treated as untrusted input.

The system should validate:

* File extension
* MIME type
* File size
* File integrity

Where appropriate, uploaded files should also be checked for malicious content before processing.

The application should never execute uploaded document content as code.

---

## 53. Data Deletion

When a user deletes a document, the system should remove or schedule deletion of:

1. Original file
2. Extracted content
3. Document chunks
4. Embeddings
5. AI analyses
6. Related conversations
7. Citation references

Deletion behavior should follow the product's finalized retention policy.

---

## 54. Testing Strategy

Testing should cover four major areas:

```text
Unit Tests
Integration Tests
End-to-End Tests
AI Evaluation
```

Each addresses different failure types.

---

## 55. Unit Testing

Unit tests should test individual components.

Examples:

* Text cleaning
* Chunking
* Metadata extraction
* Input validation
* Authorization logic
* API schema validation
* Citation formatting
* Database operations

Example:

```text
Input:
A document containing three clauses.

Expected:
Correct chunk boundaries and metadata.
```

---

## 56. Integration Testing

Integration tests should verify interactions between components.

Examples:

```text
Upload
  |
  v
Storage
  |
  v
Database
  |
  v
Processing
  |
  v
Vector Search
```

Integration testing should verify that data flows correctly across system boundaries.

---

## 57. End-to-End Testing

End-to-end tests should simulate real user workflows.

Example:

```text
Sign Up
   |
   v
Login
   |
   v
Upload PDF
   |
   v
Wait for Processing
   |
   v
View Summary
   |
   v
View Risk
   |
   v
Open Citation
   |
   v
Ask Question
   |
   v
Receive Grounded Answer
```

---

## 58. AI Evaluation Testing

Traditional software tests cannot fully determine whether an AI response is good.

AI evaluation should test:

* Retrieval quality
* Groundedness
* Citation accuracy
* Answer quality
* Risk detection
* Missing information detection
* Hallucination rate

Evaluation datasets should contain representative legal-document examples.

---

## 59. AI Regression Testing

Whenever changes are made to:

* Prompt
* LLM
* Embedding model
* Chunking
* Retrieval
* Reranking
* AI output format

the evaluation dataset should be rerun.

This prevents an improvement in one area from silently degrading another.

---

## 60. Performance Requirements

The application should measure:

* Page load time
* API latency
* Upload latency
* Document processing time
* Retrieval latency
* LLM latency
* Total analysis time

Exact performance targets should be finalized after baseline measurements.

The system should prioritize a responsive user experience without sacrificing AI quality.

---

## 61. Cost Management

AI costs can become significant.

The system should monitor:

* Input tokens
* Output tokens
* Embedding usage
* Number of AI calls
* Document processing volume
* Storage usage

Cost optimization strategies may include:

* Avoiding unnecessary repeated analysis
* Caching reusable results
* Limiting unnecessary context
* Selecting appropriate models for each task
* Controlling maximum document size
* Applying usage limits where appropriate

---

## 62. Scalability Architecture

The architecture should allow individual components to scale independently.

```text
Frontend
   |
   v
API Layer
   |
   +---- Database
   |
   +---- Document Workers
   |
   +---- AI Services
   |
   +---- Object Storage
```

As usage increases, additional API instances and processing workers can be added.

The database and storage layer should also support scaling as required.

---

## 63. Deployment Architecture

A production deployment may follow:

```text
                    INTERNET
                        |
                        v
                 Web Application
                        |
                        v
                    API Server
                   /    |     \
                  /     |      \
                 v      v       v
          PostgreSQL  Storage  AI APIs
              |
              v
           pgvector
              
                        |
                        v
               Background Workers
```

The exact cloud provider and deployment services will be selected based on cost, reliability, security, and development simplicity.

---

## 64. Development Workflow

Development should follow:

```text
Requirement
    |
    v
Design
    |
    v
Implementation
    |
    v
Local Testing
    |
    v
Commit
    |
    v
Push to GitHub
    |
    v
Automated Checks
    |
    v
Deployment
```

Changes should be committed regularly using meaningful Git commit messages.

---

## 65. Git Workflow

The project repository should use Git for version control.

Example:

```bash
git status
git add .
git commit -m "Add document upload flow"
git push
```

Commits should describe the change clearly.

Examples:

```text
Add document upload API
Implement PDF extraction
Add RAG retrieval service
Add document Q&A
Add citation support
```

---

## 66. CI/CD

The project should eventually use automated checks when code is pushed.

Potential pipeline:

```text
Git Push
   |
   v
Run Linting
   |
   v
Run Unit Tests
   |
   v
Run Integration Tests
   |
   v
Build Application
   |
   v
Deploy
```

Deployment to production should only occur after required checks pass.

---

## 67. Configuration Management

Application configuration should be centralized.

Configuration may include:

```text
Database URL
Storage configuration
AI provider configuration
Model configuration
Embedding model
Retrieval parameters
Maximum file size
Allowed file types
Rate limits
Environment
```

Configuration values should not be scattered throughout application code.

---

## 68. Dependency Management

Dependencies should be explicitly defined and version controlled.

Backend dependencies should be maintained in an appropriate Python dependency file.

Frontend dependencies should be maintained using the JavaScript package manager configuration.

Dependencies should be updated carefully and tested before deployment.

---

## 69. Technical Risks

### Risk 1: Poor PDF Extraction

Some PDFs may have difficult layouts or scanned content.

**Mitigation:**

Validate extraction quality and introduce OCR support if required.

### Risk 2: Poor Retrieval

Relevant clauses may not be retrieved.

**Mitigation:**

Evaluate chunking, embeddings, retrieval, metadata filtering, and reranking.

### Risk 3: Hallucinations

The LLM may generate unsupported information.

**Mitigation:**

Use grounding, prompt constraints, citations, response validation, and AI evaluation.

### Risk 4: High AI Cost

Large documents may require significant processing.

**Mitigation:**

Control context size, token usage, model selection, and repeated processing.

### Risk 5: Privacy Breach

Legal documents may contain sensitive information.

**Mitigation:**

Use secure storage, access control, encryption, deletion, and minimal logging.

### Risk 6: Processing Delays

Large documents may take significant time.

**Mitigation:**

Use asynchronous background processing and clear status communication.

---

## 70. Technical Decisions

The MVP makes the following high-level decisions:

| Area            | Decision                  |
| --------------- | ------------------------- |
| Frontend        | Next.js / React           |
| Language        | TypeScript                |
| Backend         | Python / FastAPI          |
| Database        | PostgreSQL                |
| Vector Search   | pgvector                  |
| Storage         | Secure object storage     |
| AI Architecture | RAG                       |
| Embeddings      | Dedicated embedding model |
| LLM             | External LLM API          |
| API Style       | REST/JSON                 |
| Processing      | Background workers        |
| Version Control | Git/GitHub                |
| Deployment      | Cloud infrastructure      |

These decisions may be changed if implementation or evaluation provides a strong reason.

---

## 71. MVP Technical Scope

### Must Have

* Frontend application
* Authentication
* Dashboard
* PDF upload
* Secure document storage
* PDF text extraction
* Document chunking
* Embedding generation
* PostgreSQL
* Vector search
* AI summary
* Risk analysis
* Missing-information analysis
* Document Q&A
* Citations
* Document deletion
* Error handling
* Basic monitoring
* Automated tests

### Nice to Have

* OCR
* Advanced hybrid search
* Advanced reranking
* Exportable reports
* Improved document viewer
* Advanced analytics
* More document formats

### Post-MVP

* Microsoft Word integration
* Document comparison
* Multi-document analysis
* Collaboration
* Organization workspaces
* External legal research
* Clause libraries
* Advanced agentic workflows
* Fine-tuned models

---

## 72. Implementation Order

The implementation should proceed in the following order:

### Phase 1 — Project Setup

* Repository structure
* Frontend setup
* Backend setup
* Environment configuration
* Database connection

### Phase 2 — Authentication

* Sign up
* Login
* Session handling
* Authorization

### Phase 3 — Document Management

* Upload
* Storage
* Document records
* Delete
* Status tracking

### Phase 4 — Document Processing

* PDF extraction
* Cleaning
* Chunking
* Metadata

### Phase 5 — RAG

* Embeddings
* Vector storage
* Retrieval
* Reranking
* Context assembly

### Phase 6 — AI Features

* Summary
* Risk detection
* Missing information
* Q&A
* Citations

### Phase 7 — UX Integration

* Dashboard
* Document workspace
* Analysis views
* Q&A interface
* Document viewer

### Phase 8 — Testing

* Unit tests
* Integration tests
* End-to-end tests
* AI evaluation

### Phase 9 — Production Readiness

* Security
* Monitoring
* Logging
* Cost controls
* Error handling
* Deployment

---

## 73. Definition of Technical Completion

The MVP technical implementation is considered complete when:

1. Users can create accounts and log in.
2. Users can upload supported PDF documents.
3. Documents are securely stored.
4. Documents are processed successfully.
5. Text is extracted and chunked.
6. Embeddings are generated.
7. Chunks are stored for retrieval.
8. Users can receive document summaries.
9. Users can view potential risks.
10. Users can view potential missing information.
11. Users can ask questions about their documents.
12. Responses are grounded in document content.
13. Citations are available for document-specific claims.
14. Users can delete their documents.
15. Unauthorized users cannot access another user's documents.
16. Major failure scenarios are handled.
17. Core software tests pass.
18. AI evaluation meets the agreed quality targets.
19. The application can be deployed successfully.

---

## 74. Future Technical Improvements

Potential improvements include:

* OCR pipeline
* Hybrid search
* Advanced reranking
* Query rewriting
* Multi-query retrieval
* Document comparison
* Multi-document retrieval
* Advanced caching
* Model routing
* Fine-tuned models
* Dedicated inference infrastructure
* Advanced observability
* Organization-level access control
* Enterprise security controls
* Microsoft Word integration

These improvements are outside the initial MVP unless evaluation or product requirements justify them.

---

## 75. Final Technical Architecture Summary

The technical architecture connects the product, UX, and AI architecture into one system.

```text
                         USER
                           |
                           v
                    NEXT.JS FRONTEND
                           |
                           v
                     FASTAPI BACKEND
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
    AUTHENTICATION      DATABASE       OBJECT STORAGE
                           |
                           v
                      DOCUMENT DATA
                           |
                           v
                  BACKGROUND PROCESSING
                           |
              +------------+------------+
              |            |            |
              v            v            v
          EXTRACT       CHUNK        EMBED
              |            |            |
              +------------+------------+
                           |
                           v
                       PGVECTOR
                           |
                           v
                       RETRIEVAL
                           |
                           v
                       RERANKING
                           |
                           v
                  RELEVANT CONTEXT
                           |
                           v
                  PROMPT + CONTEXT
                           |
                           v
                          LLM
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
          SUMMARY        RISKS       Q&A ANSWER
             |             |             |
             +-------------+-------------+
                           |
                           v
                       CITATIONS
                           |
                           v
                    NEXT.JS FRONTEND
                           |
                           v
                         USER
```

The fundamental technical architecture is:

**Next.js provides the user experience → FastAPI provides application logic → PostgreSQL stores application data → object storage stores documents → document processing prepares content → embeddings and pgvector enable retrieval → the RAG pipeline provides relevant context → the LLM generates grounded responses → citations connect responses back to document evidence.**

````