# Threshold AI impact assessment — WT-SX76-K5

## 1. Basic information

### 1.1 AI use case profile
* **Name**: Legacy Code Modernization Assistant
* **Run ID**: WT-SX76-K5
* **Summary**: An AI-driven, platform-agnostic tool to analyze, document, and map legacy software systems while providing automated compliance and architectural governance within sovereign infrastructure.

### 1.2 Establishing impact assessment responsibilities
Not stated in the outline.

### 1.3 Additional roles and responsibilities
Not stated in the outline.

### 1.4 AI use case description
The Legacy Code Modernization Assistant is an AI-driven, platform-agnostic tool designed to analyze, document, and map legacy software systems. It ingests legacy source code, configuration files, and existing technical documentation to generate baseline Software Bills of Materials (SBOMs), architectural maps, and draft compliance attestations. In the CI/CD pipeline, it compares new code states against planned configurations, flagging deviations for triage.

### 1.5 In-scope use case
Yes, the tool is used to analyze and document legacy codebases, track configuration drift in CI/CD pipelines, and assist in architectural governance.

### 1.6 Type of AI technology
Generative AI / Large Language Model (LLM) used for code analysis, architectural mapping, and natural language generation (documentation, SBOMs, and compliance drafts). Specific model provenance and residency requirements are deferred to future implementation phases.

### 1.7 Usage pattern
The system operates via a developer-focused CLI for code ingestion and analysis, a web-based dashboard for visualizing system architecture, and a CI/CD pipeline integration to monitor configuration drift. It employs a human-in-the-loop model where AI-generated drafts are reviewed line-by-line by human auditors and architecture decision groups.

### 1.8 Administrative decisions
The tool does not make automated administrative decisions affecting individuals; it provides recommendations and drafts for human review.

### 1.9 Domain
Government Information Technology (IT) modernization, software engineering, and architectural governance.

### 1.10 Expert contributions
Not stated in the outline.

### 1.11 Impact assessment review log
Not stated in the outline.

## 2. Purpose and expected benefits

### 2.1 Problem definition
Government agencies are burdened by opaque, undocumented legacy software systems that are difficult to maintain, secure, or integrate with modern services.

### 2.2 AI use case purpose
The purpose of the AI use case is to ingest legacy source code to generate documentation, identify modular components for abstraction, produce Software Bills of Materials (SBOMs) to guide modernization efforts, track configuration drift, and generate compliance attestations.

### 2.3 Non-AI alternatives
Alternatives considered include manual code audits by external consultants, non-AI static analysis tools, or complete system replacement (rip-and-replace), which is often cost-prohibitive.

### 2.4 Identifying stakeholders
* **Primary Users**: Software engineers and system architects within government IT departments.
* **Stakeholders**: Security officers, procurement leads, and the public who rely on the stability of these services.

### 2.5 Expected benefits
Expected benefits include improved documentation, accurate baseline SBOMs and architectural maps, automated tracking of configuration drift in CI/CD pipelines, visualization of modernization progress across government portfolios, and streamlined generation of automated compliance attestations aligned with Australian Whole-of-Government (WofG) standards.

## 3. Inherent risk assessment

| Area | Consequence | Likelihood | Risk rating |
| --- | --- | --- | --- |
| 3.1 Reducing service accessibility and inclusion | Moderate | Possible | Medium |
| 3.2 Unfair discrimination | Minor | Possible | Medium |
| 3.3 Stereotyping or demeaning representations | Minor | Possible | Medium |
| 3.4 Harm | Major | Possible | High |
| 3.5 Privacy concerns | Moderate | Possible | Medium |
| 3.6 Security concerns — data aspects | Major | Possible | High |
| 3.7 Security concerns — system aspects | Major | Possible | High |
| 3.8 Reputation or public confidence | Major | Possible | High |

**3.9 Overall inherent risk rating (highest-wins): High**

### 3.1 Reducing service accessibility and inclusion

The tool is an internal-facing assistant for software engineers and does not directly interface with the public. However, because it guides the modernization of legacy systems that the public relies on, any errors in architectural mapping or refactoring recommendations could lead to service disruptions. Applying a precautionary approach, there is a possible likelihood of moderate downstream accessibility impacts if a critical public-facing system experiences issues due to flawed AI-guided modernization.

*Divergence: Assessor A suggested a Minor consequence, while Assessor B suggested Moderate. The higher tier (Moderate) stands because flawed refactoring recommendations could lead to noticeable service disruptions in critical public-facing systems.*

### 3.2 Unfair discrimination

The tool analyzes technical source code rather than demographic or personal data. However, under a precautionary approach, legacy code may contain embedded business logic or eligibility rules. A misinterpretation by the AI during documentation or refactoring could introduce or perpetuate discriminatory logic, resulting in a possible likelihood of minor consequences.

