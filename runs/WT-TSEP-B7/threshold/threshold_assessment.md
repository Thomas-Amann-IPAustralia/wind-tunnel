# Threshold AI impact assessment — WT-TSEP-B7

## 1. Basic information

### Section 1 — Basic information

* **1.1 AI use case profile**: C&D Claim Evaluator (Run ID: WT-TSEP-B7).
* **1.2 Establishing impact assessment responsibilities**: Not stated in the outline.
* **1.3 Additional roles and responsibilities**: Not stated in the outline.
* **1.4 AI use case description**: A public-facing chatbot hosted on business.gov where users upload or paste a cease and desist letter. The AI analyzes the unstructured text against common legal standards and regulatory frameworks to identify potentially invalid or unenforceable claims, providing links to relevant business.gov guidance articles.
* **1.5 In-scope use case**: Yes, this is an active deployment of an AI-enabled chatbot on a public government portal (business.gov).
* **1.6 Type of AI technology**: Natural Language Processing (NLP) / Generative AI chatbot capable of parsing unstructured text and comparing it against legal frameworks.
* **1.7 Usage pattern**: Web-based chat interface with a document upload feature.
* **1.8 Administrative decisions**: Not stated in the outline. (The tool is intended to be informational and not a substitute for professional legal counsel, suggesting it does not make formal administrative decisions).
* **1.9 Domain**: Small business support, legal information, and regulatory guidance.
* **1.10 Expert contributions**: Not stated in the outline.
* **1.11 Impact assessment review log**: Not stated in the outline.

## 2. Purpose and expected benefits

### Section 2 — Purpose and expected benefits

* **2.1 Problem definition**: Small business owners often receive cease and desist letters that may contain illegitimate or bullying claims. However, they frequently lack the financial and legal resources to hire professional counsel to evaluate the validity of every demand they receive.
* **2.2 AI use case purpose**: To provide an accessible, automated tool that analyzes the text of cease and desist letters against common legal standards to help small business owners identify potentially invalid or unenforceable claims, thereby empowering them with educational resources.
* **2.3 Non-AI alternatives**: A static, comprehensive 'self-help' guide or checklist hosted on business.gov that teaches business owners how to spot common red flags themselves.
* **2.4 Identifying stakeholders**: Primary users are small business owners. Other stakeholders include the business.gov legal team, the general public, and the entities sending the cease and desist letters (who may face increased scrutiny).
* **2.5 Expected benefits**: A reduction in user-reported confusion regarding legal notices and high engagement with the provided educational resources within six months of deployment.

## 3. Inherent risk assessment

| Area | Consequence | Likelihood | Risk rating |
| --- | --- | --- | --- |
| 3.1 Reducing service accessibility and inclusion | Moderate | Possible | Medium |
| 3.2 Unfair discrimination | Moderate | Possible | Medium |
| 3.3 Stereotyping or demeaning representations | Minor | Possible | Medium |
| 3.4 Harm | Major | Possible | High |
| 3.5 Privacy concerns | Moderate | Possible | Medium |
| 3.6 Security concerns — data aspects | Moderate | Possible | Medium |
| 3.7 Security concerns — system aspects | Moderate | Possible | Medium |
| 3.8 Reputation or public confidence | Major | Possible | High |

**3.9 Overall inherent risk rating (highest-wins): High**

### 3.1 Reducing service accessibility and inclusion

The tool is public-facing and relies on a web-based chat interface and PDF document uploads. Users with accessibility needs, limited English proficiency, or low digital literacy may face barriers accessing the tool or understanding its outputs. If the document parser fails to read certain formats or if the interface is not fully compliant with accessibility standards, users will face noticeable access issues. Under the precautionary principle, since accessibility testing and mitigation strategies are not stated in the outline, we assess a Moderate consequence and a Possible likelihood.

### 3.2 Unfair discrimination

AI models analyzing legal claims may exhibit bias based on jurisdiction, language style, or the nature of the parties involved. If the model performs poorly on non-standard English or interprets legal language in a biased manner, it could provide lower-quality or misleading analyses to culturally and linguistically diverse business owners. In line with the precautionary principle, this risk of unfair treatment or incorrect assessments for specific groups is rated as a Moderate consequence with a Possible likelihood.

### 3.3 Stereotyping or demeaning representations

While the primary task is legal document analysis, generative AI chatbots can generate biased, stereotyping, or demeaning language if prompted in unexpected ways or if the underlying model contains latent biases. Given the lack of detail on conversational guardrails in the outline, we apply the precautionary default of a Minor consequence and a Possible likelihood.

### 3.4 Harm

If the chatbot incorrectly identifies a legally valid and enforceable cease and desist claim as "illegitimate" or "unenforceable," a small business owner might ignore the letter. Despite the persistent disclaimer, users are highly likely to rely on the tool's specific analysis. This could result in severe legal consequences, including costly litigation, statutory damages, or business closure. Under the precautionary principle, this potential for significant financial and operational distress is classified as a Major consequence with a Possible likelihood.

### 3.5 Privacy concerns

Users upload highly sensitive legal documents containing private disputes and potentially proprietary business information. Although the outline specifies a preference for strict data privacy controls to prevent model training, the risk of data leaks, unauthorized access, or accidental exposure of these sensitive uploads remains. Any data leak would cause noticeable distress and privacy concerns. We precautionarily rate this as a Moderate consequence and a Possible likelihood.

### 3.6 Security concerns — data aspects

The system processes unstructured text from active legal disputes, which is highly sensitive. A security breach of the business.gov infrastructure hosting these uploaded documents could compromise proprietary business data and private legal strategies, raising serious privacy and legal concerns. In the absence of detailed security architecture in the outline, we apply the precautionary default of a Moderate consequence and a Possible likelihood.

### 3.7 Security concerns — system aspects

Implementing a public-facing document upload and parsing feature on business.gov infrastructure introduces known system vulnerabilities (e.g., malicious file uploads, prompt injection attacks, or system exploits). A vulnerability could lead to unauthorized access, data leaks, or service disruption. We cautiously rate this as a Moderate consequence and a Possible likelihood.

### 3.8 Reputation or public confidence

Because the tool is hosted on the official business.gov platform, users will associate its outputs directly with government authority. If the AI provides incorrect legal guidance that leads to financial loss for small businesses, or if sensitive legal documents uploaded by users are leaked, it would trigger widespread public criticism and severely damage trust in business.gov as a reliable government portal. Under the precautionary principle, this is rated as a Major consequence and a Possible likelihood.

## 4. Threshold assessment outcome

### 4.1 Assessing officer recommendation

The proposed "C&D Claim Evaluator" chatbot offers a highly innovative, self-help mechanism for resource-constrained small business owners facing legal pressure. However, because the tool performs automated analysis on unstructured legal documents and provides assessments on the validity of legal claims, it carries substantial inherent risks.

Key areas of concern include the potential for severe financial and legal harm if a user acts on incorrect AI advice (e.g., ignoring a valid legal notice), privacy risks associated with uploading highly sensitive and proprietary legal disputes, and system security risks inherent to public-facing document upload features.

To safely progress this initiative, it is recommended that the project team conduct rigorous testing of the AI's analytical accuracy, implement strict data-handling and privacy controls to ensure uploaded documents are secure and never used for model training, and design highly visible, legally robust disclaimers to ensure users understand the tool is strictly educational and not a substitute for professional legal counsel. Further detailed risk mitigation planning and stakeholder consultation with legal experts are strongly advised before proceeding to development.

A full assessment is **required**.

Overall inherent risk is **High** — refer to an internal governance body (§12.5).
