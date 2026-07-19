# Threshold AI impact assessment — WT-9J32-99

## 1. Basic information

### 1.1 AI Use Case Profile
* **Title**: Tripwire Data Integrity Pipeline
* **Run ID**: WT-9J32-99
* **Summary**: An automated, auditable, and self-calibrating data monitoring system designed to replace manual reconciliation with a multi-stage, high-confidence verification pipeline.

### 1.2 Establishing Impact Assessment Responsibilities
Not stated in the outline.

### 1.3 Additional Roles and Responsibilities
Not stated in the outline.

### 1.4 AI Use Case Description
Tripwire is an automated, auditable data monitoring pipeline designed to replace manual reconciliation. It utilizes a multi-stage verification process consisting of bi-encoder and cross-encoder gates to validate data chunks. The system features a fail-closed design and includes an 'observation mode' for empirical calibration.

### 1.5 In-Scope Use Case
Yes, the system is in-scope as an AI-enabled automated backend pipeline for data integrity monitoring and verification.

### 1.6 Type of AI Technology
Machine learning-based multi-stage verification pipeline utilizing bi-encoder and cross-encoder architectures.

### 1.7 Usage Pattern
Headless backend pipeline operating automatically. It generates logs, health alerts, and runbooks for operator intervention when necessary.

### 1.8 Administrative Decisions
Not stated in the outline.

### 1.9 Domain
Data integrity, quality assurance, data management, and IT operations.

### 1.10 Expert Contributions
Not stated in the outline.

### 1.11 Impact Assessment Review Log
Not stated in the outline.

## 2. Purpose and expected benefits

### 2.1 Problem Definition
Manual data reconciliation and quality monitoring processes are currently prone to error, lack transparency, and suffer from fragmented ownership. These factors make it difficult to maintain high-confidence data pipelines.

### 2.2 AI Use Case Purpose
To replace manual reconciliation with an automated, auditable, and self-calibrating data monitoring system that uses a multi-stage, high-confidence verification pipeline to validate data chunks and ensure data integrity.

### 2.3 Non-AI Alternatives
The following alternatives were considered and rejected:
* **Manual auditing**: Rejected due to scale and high error rates.
* **Hard-coded rule-based systems**: Rejected due to a lack of flexibility.
* **Standard off-the-shelf monitoring tools**: Rejected due to the need for custom, high-confidence verification logic.

### 2.4 Identifying Stakeholders
* **Primary Users**: Data operators and system maintainers.
* **Stakeholders**: IT Security Advisors and business owners who rely on the integrity of the monitored data.

### 2.5 Expected Benefits
* Elimination of manual reconciliation errors.
* Increased transparency and auditability of data pipelines.
* Prevention of silent failures through a "fail loudly" design (zero silent failures).
* Empirical calibration of verification thresholds (score distributions) during a 4-8 week observation mode.
* Clear runbooks enabling operators to diagnose and resolve issues without original author intervention.

## 3. Inherent risk assessment

| Area | Consequence | Likelihood | Risk rating |
| --- | --- | --- | --- |
| 3.1 Reducing service accessibility and inclusion | Insignificant | Unlikely | Low |
| 3.2 Unfair discrimination | Moderate | Possible | Medium |
| 3.3 Stereotyping or demeaning representations | Minor | Unlikely | Low |
| 3.4 Harm | Moderate | Possible | Medium |
| 3.5 Privacy concerns | Moderate | Possible | Medium |
| 3.6 Security concerns — data aspects | Moderate | Possible | Medium |
| 3.7 Security concerns — system aspects | Moderate | Possible | Medium |
| 3.8 Reputation or public confidence | Moderate | Possible | Medium |

**3.9 Overall inherent risk rating (highest-wins): Medium**

### 3.1 Reducing service accessibility and inclusion

Tripwire is a headless backend pipeline used internally by data operators and system maintainers. It does not serve as a public-facing interface or direct service delivery channel. Any system glitch would be a minor backend issue with no direct barrier to public service accessibility, making any impact on inclusion highly unlikely and insignificant.

