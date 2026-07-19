# privacy — owned sections

## 7.1

Yes. The ATO Deduction Assistant can comply with the Australian Privacy Principles (APPs), provided that robust data minimisation, filtering, and security controls are implemented. Crucially, all user interaction logs and processed data will be stored strictly on Australian soil. This onshore data storage commitment is a key privacy control that supports compliance with APP 8 by ensuring that no personal information is disclosed to overseas recipients (APP Guidelines, p.122; OAIC PIA Tool, §APP 8 — Cross-border disclosure of personal information). Because the chatbot features a free-text interface, there is a risk that taxpayers may input unsolicited personal information, such as Tax File Numbers (TFNs) or sensitive financial details. To ensure compliance with APP 11, the ATO must implement robust access security and monitoring controls to protect against internal and external risks, ensuring that personal information is only accessed by authorised persons on a strict need-to-know basis (OAIC PIA Tool, §APP 11 — Security of personal information). This includes implementing real-time data minimisation techniques, such as automated scrubbing or masking of TFNs and other personal identifiers from user prompts before they are processed by the LLM. Furthermore, if any personal information is shared with third-party service providers, enforceable contractual arrangements must be put in place to protect the information and monitor compliance with APP 6 (OAIC PIA Tool, §APP 6 — Use or disclosure of personal information).

*Citations: [APP Guidelines, p.122], [OAIC PIA Tool, §APP 8 — Cross-border disclosure of personal information], [OAIC PIA Tool, §APP 11 — Security of personal information], [OAIC PIA Tool, §APP 6 — Use or disclosure of personal information]*

## Gaps

- **7.2**: The specific storage repository or document management system path for the privacy threshold and impact assessments is not specified in the use-case outline, and the checkpoint question was left unanswered.
