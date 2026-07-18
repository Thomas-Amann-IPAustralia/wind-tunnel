# Threshold AI impact assessment — WT-PX5H-3D

## 1. Basic information

# Section 1 — Basic information

### 1.1 AI use case profile
* **Project Name:** APS Tech Navigator
* **Run ID:** WT-PX5H-3D
* **Summary:** An AI-powered chatbot designed to help public servants identify and navigate technology solutions for their operational challenges.

### 1.2 Establishing impact assessment responsibilities
Not stated in the outline.

### 1.3 Additional roles and responsibilities
Not stated in the outline.

### 1.4 AI use case description
The APS Tech Navigator is a web-based, AI-powered chatbot interface that acts as a technical advisor. It guides APS staff through their specific operational problems and suggests appropriate technology solutions or pathways based on internal OFFICIAL information and publicly available data. The system engages in a back-and-forth dialogue, asking clarifying questions to identify bottlenecks, and synthesizes the conversation into a draft project brief or a list of recommended technical pathways.

### 1.5 In-scope use case
Yes, this is an in-scope AI system designed for internal use within the Australian Public Service (APS) to assist staff with operational problem-solving and drafting project briefs.

### 1.6 Type of AI technology
Generative AI, Natural Language Processing (NLP), and Large Language Models (LLM) capable of interactive dialogue, synthesis of unstructured text, and document drafting.

### 1.7 Usage pattern
Interactive dialogue via a web-based browser application featuring a voice-enabled chat interface. Users engage in a back-and-forth voice or text dialogue, and the system provides text-based outputs or draft documents.

### 1.8 Administrative decisions
The system does not make administrative decisions. It acts as an interactive thought partner, providing recommendations and draft briefs that the user must review and refine.

### 1.9 Domain
Government administration, internal APS operational support, IT advisory, and procurement pathway navigation.

### 1.10 Expert contributions
Not stated in the outline.

### 1.11 Impact assessment review log
Not stated in the outline.

## 2. Purpose and expected benefits

# Section 2 — Purpose and expected benefits

### 2.1 Problem definition
Public servants in the APS often lack the technical literacy or awareness of available tools to effectively identify and solve operational problems. This leads to a gap between identifying an operational need and knowing how to address it with technology.

### 2.2 AI use case purpose
The purpose of the APS Tech Navigator is to act as an interactive technical advisor. It guides APS staff through their specific operational hurdles via iterative dialogue, helps them identify appropriate technology solutions or pathways based on internal OFFICIAL information, and synthesizes the conversation into an actionable draft project brief or a list of recommended technical pathways.

### 2.3 Non-AI alternatives
Traditional search engines or internal knowledge bases were considered. However, they lack the ability to act as an interactive thought partner and do not have the capacity to synthesize complex, unstructured operational problems into actionable project briefs through iterative dialogue.

### 2.4 Identifying stakeholders
* **Primary Users:** APS staff across various roles who encounter operational hurdles but lack the technical expertise to identify solutions.
* **Downstream Stakeholders:** IT and procurement departments who must manage the implementation of the suggested solutions.
* **Indirect Stakeholders:** The broader public, who benefit from a more efficient and capable public service.

### 2.5 Expected benefits
The expected benefits include bridging the gap between operational needs and technological solutions, uplifting technical literacy among APS staff, and generating actionable project briefs. Success will be measured six months post-launch by achieving a 20% positive feedback rate from users and the successful transition of at least one project from a chatbot-generated brief into an actual developed solution.

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
| 3.8 Reputation or public confidence | Moderate | Possible | Medium |

**3.9 Overall inherent risk rating (highest-wins): Medium**

### 3.1 Reducing service accessibility and inclusion

The system features a voice-enabled web interface. If the voice recognition or conversational model fails to accommodate diverse accessibility needs (such as speech impairments, non-standard accents, or screen readers), it will create noticeable access barriers for some APS staff. Applying the precautionary principle, as the outline does not detail specific accessibility compliance (such as WCAG) or fallback mechanisms, we assume a Moderate consequence and a Possible likelihood.