*Divergence: Assessor A assessed likelihood as Rare, while Assessor B assessed it as Unlikely. The higher likelihood (Unlikely) stands.*

### 3.2 Unfair discrimination

The system uses bi-encoder and cross-encoder gates to validate data chunks from CSVs and SQL databases. The outline does not specify the contents of the structured data. Applying the precautionary principle, if the data contains demographic or personal information, biased semantic representations within the encoders could lead to unfair filtering or validation failures for specific groups, requiring intervention to resolve.

### 3.3 Stereotyping or demeaning representations

As a headless backend system processing structured data, the risk of generating or perpetuating demeaning representations to the public is very low. However, under a precautionary approach, if the encoder models process natural language data chunks, there is a minor risk that biased semantic associations could manifest in internal logs, metadata, or operator alerts, which would be isolated and quickly resolved.

### 3.4 Harm

The system features a 'fail-closed' design. If the verification pipeline incorrectly flags valid data as uncertain or invalid due to calibration issues, it could halt critical downstream data pipelines. This could cause noticeable operational disruption, financial losses, or administrative distress to business owners and dependent systems before operators can resolve the issue using runbooks.

### 3.5 Privacy concerns

The pipeline processes structured data from SQL databases and CSVs. Since the outline does not state whether this data is de-identified, we must precautionarily assume it may contain sensitive personal information (PII). Processing this data through custom ML encoders and storing it in logs or SQLite databases without proper encryption or access controls raises noticeable privacy concerns.

### 3.6 Security concerns — data aspects

Tripwire ingests structured data from multiple external sources (databases and CSVs). The outline does not specify the security classification of these data sources, so we assume the data could be sensitive. A vulnerability in the ingestion or verification pipeline, or database corruption due to concurrency issues, could lead to unauthorized access or moderate data compromise, requiring formal investigation.

### 3.7 Security concerns — system aspects

The implementation of custom bi-encoder and cross-encoder gates in a headless backend introduces architectural complexity. Furthermore, the outline explicitly identifies a system constraint regarding strict CI concurrency limits to prevent SQLite state corruption. Vulnerabilities in model deployment or concurrent state management could lead to data leaks, access issues, or system instability, representing a contained but serious system security risk.

### 3.8 Reputation or public confidence

While Tripwire is an internal tool, it is responsible for the integrity of data that business owners and potentially public services rely upon. If a failure occurs—such as a silent corruption or a prolonged 'fail-closed' outage that halts dependent systems—it would attract scrutiny and undermine public confidence in the agency's data oversight and technical capability, requiring a remedial response.

## 4. Threshold assessment outcome

### 4.1 Assessing Officer Recommendation
The Tripwire Data Integrity Pipeline represents a significant shift from manual data reconciliation to an automated, machine-learning-driven verification system. The inclusion of robust safety features—such as a fail-closed architecture, a headless backend, 'fail loudly' constraints, and a dedicated 4-8 week 'observation mode' for empirical calibration—demonstrates a strong baseline for risk management.

However, the use of custom bi-encoder and cross-encoder models introduces inherent risks that require careful management. Because the outline is silent on the specific nature of the structured data being processed (including whether it contains personally identifiable information or demographic fields), a precautionary approach has been adopted across several risk categories.

Key areas of focus moving forward should include:
1. **Data Governance**: Clarifying whether the SQL databases and CSVs contain sensitive or personal data, and ensuring appropriate privacy safeguards and access controls are in place.
2. **Model Bias and Calibration**: Closely monitoring the bi-encoder and cross-encoder gates during the observation mode to ensure they do not introduce unfair discrimination or systematic errors in data validation.
3. **System Security**: Addressing the known concurrency constraints to prevent SQLite state corruption and securing the headless pipeline against unauthorized access.

It is recommended that the project team proceed with detailed technical documentation of the encoder models, establish clear data schemas, and closely document the outcomes of the 4-8 week calibration phase to ensure the system's decision-making remains transparent and auditable. Runbooks must also be thoroughly tested to ensure operators can effectively manage any flagged uncertainties.

A full assessment is **required**.
