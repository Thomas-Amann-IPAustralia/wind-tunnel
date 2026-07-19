# privacy — owned sections

## 7.1

No. The current project outline does not specify whether the structured data ingested from SQL databases and CSVs contains personal or sensitive information. If personal or sensitive information is processed, we cannot be satisfied of compliance with the Australian Privacy Principles (APPs) at this stage. To ensure compliance, the project must verify if personal information is collected or used (APP 3), ensure data minimisation techniques are integrated, and confirm that any secondary use of personal information for training or calibrating the bi-encoder and cross-encoder gates complies with APP 6 or has valid consent (OAIC AI Training Checklist, p.2; OAIC AI Training Top 5, p.1). Furthermore, robust security measures must be implemented under APP 11 to protect any personal information stored in logs or SQLite databases from unauthorised access or corruption (OAIC AI Selection Checklist, p.2).

*Citations: [OAIC AI Training Checklist, p.2], [OAIC AI Training Top 5, p.1], [OAIC AI Selection Checklist, p.2]*

## Gaps

- **7.2**: The project outline does not state where the privacy threshold assessment or privacy impact assessment is stored.
