# data_governance — owned sections

## 6.1

Yes. The ATO Deduction Assistant uses Retrieval-Augmented Generation (RAG) to ground its responses in official, public tax policy documents. This data is highly suitable because it represents the authoritative source of truth for tax deduction eligibility, ensuring the chatbot's guidance remains aligned with official ATO policy. To ensure suitability and reliability, the system will verify that the reference data covers all expected taxpayer scenarios and groups. Furthermore, the RAG architecture maintains strict traceability (lineage), allowing the system to cite the specific policy document that influenced a given output, which helps explain the basis of the guidance to users. The system is also strictly isolated from live taxpayer account data to prevent security and privacy risks.

*Citations: [Data Quality Checklist, p.3]*

## 6.2

Not applicable. The ATO Deduction Assistant is designed to process public tax policy documents and user-provided financial scenarios to provide general tax deduction guidance. It does not target, collect, or use Indigenous data, nor do its outputs specifically relate to Indigenous people. However, if any future expansion of the system incorporates Indigenous data or impacts Indigenous communities, the ATO will ensure consistency with the Framework for the Governance of Indigenous Data to support Aboriginal and Torres Strait Islander agency over their data and protect Indigenous cultural and intellectual property.

*Citations: [DDGS, p.13], [AI Use Policy v2.0, p.20]*

## 8.3

Yes. The ATO will establish processes to maintain comprehensive documentation and records throughout the lifecycle of the ATO Deduction Assistant, in accordance with National Archives of Australia (NAA) guidance. This includes capturing and retaining the AI system's inputs, source data (the tax policy documents), and system outputs (the chatbot interactions and metadata) in an approved records management system to ensure transparency and accountability. A risk-based decision will be made regarding the retention of user prompts and inputs as supporting evidence to demonstrate how outputs were generated. Additionally, the ATO will document and retain records of the system's design, development, testing, and operational specifications, as well as policies and procedures governing its correct usage.

*Citations: [NAA AI Records Guidance, §Example: AI technologies incorporated into a regulatory compliance assessment business system], [NAA AI Records Guidance, §Managing AI technologies incorporated into business systems], [NAA AI Records Guidance, §Disposal of generative AI assistant prompts and inputs]*
