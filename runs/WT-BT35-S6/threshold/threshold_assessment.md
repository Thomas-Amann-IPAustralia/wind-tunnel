# Threshold AI impact assessment — WT-BT35-S6

## 1. Basic information

### 1.1 AI Use Case Profile
- **Title**: Manager Performance Assessment Assistant
- **Summary**: A mobile-first AI tool that synthesizes performance data and manager-logged notes to help draft objective staff evaluations.

### 1.2 Establishing Impact Assessment Responsibilities
- **Assessing Officer**: Not stated in the outline.
- **Approving Officer**: Not stated in the outline.

### 1.3 Additional Roles and Responsibilities
- Not stated in the outline.

### 1.4 AI Use Case Description
The proposed system is a mobile-first AI-powered assessment tool designed to assist managers in drafting objective staff evaluations. It analyzes and synthesizes performance data, goal-tracking records, and manager-logged feedback notes to generate draft performance summaries and development suggestions for managers to review and finalize.

### 1.5 In-Scope Use Case
Yes. The system uses AI to analyze and synthesize performance data to generate draft evaluations for human review.

### 1.6 Type of AI Technology
Natural Language Processing (NLP) and Generative AI (specifically text synthesis and summarisation).

### 1.7 Usage Pattern
Human-in-the-loop: The AI generates draft performance summaries and development suggestions, which are then reviewed, edited, and finalized by the manager.

### 1.8 Administrative Decisions
The AI drafts evaluations that directly influence performance assessments, which may subsequently affect administrative decisions regarding staff development, retention, or promotion. The final decisions are made by the managers, but the AI's drafts directly influence them.

### 1.9 Domain
Human Resources / Internal Staff Performance Management.

### 1.10 Expert Contributions
- Not stated in the outline.

### 1.11 Impact Assessment Review Log
- Not stated in the outline.

## 2. Purpose and expected benefits

### 2.1 Problem Definition
Managers frequently struggle to provide consistent, objective, and timely performance feedback to their staff. This difficulty leads to gaps in staff development and introduces potential bias into performance evaluations.

### 2.2 AI Use Case Purpose
To assist managers by analyzing performance data and feedback logs to generate draft performance summaries and development suggestions, thereby improving feedback consistency, timeliness, and reducing evaluation bias.

### 2.3 Non-AI Alternatives
- Not stated in the outline.

### 2.4 Identifying Stakeholders
- **Primary Users**: Managers who input notes and review/approve the AI-generated summaries.
- **Primary Stakeholders Affected**: Staff members whose performance evaluations and development pathways are shaped by these assessments.

### 2.5 Expected Benefits
- Improved consistency and objectivity in staff evaluations.
- More timely feedback delivery.
- Reduced bias in performance assessments.
- Better identified development opportunities for staff.

## 3. Inherent risk assessment

| Area | Consequence | Likelihood | Risk rating |
| --- | --- | --- | --- |
| 3.1 Reducing service accessibility and inclusion | Moderate | Possible | Medium |
| 3.2 Unfair discrimination | Moderate | Possible | Medium |
| 3.3 Stereotyping or demeaning representations | Moderate | Possible | Medium |
| 3.4 Harm | Moderate | Possible | Medium |
| 3.5 Privacy concerns | Moderate | Possible | Medium |
| 3.6 Security concerns — data aspects | Moderate | Possible | Medium |
| 3.7 Security concerns — system aspects | Moderate | Possible | Medium |
| 3.8 Reputation or public confidence | Moderate | Possible | Medium |

**3.9 Overall inherent risk rating (highest-wins): Medium**

### 3.1 Reducing service accessibility and inclusion

The outline specifies a "mobile-first" application. If the mobile interface or the generated summaries are not fully accessible or optimized for assistive technologies, managers with visual, motor, or cognitive impairments may face barriers when inputting notes or reviewing drafts. Since accessibility measures are not explicitly stated in the outline, a precautionary moderate consequence and possible likelihood are applied.

### 3.2 Unfair discrimination

