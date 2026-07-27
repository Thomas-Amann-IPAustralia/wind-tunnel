# Threshold AI impact assessment — WT-GCDX-T3

## 1. Basic information

### 1.1 AI Use Case Profile
- **Title:** Policy Impact Mapper (WT-GCDX-T3)
- **Summary:** An AI tool that automates the identification of internal policy dependencies by cross-referencing new legislation against a version-controlled snapshot of agency documentation.
- **Status:** Proof of Concept (POC) stage.

### 1.2 Establishing Impact Assessment Responsibilities
Not stated in the outline.

### 1.3 Additional Roles and Responsibilities
Not stated in the outline.

### 1.4 AI Use Case Description
The Policy Impact Mapper is an AI-powered decision-support tool designed to automate the identification of internal policy dependencies. It ingests new legislative or regulatory requirements and cross-references them against a version-controlled snapshot of the agency's internal document repository. The system flags affected policies, forms, and processes, providing clear citations and maintaining an audit trail of the document versions used.

### 1.5 In-scope Use Case
Yes. The tool is used to map legislative changes to internal agency frameworks to support compliance and operational alignment for policy, legal, compliance, and operational staff.

### 1.6 Type of AI Technology
AI-powered impact mapping and semantic retrieval tool. The specific underlying model architecture is not explicitly detailed, though it relies on semantic understanding of legislative intent rather than simple keyword matching.

### 1.7 Usage Pattern
Decision-support tool (human-in-the-loop). Users upload source text, view a generated impact map, and interact with a 'review/reject/assign' workflow. No automated changes are made.

### 1.8 Administrative Decisions
No automated administrative decisions are made by this system. It is strictly restricted to a decision-support tool with no automated changes to policies or systems.

### 1.9 Domain
Government administration, internal policy, compliance, and legal frameworks.

### 1.10 Expert Contributions
Not stated in the outline.

### 1.11 Impact Assessment Review Log
Not stated in the outline.

## 2. Purpose and expected benefits

### 2.1 Problem Definition
Government agencies struggle to manually track how new legislation or policy updates impact existing internal frameworks. This manual process leads to slow response times and carries a significant risk of missing critical policy dependencies.

### 2.2 AI Use Case Purpose
To streamline and automate the identification of internal policy dependencies by cross-referencing new legislation against a curated, version-controlled snapshot of agency documentation, flagging affected policies, forms, and processes with clear citations for human review.

### 2.3 Non-AI Alternatives
Manual review via cross-departmental working groups (the current state), or keyword-based search tools that lack the semantic understanding required to interpret legislative intent and complex policy relationships.

### 2.4 Identifying Stakeholders
- **Primary Users:** Policy, legal, compliance, and operational staff within the agency.
- **Affected Stakeholders:** Frontline staff and members of the public who rely on accurate, up-to-date, and legally compliant agency guidance.

### 2.5 Expected Benefits
- Faster discovery and mapping of policy dependencies compared to manual review.
- Reduced risk of missing critical legislative dependencies.
- Improved accuracy of internal guidance through systematic cross-referencing.
- Clear audit trails of document versions used during analysis, reducing version conflicts.

## 3. Inherent risk assessment

| Area | Consequence | Likelihood | Risk rating |
| --- | --- | --- | --- |
| 3.1 Reducing service accessibility and inclusion | Moderate | Possible | Medium |
| 3.2 Unfair discrimination | Moderate | Possible | Medium |
| 3.3 Stereotyping or demeaning representations | Minor | Possible | Medium |
| 3.4 Harm | Moderate | Possible | Medium |
| 3.5 Privacy concerns | Minor | Possible | Medium |
| 3.6 Security concerns — data aspects | Moderate | Possible | Medium |
| 3.7 Security concerns — system aspects | Moderate | Possible | Medium |
| 3.8 Reputation or public confidence | Moderate | Possible | Medium |

**3.9 Overall inherent risk rating (highest-wins): Medium**

### 3.1 Reducing service accessibility and inclusion

If the tool fails to identify a critical legislative dependency (a false negative), internal policies and forms may not be updated. This could result in frontline staff continuing to operate under outdated guidelines, leading to noticeable access issues or incorrect service delivery for specific cohorts of the public. Given the reliance on the tool, this is a possible occurrence.

