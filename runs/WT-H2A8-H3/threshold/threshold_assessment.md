# Threshold AI impact assessment — WT-H2A8-H3

## 1. Basic information

### 1.1 AI use case profile
- **Name**: APS Markdown Conversion Service
- **Run ID**: WT-H2A8-H3

### 1.2 Establishing impact assessment responsibilities
- Not stated in the outline.

### 1.3 Additional roles and responsibilities
- Not stated in the outline.

### 1.4 AI use case description
A cross-agency, ephemeral utility for public servants to convert diverse web and document formats into standardized Markdown. The system uses deterministic parsing libraries and explicitly avoids LLM-based processing entirely.

### 1.5 In-scope use case
Yes, the tool is designed for public servants across all APS agencies to convert web and document formats.

### 1.6 Type of AI technology
The system uses deterministic parsing libraries and explicitly avoids LLM-based processing. (Note: While the outline describes a deterministic parser rather than traditional AI, it is being evaluated under this threshold framework).

### 1.7 Usage pattern
Ephemeral web-based utility. Users input a URL or upload a file, and the system processes the content in volatile memory, purging it immediately upon completion.

### 1.8 Administrative decisions
Not stated in the outline.

### 1.9 Domain
Government administration, document processing, and cross-agency utility.

### 1.10 Expert contributions
Not stated in the outline.

### 1.11 Impact assessment review log
Not stated in the outline.

## 2. Purpose and expected benefits

### 2.1 Problem definition
Public servants frequently struggle with information trapped in poorly formatted PDFs, legacy web pages, or inconsistent document structures, making it difficult to index, search, or reuse content effectively.

### 2.2 AI use case purpose
To provide a cross-agency, web-based conversion utility that accepts URLs or files and uses deterministic parsing libraries to transform content into standardized Markdown, facilitating easier content reuse and indexing.

### 2.3 Non-AI alternatives
Manual re-typing, traditional web scraping scripts (such as BeautifulSoup), or off-the-shelf document conversion software like Pandoc.

### 2.4 Identifying stakeholders
- **Primary Users**: Public servants across all APS agencies.
- **Stakeholders**: Agency IT security teams who must vet the tool for cross-departmental data handling and compliance.

### 2.5 Expected benefits
Providing a net positive utility for document conversion across the APS, enabling more efficient workflows by providing clean Markdown and stripping navigation/ads, while maintaining a strictly stateless, ephemeral core that minimizes data retention risks.

## 3. Inherent risk assessment

| Area | Consequence | Likelihood | Risk rating |
| --- | --- | --- | --- |
| 3.1 Reducing service accessibility and inclusion | Minor | Possible | Medium |
| 3.2 Unfair discrimination | Insignificant | Unlikely | Low |
| 3.3 Stereotyping or demeaning representations | Insignificant | Unlikely | Low |
| 3.4 Harm | Minor | Possible | Medium |
| 3.5 Privacy concerns | Moderate | Possible | Medium |
| 3.6 Security concerns — data aspects | Moderate | Possible | Medium |
| 3.7 Security concerns — system aspects | Moderate | Possible | Medium |
| 3.8 Reputation or public confidence | Minor | Possible | Medium |

**3.9 Overall inherent risk rating (highest-wins): Medium**

### 3.1 Reducing service accessibility and inclusion

The tool converts web pages and documents to Markdown. If the deterministic parser fails to handle certain complex formats or strips accessibility features (such as alt text or semantic headers), it could create minor, short-term barriers for public servants relying on screen readers or trying to reuse the content. Since accessibility standards for the output Markdown are not explicitly detailed in the outline, we precautionarily assume a Minor consequence with a Possible likelihood.

### 3.2 Unfair discrimination

The system uses deterministic parsing libraries to convert document formats to Markdown and avoids LLM-based processing entirely. There is no decision-making, profiling, or natural language generation that could introduce bias or unfair discrimination. However, to remain precautionary, we acknowledge a minor possibility (Unlikely) that parsing errors could theoretically affect specific language scripts or localized formatting styles, resulting in Insignificant consequences.