The AI will process internal performance review documents, goal-tracking data, and feedback logs to generate evaluations. Performance evaluations are highly susceptible to systemic bias. AI models trained on or synthesizing unstructured feedback logs and meeting transcripts may replicate or amplify historical biases against minority groups, women, or neurodivergent staff. Given the direct impact on careers and the lack of stated bias-mitigation strategies in the outline, this risk is considered possible with moderate consequences.

### 3.3 Stereotyping or demeaning representations

Language models used to synthesize natural language notes and transcripts can generate coded or gendered language (e.g., describing assertive behavior differently based on gender). Without explicit guardrails detailed in the outline, there is a possible risk of perpetuating harmful stereotypes in staff evaluations, warranting a moderate consequence rating.

### 3.4 Harm

Biased, inaccurate, or unfair performance summaries can lead to tangible professional, financial, and psychological harm for staff members. This includes unfair performance ratings, missed promotion opportunities, career stagnation, or distress. Because evaluations directly affect careers and livelihoods, the potential consequence is moderate and the likelihood is possible.

### 3.5 Privacy concerns

The system will process highly sensitive HR data, including performance reviews, goal-tracking data, and potentially "anonymized meeting transcripts or feedback logs." If the anonymization of transcripts is incomplete, or if sensitive personal disclosures made during meetings are processed and exposed by the AI, it poses a moderate privacy risk with a possible likelihood.

### 3.6 Security concerns — data aspects

Internal performance data and meeting transcripts are highly confidential. A data breach compromising this information could expose sensitive organizational dynamics and personal employee details. Given the mobile-first deployment, data security is critical, leading to a precautionary selection of moderate consequence and possible likelihood.

### 3.7 Security concerns — system aspects

Deploying a mobile-first application that handles sensitive HR data and integrates with internal databases and AI APIs introduces specific system security risks. Vulnerabilities such as insecure local data caching on mobile devices, API exploits, or unauthorized access if a device is lost could expose sensitive employee records. Precautionarily, this is rated as a moderate consequence with a possible likelihood.

### 3.8 Reputation or public confidence

Using AI to draft employee performance evaluations could attract negative attention from staff, unions, or the public if perceived as outsourcing human leadership and merit-based assessments to algorithms. If the system is viewed as biased or insecure, it could undermine trust in public service administration and internal governance, warranting a moderate consequence and possible likelihood.

## 4. Threshold assessment outcome

### 4.1 Assessing Officer Recommendation
Based on the preliminary threshold assessment of the "Manager Performance Assessment Assistant," the proposed system introduces several areas of notable risk that warrant careful management. The system processes highly sensitive personal and professional information—including performance reviews, goal-tracking data, and potentially un-anonymized meeting transcripts. Because the outputs directly influence staff performance evaluations, career progression, and development opportunities, there are inherent risks regarding algorithmic bias, unfair discrimination, and privacy.

While the system maintains a human-in-the-loop pattern where managers must review and approve all drafts, the potential for automation bias (where managers over-rely on AI-generated drafts without critical review) remains a key concern. Furthermore, the mobile-first design introduces specific accessibility and security considerations.

To ensure safe, fair, and transparent deployment, it is recommended that the project team undertake the following actions:
1. **Conduct a Privacy Impact Assessment (PIA)** to address the collection, storage, and processing of sensitive employee data and transcripts, ensuring robust data minimization and anonymization.
2. **Establish Rigorous Bias Testing** on the synthesis models to ensure they do not perpetuate or amplify gendered, racial, or neurodivergent biases in performance feedback.
3. **Perform an Accessibility Audit** of the mobile interface to ensure all managers, including those with disabilities, can fully utilize the tool.
4. **Implement Clear Human-in-the-Loop Protocols** to ensure managers remain fully accountable for the final evaluations and do not defer uncritically to AI-generated drafts.
5. **Review System Security** to address mobile-specific vulnerabilities, such as insecure local data caching or API risks.

A cautious, precautionary approach should be maintained throughout the design and deployment phases to safeguard employee trust and ensure compliance with privacy and anti-discrimination standards.

A full assessment is **required**.