### 3.2 Unfair discrimination

If the AI misinterprets legislative intent or fails to flag a legislative change that removes a discriminatory barrier or introduces new protections, the agency may continue to apply outdated, discriminatory internal policies. While human review is mandatory, automation bias might lead officers to overlook these omissions, resulting in noticeable harm to some individuals or groups before the issue is identified and corrected.

### 3.3 Stereotyping or demeaning representations

The system processes formal legislative texts and curated internal policy documents, which are highly structured and unlikely to contain demeaning representations. However, semantic mapping tools or underlying language models can occasionally generate or perpetuate subtle, biased representations or mischaracterizations, or surface outdated terminology from historical documents. If this occurs, it would likely represent an isolated incident that can be quickly corrected.

*Divergence: Assessor A said Unlikely, Assessor B said Possible; the higher (Possible) stands because under precautionary defaults, semantic mapping tools or underlying language models can occasionally generate or perpetuate subtle, biased representations or mischaracterizations.*

### 3.4 Harm

A failure to identify a critical legislative dependency (e.g., a change in safety standards, compliance obligations, or financial entitlements) could result in the agency operating out of alignment with the law. This could cause noticeable operational, financial, or regulatory harm to the organisation and the public relying on its services. Given the complexity of legislative interpretation, this is a possible occurrence if human reviewers rely too heavily on the tool.

### 3.5 Privacy concerns

The system is designed to process unclassified internal policy documents and public legislation. While it is not intended to handle sensitive personal information, internal documents and metadata (such as owner names, status, and internal dates) are ingested. There is a possibility that internal documents may contain minor personal data (e.g., staff contact details). A minor breach or exposure of this data is possible but would cause limited distress and be quickly resolved.

### 3.6 Security concerns — data aspects

Although restricted to unclassified data, the system ingests a comprehensive snapshot of the agency's internal document repository. A security compromise of this data store or the tool's database could expose sensitive internal operational procedures, guidelines, or draft policies, raising moderate security and privacy concerns that would require investigation.

### 3.7 Security concerns — system aspects

The system uses a web-based dashboard for uploading source text and interacting with policy mappings. A vulnerability in this interface, the underlying document ingestion pipeline, or the integration of the AI system could lead to unauthorized access or data leaks of internal policy structures, which is a serious but containable system security concern.

### 3.8 Reputation or public confidence

If the agency fails to implement a major legislative change because the AI tool missed the dependency, and this leads to incorrect service delivery or legal non-compliance, it would likely attract media attention and public scrutiny. This would raise questions about the agency's oversight of its AI tools, causing a moderate impact on public trust that requires a remedial response.

## 4. Threshold assessment outcome

### 4.1 Assessing Officer Recommendation
The Policy Impact Mapper (WT-GCDX-T3) is proposed as a decision-support tool to assist policy and compliance staff in mapping legislative changes to internal agency documents. While the tool maintains a human-in-the-loop workflow and is restricted to unclassified data, several inherent risks must be carefully managed. Specifically, the risk of false negatives (missing critical policy dependencies) could lead to operational non-compliance, outdated public guidance, and subsequent reputational damage. It is recommended that the project proceed with a strong focus on establishing robust human-in-the-loop verification protocols.

To mitigate risks during the POC and subsequent phases, the project team should:
1. **Address Automation Bias:** Implement mandatory training and clear guidelines for policy officers to ensure they critically evaluate and verify all AI-generated suggestions rather than accepting them reflexively, emphasizing that the tool does not replace comprehensive manual legal review.
2. **Rigorous Calibration:** Fully leverage the 'gold standard' set of 10-15 historical changes to calibrate retrieval rules, glossary usage, and confidence thresholds before any live testing occurs.
3. **Maintain Strict Data Governance:** Ensure the 'frozen' document set used for the POC is securely managed, and establish clear procedures for transitioning to live, version-controlled document feeds in future phases.
4. **Establish Feedback Loops:** Systematically categorize and analyze false positives and false negatives during the POC, continuously monitoring the ratio of confirmed versus rejected suggestions to refine the retrieval logic and ensure ongoing accuracy and safety.

A full assessment is **required**.
