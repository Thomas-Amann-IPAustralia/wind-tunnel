# Threshold AI impact assessment — WT-FXD5-3G

## 1. Basic information

### 1.1 AI use case profile
- **Name**: ATO Deduction Assistant
- **Run ID**: WT-FXD5-3G
- **Summary**: A public-facing chatbot using RAG and a user-adjustable 'creativity' dial to provide guidance on tax deduction eligibility while maintaining clear boundaries between advice and policy.

### 1.2 Establishing impact assessment responsibilities
- *Not stated in the outline.*

### 1.3 Additional roles and responsibilities
- *Not stated in the outline.*

### 1.4 AI use case description
The ATO Deduction Assistant is a public-facing chatbot hosted by the ATO. It provides guidance on eligible tax deductions based on user-provided employment or expense details. The system utilizes a Large Language Model (LLM) to interpret tax policy documents and features a Retrieval-Augmented Generation (RAG) architecture. The user interface includes a web-based chat integrated into the existing ATO portal, featuring a 'creativity' dial that serves as a meta-signal for system fallibility, alongside mandatory disclaimers and direct links to official policy documentation for verification.

### 1.5 In-scope use case
Yes, the system is a public-facing advisory tool designed to assist individual taxpayers with tax deduction guidance.

### 1.6 Type of AI technology
- Large Language Model (LLM)
- Retrieval-Augmented Generation (RAG)

### 1.7 Usage pattern
Public-facing interactive web-based chat interface integrated into the ATO portal.

### 1.8 Administrative decisions
No. The system is strictly advisory, includes prominent disclaimers, and has no integration with live taxpayer account data to ensure it does not make legally binding administrative decisions.

### 1.9 Domain
Taxation and Public Administration.

### 1.10 Expert contributions
- *Not stated in the outline.*

### 1.11 Impact assessment review log
- *Not stated in the outline.*

## 2. Purpose and expected benefits

### 2.1 Problem definition
Taxpayers often struggle to navigate complex deduction rules, leading to errors in their returns or unnecessary inquiries to the ATO.

### 2.2 AI use case purpose
To provide accessible, interactive guidance on tax deduction eligibility based on user-provided employment or expense details, helping taxpayers interpret complex tax policy documents before submitting their returns.

### 2.3 Non-AI alternatives
Non-AI alternatives considered include an interactive decision tree or a static FAQ wizard. While highly accurate, these alternatives often fail to capture the nuance of unique taxpayer scenarios, which is why a RAG-based LLM is being explored.

### 2.4 Identifying stakeholders
- **Primary Users**: Individual taxpayers.
- **Internal Stakeholders**: ATO support staff and policy teams responsible for the accuracy of the guidance.

### 2.5 Expected benefits
- Reduction in general inquiry call volume to the ATO.
- High rate of user click-throughs to official policy documentation.
- Positive sentiment scores regarding the clarity of guidance provided.
- Maintaining zero instances of the bot providing legally binding advice.

## 3. Inherent risk assessment

| Area | Consequence | Likelihood | Risk rating |
| --- | --- | --- | --- |
| 3.1 Reducing service accessibility and inclusion | Moderate | Possible | Medium |
| 3.2 Unfair discrimination | Moderate | Possible | Medium |
| 3.3 Stereotyping or demeaning representations | Minor | Possible | Medium |
| 3.4 Harm | Moderate | Possible | Medium |
| 3.5 Privacy concerns | Moderate | Possible | Medium |
| 3.6 Security concerns — data aspects | Moderate | Possible | Medium |
| 3.7 Security concerns — system aspects | Moderate | Possible | Medium |
| 3.8 Reputation or public confidence | Major | Possible | High |

**3.9 Overall inherent risk rating (highest-wins): High**

### 3.1 Reducing service accessibility and inclusion

The chatbot is public-facing on the ATO portal and intended for individual taxpayers. Introducing a 'creativity' dial as a UX element, while intended as a meta-signal for fallibility, may confuse users with lower digital or financial literacy, cognitive disabilities, or those who require highly consistent and predictable interfaces. This could create noticeable access barriers or lead to incorrect interpretations of tax eligibility for certain groups.