### 3.2 Unfair discrimination

The AI references past project documentation, software catalogs, and internal policy to recommend technical pathways. There is an inherent risk that the AI perpetuates historical biases (e.g., favoring specific dominant vendors, technologies, or teams, while excluding niche or diverse-led solutions). Under the precautionary principle, since bias mitigation and algorithmic fairness strategies are not stated in the outline, we select a Moderate consequence and a Possible likelihood.

### 3.3 Stereotyping or demeaning representations

While the tool is an internal IT advisor, generative conversational models can occasionally output biased, inappropriate, or stereotyped language when interpreting unstructured user inputs or drafting briefs. In the absence of stated guardrails in the outline, we precautionarily default the likelihood to Possible, with a Minor consequence given its internal-only, non-public-facing nature.

### 3.4 Harm

The AI synthesizes complex operational problems into draft project briefs and technical pathways. If the AI hallucinates or recommends non-compliant, insecure, or unfeasible technical solutions, it could cause noticeable financial or operational harm to departments that act on these briefs. Applying the precautionary principle due to the lack of detailed human-in-the-loop validation processes in the outline, we select a Moderate consequence and a Possible likelihood.

### 3.5 Privacy concerns

The chatbot is voice-enabled and accepts unstructured conversational inputs from APS staff describing their daily struggles, which may inadvertently include personal or sensitive operational data. Since the outline does not specify privacy-masking, data-anonymization, or input-filtering protocols, we precautionarily assume a Moderate consequence and a Possible likelihood of privacy concerns.

### 3.6 Security concerns — data aspects

The system ingests and references internal documentation classified up to OFFICIAL. While the outline states that data hosting and processing must occur within Australia, it does not detail the access controls or security architecture protecting this aggregated repository. Precautionarily, we assume a Moderate consequence and a Possible likelihood of data-related security concerns.

### 3.7 Security concerns — system aspects

The use of a web-based, voice-enabled generative AI interface introduces potential system vulnerabilities, such as prompt injection, jailbreaking, or adversarial manipulation of the model's outputs. Because the outline does not specify the technical security architecture, vulnerability testing, or guardrails, we precautionarily select a Moderate consequence and a Possible likelihood.

### 3.8 Reputation or public confidence

If the APS Tech Navigator provides flawed technical recommendations that lead to failed IT projects, or if there is a leak of internal OFFICIAL information, it would attract negative attention and undermine public confidence in the APS's technological capability and governance. Applying the precautionary principle, we select a Moderate consequence and a Possible likelihood.

## 4. Threshold assessment outcome

# Section 4 — Threshold assessment outcome

### 4.1 Assessing officer recommendation
The APS Tech Navigator represents a highly promising application of generative AI to address technical literacy gaps and streamline internal problem-solving within the APS. However, because the system is designed to ingest and reference internal documentation classified up to OFFICIAL and generate technical pathways that influence downstream IT procurement, several inherent risks must be proactively managed.

To ensure safe and responsible implementation, it is recommended that the project team:
1. Establish a strict "human-in-the-loop" validation process, ensuring that all AI-generated project briefs and technical pathways are thoroughly reviewed by qualified IT and procurement professionals before action is taken, and integrate clear disclaimers that outputs are drafts only.
2. Implement robust data-masking, input-filtering protocols, and guardrails around data ingestion to prevent the accidental processing of information above the OFFICIAL classification or sensitive personal data.
3. Conduct comprehensive accessibility testing (aligned with WCAG standards) to ensure the voice and text interfaces are fully inclusive for all APS staff.
4. Define clear security architectures and access controls for the internal document repository, and conduct regular monitoring for prompt injection and model hallucination to maintain the integrity of the advice provided.

A full assessment is **required**.
