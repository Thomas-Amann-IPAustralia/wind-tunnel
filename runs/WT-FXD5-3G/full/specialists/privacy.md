# privacy — owned sections

## 7.1

Yes. The ATO Deduction Assistant can comply with the Australian Privacy Principles (APPs), provided that robust data minimisation, filtering, and security controls are implemented. Because the chatbot features a free-text interface, there is a risk that taxpayers may input unsolicited personal information, such as Tax File Numbers (TFNs) or sensitive financial details. Under APP 4, any such additional, unrequested information is classified as unsolicited (APP Guidelines, p.108). As an agency, if these inputs are contained in a Commonwealth record, the ATO is not required to destroy or de-identify the personal information under APP 4.3, but must instead deal with it in accordance with APPs 5–13 (APP Guidelines, p.108; APP Guidelines, p.111). To ensure compliance with APP 3 (Collection) and APP 11 (Security), the ATO must adopt a privacy-by-design approach and complete a comprehensive privacy impact assessment (OAIC AI Training Checklist, p.1). This includes implementing real-time data minimisation techniques, such as automated scrubbing or masking of TFNs and other personal identifiers from user prompts before they are processed by the LLM. Furthermore, to satisfy APP 10 (Accuracy) and APP 11, the ATO must ensure that the AI system is appropriate and reliable for its intended uses, understand its limitations, and implement mitigations or safeguards to address the risk of inaccuracy (OAIC AI Selection Checklist, p.1; OAIC AI Training Checklist, p.1). The use of clear disclaimers to signal where AI models require careful consideration is also appropriate to manage user expectations and ensure transparency (OAIC AI Training Top 5, p.1).

*Citations: [APP Guidelines, p.108], [APP Guidelines, p.111], [OAIC AI Training Checklist, p.1], [OAIC AI Selection Checklist, p.1], [OAIC AI Training Top 5, p.1]*

## Gaps

- **7.2**: The specific storage repository or document management system path for the privacy threshold and impact assessments is not specified in the use-case outline, and the checkpoint question was left unanswered.