### 3.2 Unfair discrimination

Taxpayers present highly diverse financial and employment scenarios. LLMs can exhibit subtle biases based on the phrasing of user queries or the training data. If the RAG system interprets tax policy differently or provides inconsistent guidance for non-standard employment types (e.g., gig economy workers or sole traders) compared to standard wage earners, it could lead to perceived or actual unfair treatment, resulting in noticeable bias concerns requiring manual intervention.

### 3.3 Stereotyping or demeaning representations

While the system is grounded in neutral official ATO tax policy documents via RAG, the LLM processes user-provided financial scenarios. Because LLMs are generative, there is a possibility that the model could generate responses reflecting occupational or socioeconomic stereotypes based on the user's input. These would likely be isolated incidents with minor consequences, but they remain a foreseeable possibility.

*Divergence: Assessor A said Unlikely, Assessor B said Possible; the higher likelihood (Possible) stands because the LLM processes user-provided free-text financial scenarios, making isolated incidents of stereotyping a foreseeable possibility.*

### 3.4 Harm

If the chatbot provides incorrect or misleading guidance on deduction eligibility (potentially exacerbated by a user turning up the 'creativity' dial), taxpayers may submit incorrect returns. Even with disclaimers, users often place high trust in official government portals. This could result in financial penalties, audits, and subsequent distress for individuals, representing noticeable harm.

### 3.5 Privacy concerns

Although the system is strictly isolated from live taxpayer account data, users interacting with a free-text chat interface are prompted to input their own financial scenarios. There is a foreseeable risk that users will input highly sensitive personal financial details or Tax File Numbers (TFNs) despite disclaimers, raising noticeable privacy and data handling concerns.

### 3.6 Security concerns — data aspects

The system processes user-provided financial scenarios. If these interactive sessions or prompt logs are compromised, leaked, or accessed by unauthorized parties, it could lead to a moderate compromise of sensitive user-disclosed financial data, raising privacy concerns that require investigation.

*Divergence: Assessor A said Minor/Unlikely, Assessor B said Moderate/Possible; the higher tiers (Moderate/Possible) stand because users may input sensitive financial information into the chat, and a compromise of these logs could lead to a moderate data compromise.*

### 3.7 Security concerns — system aspects

Public-facing LLM interfaces are frequent targets for system-level exploits such as prompt injection or jailbreaking. A successful exploit could cause the system to bypass guardrails, output inappropriate content, or leak user session histories, presenting a contained but serious system security issue.

### 3.8 Reputation or public confidence

The ATO is a high-profile government agency where public trust is critical. Any public failure, hallucination, or incorrect tax guidance provided by an official ATO chatbot—especially one featuring an adjustable 'creativity' dial that could be perceived as gamifying tax compliance—would likely attract significant media scrutiny, damage the agency's reputation, and undermine public confidence in official digital services.

## 4. Threshold assessment outcome

### 4.1 Assessing officer recommendation
It is recommended that the ATO Deduction Assistant project proceed with a highly precautionary implementation strategy. The proposed system introduces a public-facing generative AI interface into a highly sensitive domain (taxation). While the tool is strictly advisory and isolated from live taxpayer account data, its public-facing nature and the use of an LLM present inherent risks of generating inaccurate or misleading tax guidance.

In particular, the inclusion of a user-adjustable 'creativity' dial—while intended as a meta-signal for fallibility—introduces unpredictable variance in LLM outputs that could confuse users, create accessibility barriers, or undermine the perceived authority of the guidance. Before deployment, robust guardrails must be established around the RAG pipeline, and the 'creativity' dial's parameters must be strictly bounded. Extensive red-teaming against prompt injection is required. Furthermore, clear, prominent disclaimers must be paired with robust logging of user interactions to monitor for potential drift or hallucinated advice. A structured feedback loop with ATO policy teams should be established to continuously verify the accuracy of the RAG source documents and ensure the system consistently directs users to official policy documents for final verification.

A full assessment is **required**.

Overall inherent risk is **High** — refer to an internal governance body (§12.5).