*Divergence: Assessor A suggested Insignificant consequence and Rare likelihood, while Assessor B suggested Minor and Possible. The higher tiers stand under a precautionary approach, acknowledging that legacy code may contain embedded business logic or eligibility rules that could be misinterpreted.*

### 3.3 Stereotyping or demeaning representations

The tool processes source code and technical documentation, which is highly unlikely to contain or generate stereotyping or demeaning representations. However, applying a strict precautionary default due to the lack of explicit constraints on natural language generation in the outline, there is a possible likelihood of minor consequences.

*Divergence: Assessor A suggested Insignificant consequence and Rare likelihood, while Assessor B suggested Minor and Possible. The higher tiers stand due to a strict precautionary default regarding the lack of explicit constraints on the model's natural language generation.*

### 3.4 Harm

The tool generates SBOMs and architectural maps to guide modernization. If the AI fails to identify critical security vulnerabilities or dependencies, or if it suggests flawed refactoring paths that are implemented, it could lead to major system failures or security breaches in critical government infrastructure. This presents a possible likelihood of major consequences, including widespread operational disruption.

*Divergence: Assessor A suggested a Moderate consequence, while Assessor B suggested Major. The higher tier (Major) stands because flawed refactoring or missed vulnerabilities could lead to major system failures in critical government infrastructure.*

### 3.5 Privacy concerns

Although the tool is designed to process source code and configuration files, legacy repositories frequently contain hardcoded credentials, API keys, or legacy test data containing personal information. If the AI processes or exposes this sensitive data within its dashboard or reports, it raises privacy concerns, resulting in a possible likelihood of moderate consequences.

### 3.6 Security concerns — data aspects

The input data consists of highly sensitive government legacy source code, configuration files, and technical documentation. A data leak or unauthorized access to this intellectual property could expose critical system vulnerabilities to malicious actors, posing a major security risk. While the outline specifies a sovereign, air-gapped environment, the model provenance and residency requirements are deferred to future phases, introducing uncertainty and a possible likelihood of major consequences.

### 3.7 Security concerns — system aspects

The implementation relies on an LLM endpoint where specific model provenance and residency requirements are deferred to future phases. This creates supply chain and integration risks, such as potential vulnerabilities in the self-managed infrastructure or the model itself. A system-level vulnerability could lead to unauthorized access to the underlying code repositories, presenting a possible likelihood of major consequences.

*Divergence: Assessor A suggested a Moderate consequence, while Assessor B suggested Major. The higher tier (Major) stands because deferred model provenance and residency requirements introduce supply chain risks that could lead to critical vulnerabilities and unauthorized access to code repositories.*

### 3.8 Reputation or public confidence

The tool is intended to generate automated compliance attestations and guide critical IT modernization. If the AI generates inaccurate documentation or flawed compliance drafts that are inadvertently approved, or if its use leads to a security breach of government source code, it would result in widespread public criticism and major reputational damage to the government's digital capability. This presents a possible likelihood of major consequences.

*Divergence: Assessor A suggested a Moderate consequence, while Assessor B suggested Major. The higher tier (Major) stands because a security breach of government source code or flawed compliance attestations would result in widespread public criticism and major reputational damage.*

## 4. Threshold assessment outcome

### 4.1 Assessing officer recommendation
The Legacy Code Modernization Assistant represents a highly valuable capability for addressing technical debt across government agencies. However, because it operates on highly sensitive proprietary source code and configuration files, and because critical decisions regarding LLM provenance and hosting infrastructure have been deferred, a cautious approach is warranted. The potential for downstream impacts on public-facing services (via flawed refactoring recommendations) and the risk of exposing sensitive system vulnerabilities require robust governance.

It is recommended that:
1. **Sovereign Deployment**: The LLM endpoint must be hosted strictly on sovereign, self-managed, or air-gapped infrastructure as preferred in the outline, to prevent any external exposure of government source code. A comprehensive security and privacy review of this environment must be conducted before any production deployment.
2. **Human-in-the-Loop (HITL)**: All AI-generated outputs, particularly Software Bills of Materials (SBOMs) and draft compliance attestations, must continue to undergo strict, line-by-line human verification by qualified engineers and auditors before final sign-off.
3. **Security Auditing**: A comprehensive security assessment of the tool's integration into CI/CD pipelines should be conducted to ensure that the automated analysis does not introduce new attack vectors or expose sensitive configuration data.
4. **Model Provenance**: Future implementation phases must explicitly define and verify model provenance and residency requirements to align with Australian Whole-of-Government standards.

A full assessment is **required**.

Overall inherent risk is **High** — refer to an internal governance body (§12.5).
