# Threshold AI impact assessment — WT-J29D-R9

## 1. Basic information

### 1.1 AI use case profile
- **Title:** Automated Web Compliance Monitor
- **Run ID:** WT-J29D-R9
- **Summary:** An internal AI-driven tool to identify and streamline the registration of problematic websites through human-in-the-loop oversight and continuous model refinement.

### 1.2 Establishing impact assessment responsibilities
Not stated in the outline.

### 1.3 Additional roles and responsibilities
Not stated in the outline.

### 1.4 AI use case description
The proposed system is an internal AI-powered monitoring tool designed to scan web content across a target list of domains. It identifies websites meeting specific 'problematic' criteria and flags them for human review. The system provides compliance officers with a visual snapshot of the page, highlighted text, and an explicit confidence score to assist in their evaluation.

### 1.5 In-scope use case
Yes, the system is in-scope as it utilizes AI to analyze web content and assist in administrative workflows to track problematic websites requiring registration or intervention.

### 1.6 Type of AI technology
AI-driven web content scanning and contextual classification, featuring confidence scoring and a feedback mechanism for model refinement.

### 1.7 Usage pattern
Internal deployment on containerized infrastructure. The tool operates with a strict human-in-the-loop pattern, where AI outputs are reviewed by compliance officers via a web-based dashboard who must manually approve or reject the registration action.

### 1.8 Administrative decisions
The AI system does not make automated administrative decisions. It flags potential violations, and a human compliance officer must review the evidence and manually click 'register' to initiate any formal administrative action.

### 1.9 Domain
Web compliance, regulatory oversight, and registry management.

### 1.10 Expert contributions
Not stated in the outline.

### 1.11 Impact assessment review log
Not stated in the outline.

## 2. Purpose and expected benefits

### 2.1 Problem definition
Public servants currently lack an efficient way to identify and track problematic websites that require registration or intervention, leading to manual, slow, and inconsistent oversight.

### 2.2 AI use case purpose
To automate the scanning of web content across target domains to identify sites meeting specific 'problematic' criteria, thereby streamlining the workflow for human review and subsequent administrative action.

### 2.3 Non-AI alternatives
Manual web crawling and reporting by staff, or using standard keyword-based web filtering tools that lack the contextual understanding of AI.

### 2.4 Identifying stakeholders
- **Primary Users:** Compliance officers and administrative staff who review flagged sites and manage registrations.
- **Affected Stakeholders:** Members of the public who interact with the monitored websites, and the IT teams responsible for managing the registry infrastructure.

### 2.5 Expected benefits
- A measurable reduction in the time taken to identify and register problematic sites compared to the current manual baseline.
- A high officer-approval rate for AI-flagged items, indicating precise and useful targeting.

## 3. Inherent risk assessment

| Area | Consequence | Likelihood | Risk rating |
| --- | --- | --- | --- |
| 3.1 Reducing service accessibility and inclusion | Moderate | Possible | Medium |
| 3.2 Unfair discrimination | Moderate | Possible | Medium |
| 3.3 Stereotyping or demeaning representations | Moderate | Possible | Medium |
| 3.4 Harm | Moderate | Possible | Medium |
| 3.5 Privacy concerns | Moderate | Likely | Medium |
| 3.6 Security concerns — data aspects | Moderate | Possible | Medium |
| 3.7 Security concerns — system aspects | Moderate | Possible | Medium |
| 3.8 Reputation or public confidence | Moderate | Possible | Medium |

**3.9 Overall inherent risk rating (highest-wins): Medium**

### 3.1 Reducing service accessibility and inclusion

If the AI systematically misidentifies certain types of websites or fails to identify truly problematic ones, it could lead to unjustified administrative actions or delayed interventions, causing noticeable access issues for some groups. Given the complexity of contextual web analysis, errors are possible in the foreseeable future.

### 3.2 Unfair discrimination

The AI scans web content to identify 'problematic' criteria. If the training data or classification logic contains implicit biases, it may disproportionately flag websites associated with specific cultural, linguistic, or marginalized groups. While a human reviews the flags, confirmation bias or high volume could lead to unfair administrative actions.

### 3.3 Stereotyping or demeaning representations

If the AI's classification criteria for 'problematic' content rely on or generate biased associations, it could systematically flag and penalize sites representing minority views or cultural practices, reinforcing harmful stereotypes.

### 3.4 Harm

Incorrectly registering a website as 'problematic' can cause financial distress, reputational damage, or operational disruption to the business or individual running the site. Although there is a human-in-the-loop, the potential for human error or rubber-stamping exists, making this harm possible.

### 3.5 Privacy concerns

The system processes public web content, URLs, and metadata, and stores snapshots as long-term legal evidence. Because public websites frequently contain personal information or sensitive user-generated content, it is likely that privacy concerns will arise regarding the long-term storage of these snapshots.

*Divergence: Assessor A assessed the likelihood as Possible, while Assessor B assessed it as Likely. The higher likelihood (Likely) stands because public websites frequently contain personal information, making privacy concerns highly probable when capturing and storing long-term snapshots.*

### 3.6 Security concerns — data aspects

The system stores snapshots as long-term legal evidence in an immutable, WORM-compliant environment. While strict access controls and cryptographic hashing are planned, the aggregation of flagged 'problematic' site data represents a high-value target for unauthorized access or leaks, which could expose sensitive compliance investigations.

### 3.7 Security concerns — system aspects

The system is deployed on internal, containerized infrastructure. Vulnerabilities in the container environment, the web-based dashboard, or the automated crawling mechanism could be exploited, potentially exposing the target list of domains or the internal registry.

### 3.8 Reputation or public confidence

Automated monitoring of web content by a government agency carries inherent reputational risks. If the AI system produces high rates of false positives, or if it is perceived as an automated government surveillance tool targeting specific online communities, it could undermine public confidence in the agency's regulatory fairness and oversight.

## 4. Threshold assessment outcome

### 4.1 Assessing officer recommendation
The Automated Web Compliance Monitor presents a clear opportunity to improve the efficiency and consistency of identifying problematic websites. However, because the system's outputs trigger formal administrative actions (registration), several inherent risks must be carefully managed.

The following recommendations are made to guide the next stages of project development:

1. **Establish Clear 'Problematic' Criteria:** To mitigate risks of unfair discrimination and stereotyping, the criteria used by the AI to classify content must be transparently defined, documented, and regularly audited for bias.
2. **Mitigate Automation Bias:** Ensure that compliance officers receive training on how to interpret confidence scores, particularly low-confidence flags, to prevent "rubber-stamping" of AI recommendations.
3. **Validate Data Security and Privacy:** Given that snapshots are stored as long-term legal evidence in an immutable, WORM-compliant environment, a comprehensive privacy impact assessment and security review of the containerized infrastructure must be conducted to protect potentially sensitive metadata and public web content.
4. **Implement a Robust Feedback Loop:** The proposed feedback mechanism for false positives should be actively monitored to ensure continuous model refinement and to minimize systemic errors over time.

A full assessment is **required**.
