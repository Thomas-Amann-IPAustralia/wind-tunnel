# privacy — owned sections

## 7.1

Yes. The ATO Deduction Assistant can comply with the Australian Privacy Principles (APPs), provided that robust data minimisation, filtering, and security controls are implemented. Because the chatbot features a free-text interface, there is a risk that taxpayers may input unsolicited personal information, such as Tax File Numbers (TFNs) or sensitive financial details (Threshold Assessment §3.5). Under APP 4, any such additional, unrequested information is classified as unsolicited (APP Guidelines, p.109). As an agency, these inputs will likely be stored within a 'Commonwealth record' (APP Guidelines, p.20), meaning they are exempt from the automatic destruction or de-identification requirements of APP 4.3 but must still be managed in strict compliance with APPs 5–13 (APP Guidelines, p.108). To ensure compliance with APP 3 (Collection) and APP 11 (Security), the ATO must implement real-time data minimisation techniques, such as automated scrubbing or masking of TFNs and other personal identifiers from user prompts before they are processed by the LLM (OAIC AI Training Checklist, p.2). Furthermore, to satisfy APP 6 (Use and Disclosure) and APP 11, the ATO must ensure that user inputs are strictly isolated, hosted securely (e.g., within a secure cloud environment complying with the ISM), and that terms of use prevent the AI system developer from accessing or using these inputs for model training or secondary purposes (OAIC AI Selection Checklist, p.2).

*Citations: [APP Guidelines, p.109], [APP Guidelines, p.20], [APP Guidelines, p.108], [OAIC AI Training Checklist, p.2], [OAIC AI Selection Checklist, p.2]*

## Gaps

- **7.2**: The specific storage repository or document management system path for the privacy threshold and impact assessments is not specified in the use-case outline.
