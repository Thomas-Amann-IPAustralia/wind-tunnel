# data_governance — owned sections

## 6.1

Yes. The AI system requires the input of unstructured text from cease and desist letters uploaded by users to operate. The chosen data (the uploaded letters) is highly suitable because it represents the direct, real-world legal disputes that small business owners need evaluated. To ensure data suitability and reliability of the AI outputs, the system must align with key data quality principles:

1. **Accuracy and Completeness**: The system must correctly parse the uploaded text (e.g., PDFs or pasted text) to ensure all mandatory fields and legal claims are fully captured without omission (Data Quality Checklist, p.1).
2. **Timeliness**: The legal standards and regulatory frameworks used by the AI to evaluate these claims must be kept up to date to ensure the analysis is relevant to current laws (Data Quality Checklist, p.2).
3. **Data Coverage and Bias**: The training and evaluation data for the underlying model must cover all common legal scenarios, jurisdictions, and language styles that the AI will encounter to avoid biased or lower-quality assessments for diverse business owners (Data Quality Checklist, p.3).
4. **Traceability**: The system must maintain clear lineage to prove which legal guidelines or business.gov reference materials influenced a specific AI output, ensuring the advice is interpretable and verifiable (Data Quality Checklist, p.3).

*Citations: [Data Quality Checklist, p.1], [Data Quality Checklist, p.2], [Data Quality Checklist, p.3]*

## 6.2

Not applicable. The C&D Claim Evaluator is a general-purpose tool designed to analyze unstructured text from cease and desist letters uploaded by small business owners, and does not specifically target, collect, or use Indigenous data as part of its core design. However, if the system processes letters involving Indigenous businesses, communities, or intellectual property, or if any outputs relate to Indigenous people, the agency must ensure consistency with the Framework for Governance of Indigenous Data. This includes partnering with Aboriginal and Torres Strait Islander people to reflect their priorities, building APS capability to support their inclusion in data governance, and embedding co-design in data use and governance activities (DDGS, p.13; AI Use Policy v2.0, p.20).

*Citations: [DDGS, p.13], [AI Use Policy v2.0, p.20]*

## 8.3

Yes. The agency must establish robust processes to maintain appropriate documentation and records throughout the lifecycle of the AI use case, in accordance with National Archives of Australia (NAA) guidance and the Archives Act 1983.

1. **System Development and Governance Records**: The agency must capture and record application design documentation, operational specifications, details of the AI model, rules frameworks, configuration, and training datasets in the system's development records (NAA AI Records Guidance, §Example: AI technologies incorporated into a regulatory compliance assessment business system).
2. **Individual Session and Input Records**: Since the chatbot processes sensitive legal disputes, the AI-generated outputs (the preliminary analysis and recommendations) and associated metadata must be captured into an approved records management system (NAA AI Records Guidance, §Managing AI technologies incorporated into business systems).
3. **Prompts and Inputs**: The agency must make risk-based decisions to retain user prompts and uploaded source documents (inputs) to preserve adequate evidence of how the AI outputs were generated, ensuring transparency and accountability (NAA AI Records Guidance, §Disposal of generative AI assistant prompts and inputs).
4. **Policies and Procedures**: Documentation regarding the correct usage of the AI, system testing, and the disclaimers provided to users must be retained to demonstrate compliant operation (NAA AI Records Guidance, §Example: AI technologies incorporated into a regulatory compliance assessment business system).

*Citations: [NAA AI Records Guidance, §Example: AI technologies incorporated into a regulatory compliance assessment business system], [NAA AI Records Guidance, §Managing AI technologies incorporated into business systems], [NAA AI Records Guidance, §Disposal of generative AI assistant prompts and inputs]*
