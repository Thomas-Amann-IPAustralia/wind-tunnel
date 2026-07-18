# privacy — owned sections

## 7.1

Yes. The core architecture of the APS Markdown Conversion Service is designed to be strictly ephemeral, processing documents and URLs in volatile memory and purging them immediately upon completion. This 'privacy by design' approach aligns with APP 11 (security of personal information) by ensuring there is no persistent storage of user-uploaded files or converted outputs, thereby minimizing the risk of unauthorized access, loss, or disclosure (APP Guidelines, p.188; OAIC AI Selection Checklist, p.2). However, full compliance with APP 3 (collection) and APP 6 (disclosure) depends on the feedback mechanism. The proposed public GitHub repository feedback channel introduces a risk of accidental disclosure of personal information. While a 250-character limit and automated PII scanning are planned, these controls must be rigorously tested, regularly audited, and accompanied by clear, prominent user warnings to ensure that no personal information is collected or disclosed via this channel (OAIC AI Selection Checklist, p.2; OAIC AI Training Checklist, p.1).

*Citations: [APP Guidelines, p.188], [OAIC AI Selection Checklist, p.2], [OAIC AI Training Checklist, p.1]*

## 7.2

No privacy threshold assessment or privacy impact assessment has been documented or stored for the APS Markdown Conversion Service, as no such documentation is provided in the use-case outline or threshold assessment.
