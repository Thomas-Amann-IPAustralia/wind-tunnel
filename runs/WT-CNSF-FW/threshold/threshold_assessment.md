# Threshold AI impact assessment — WT-CNSF-FW

## 1. Basic information

### 1.1 AI use case profile
- **Title:** Departmental Knowledge Graph
- **Run ID:** WT-CNSF-FW

### 1.2 Establishing impact assessment responsibilities
- Not stated in the outline.

### 1.3 Additional roles and responsibilities
- Not stated in the outline.

### 1.4 AI use case description
An automated knowledge graph designed to ingest internal departmental documents and communications. It uses AI to extract nodes (entities) and edges (relationships) from unstructured text to map and connect fragmented internal information.

### 1.5 In-scope use case
Yes, the project involves building an AI-powered knowledge graph to map and connect fragmented internal departmental information.

### 1.6 Type of AI technology
Natural Language Processing (NLP) / Information Extraction AI used to extract entities (nodes) and relationships (edges) from unstructured text.

### 1.7 Usage pattern
Internal tool for departmental staff and policy researchers.

### 1.8 Administrative decisions
Not stated in the outline.

### 1.9 Domain
Internal knowledge management, information discovery, and policy research.

### 1.10 Expert contributions
Not stated in the outline.

### 1.11 Impact assessment review log
Not stated in the outline.

## 2. Purpose and expected benefits

### 2.1 Problem definition
Departmental information is currently siloed and fragmented, making it difficult for staff to discover relevant internal knowledge, policies, or project history efficiently.

### 2.2 AI use case purpose
To build an automated knowledge graph that maps relationships between entities across unstructured text, connecting fragmented internal information and enabling efficient discovery of internal knowledge, policies, and project history.

### 2.3 Non-AI alternatives
Not stated in the outline.

### 2.4 Identifying stakeholders
- **Primary Users:** Departmental staff and policy researchers.
- **Stakeholders:** IT/data governance teams (responsible for information security) and the leadership team (seeking better organizational insights).

### 2.5 Expected benefits
- Improved discovery of internal knowledge, policies, and project history.
- Reduced information siloing.
- Enhanced organizational insights for the leadership team.

## 3. Inherent risk assessment

| Area | Consequence | Likelihood | Risk rating |
| --- | --- | --- | --- |
| 3.1 Reducing service accessibility and inclusion | Moderate | Possible | Medium |
| 3.2 Unfair discrimination | Moderate | Possible | Medium |
| 3.3 Stereotyping or demeaning representations | Moderate | Possible | Medium |
| 3.4 Harm | Moderate | Possible | Medium |
| 3.5 Privacy concerns | Major | Likely | High |
| 3.6 Security concerns — data aspects | Major | Likely | High |
| 3.7 Security concerns — system aspects | Moderate | Possible | Medium |
| 3.8 Reputation or public confidence | Moderate | Possible | Medium |

**3.9 Overall inherent risk rating (highest-wins): High**

### 3.1 Reducing service accessibility and inclusion

Since the outline does not detail the user interface or accessibility features, we must precautionarily assume that noticeability of access issues could be Moderate if staff rely on this tool for policy research and encounter barriers. The likelihood is set to Possible as a precautionary default in the absence of specific design constraints.

*Divergence: Assessor A rated the consequence as Moderate, while Assessor B rated it as Minor. The higher tier (Moderate) stands, reflecting the precautionary assumption that access issues could cause noticeable barriers for staff relying on the tool for policy research.*

### 3.2 Unfair discrimination

Ingesting unstructured communications (like emails and meeting minutes) and using AI to extract entities and relationships carries a risk of extracting biased or unfair associations. Precautionarily, this could cause noticeable harm or bias concerns for internal staff (e.g., misattributing project responsibilities or policy positions), requiring intervention. Likelihood is Possible given the unstructured nature of the source data.

### 3.3 Stereotyping or demeaning representations

The system ingests historical internal documents and email archives which may contain outdated language or biased representations. The AI could systematically extract and map these as valid relationships, perpetuating stereotypes internally. In the absence of explicit filtering mechanisms in the outline, we precautionarily rate the consequence as Moderate and likelihood as Possible.

### 3.4 Harm

Incorrect entity extraction or relationship mapping from sensitive internal communications (like emails) could lead to professional distress or internal organizational disruption if individuals are incorrectly linked to sensitive, failed, or controversial projects. Precautionarily, we assume a Moderate consequence of internal organizational/individual harm, with a Possible likelihood due to the lack of stated validation or human-in-the-loop verification in the outline.

### 3.5 Privacy concerns

The project plans to ingest highly sensitive unstructured data, specifically mentioning email archives and internal wikis. Email archives inherently contain personal, private, and sensitive communications. Mapping these relationships without explicit, granular privacy-preserving constraints makes the risk of exposing private or sensitive personal data Likely to occur, with a Major consequence to internal trust and privacy.

*Divergence: Assessor A rated the consequence as Major, while Assessor B rated it as Moderate. The higher tier (Major) stands, reflecting the significant risk to internal trust and privacy from large-scale misuse or exposure of private data in email archives.*

### 3.6 Security concerns — data aspects

The outline notes that the data sensitivity is likely high given the internal nature of the content (including policy documents and project reports). Ingesting this into a centralized knowledge graph without defined security classification boundaries presents a Major consequence if sensitive or classified data is exposed to unauthorized internal users. The likelihood is Likely because the system is designed to connect siloed data, which naturally bypasses existing silo-based access controls unless strictly managed.

*Divergence: Assessor A rated the likelihood as Likely, while Assessor B rated it as Possible. The higher tier (Likely) stands, reflecting the inherent risk that connecting siloed data will bypass existing access controls unless strictly managed.*

### 3.7 Security concerns — system aspects

The outline does not specify the sourcing or technical architecture of the AI system. Precautionarily, we must assume that system vulnerabilities or data leakage through the AI model (such as unauthorized data inference or prompt injection if a LLM is used) could lead to a Moderate security compromise. The likelihood is Possible given the lack of technical constraints in the outline.

### 3.8 Reputation or public confidence

Mining internal employee emails and communications using AI can trigger significant internal and external reputational concerns regarding surveillance and data governance. If made public, any leak of sensitive internal communications or policy drafts mapped by the AI could lead to a Moderate impact on public confidence and questions about oversight. The likelihood is Possible given the high sensitivity of the data sources.

## 4. Threshold assessment outcome

### 4.1 Assessing officer recommendation
The proposed Departmental Knowledge Graph aims to ingest highly sensitive internal unstructured data, explicitly including email archives, meeting minutes, and project reports. While the primary users are internal staff, the ingestion of communications and unstructured text presents significant risks regarding privacy, data security, and potential exposure of sensitive information.

A cautious approach is recommended, focusing on robust data governance, clear access control frameworks, and validation of AI-extracted relationships to prevent misinformation, bias, or unauthorized data exposure. Particular attention must be paid to ensuring that sensitive or restricted information is not inappropriately exposed or linked across different security domains within the department. Detailed technical and privacy safeguards must be established before proceeding with implementation.

A full assessment is **required**.

Overall inherent risk is **High** — refer to an internal governance body (§12.5).