*Divergence: Assessor A suggested a Rare likelihood, while Assessor B suggested Unlikely. The higher likelihood (Unlikely) stands to precautionarily account for theoretical parsing errors affecting specific language scripts.*

### 3.3 Stereotyping or demeaning representations

The tool is a deterministic parser that converts input text directly to Markdown without generating new content or modifying meaning. If the source text contains stereotyping, the tool will faithfully reproduce it, but it does not generate or perpetuate new stereotypes. We select an Unlikely likelihood and Insignificant consequence to remain precautionary.

*Divergence: Assessor A suggested a Rare likelihood, while Assessor B suggested Unlikely. The higher likelihood (Unlikely) stands as a precautionary measure.*

### 3.4 Harm

The system processes internal documents and public-facing web content. If a critical document is parsed incorrectly or suffers formatting corruption during conversion, and is relied upon without verification, it could lead to minor operational errors or misinformation within an agency. Precautionarily, we default the likelihood to Possible for a Minor consequence.

### 3.5 Privacy concerns

The tool processes internal documents which may contain sensitive or personal information (PII). Although the core architecture is ephemeral (processed in volatile memory and purged immediately), the public feedback mechanism via GitHub poses a risk of users accidentally submitting sensitive data. Despite the planned 250-character limit and automated PII scanning, a leak of sensitive data remains a Moderate consequence and is rated as Possible.

### 3.6 Security concerns — data aspects

The system processes internal documents across various APS agencies, which may have security classifications. If the cross-agency authentication or data isolation mechanisms fail, sensitive or classified internal documents could be exposed to unauthorized users. Although the architecture is ephemeral, the ingestion of classified documents via a cross-agency web tool presents a potential data security risk if intercepted. Precautionarily, we select a Moderate consequence and a Possible likelihood.

### 3.7 Security concerns — system aspects

The tool accepts URLs and file uploads, which introduces risks of Server-Side Request Forgery (SSRF) or malicious file uploads. A vulnerability in the deterministic parsing libraries or the web interface could be exploited to compromise the container or access the internal network. Since the outline does not detail specific security hardening, we precautionarily select a Moderate consequence and a Possible likelihood.

### 3.8 Reputation or public confidence

If the tool suffers a security breach, leaks data via the public GitHub feedback repository, or consistently fails to parse documents accurately, it could lead to a minor dent in public or inter-agency confidence in government-provided digital utilities. Precautionarily, we select a Minor consequence and a Possible likelihood.

## 4. Threshold assessment outcome

### 4.1 Assessing Officer Recommendation
Based on the threshold assessment of the APS Markdown Conversion Service, the following recommendations are made to manage inherent risks:

1. **Security Architecture and SSRF Controls**: Although the system is designed to be ephemeral and processes data in volatile memory, it accepts user-uploaded files and external URLs. This introduces potential vectors for Server-Side Request Forgery (SSRF) and malicious file execution. A comprehensive security assessment of the deterministic parsing libraries and robust input validation must be implemented.
2. **Privacy and Feedback Safeguards**: The proposed feedback mechanism utilizes a public GitHub repository. Although a 250-character limit and an automated PII scanner are planned, there remains a risk of accidental disclosure of sensitive public service data. The automated GitHub Action must be rigorously tested and regularly audited, and clear user guidance must be displayed warning users not to upload sensitive information.
3. **Cross-Agency Authentication**: Ensure that the cross-agency authentication mechanism is robustly integrated and complies with federal identity security standards to prevent unauthorized access and enforce strict data isolation.
4. **Verification of Output and Accessibility**: Since deterministic parsers can occasionally misinterpret complex document layouts or strip accessibility features (e.g., alt text, semantic headers), clear user guidance should emphasize that converted Markdown outputs must be verified for accuracy. The parsing libraries should also be configured to preserve essential accessibility elements where possible.

A full assessment is **required**.
