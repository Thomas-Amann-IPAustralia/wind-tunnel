# privacy — owned sections

## 7.1

Yes, subject to the implementation of recommended safeguards. The Legacy Code Modernization Assistant is designed to analyze legacy source code, configuration files, and technical documentation, which are not intended to contain personal information. However, as noted in the threshold assessment (Section 3.5), legacy repositories may contain hardcoded credentials, API keys, or legacy test data containing personal information. To ensure compliance with APP 3 (collection of solicited personal information) and APP 11 (security of personal information), the agency must implement pre-ingestion scanning and sanitisation tools to identify and strip any personal information or sensitive data before it is processed by the LLM. Furthermore, hosting the LLM endpoint on sovereign, self-managed, or air-gapped infrastructure (as preferred in the outline) aligns with APP 11 obligations to protect personal information from unauthorised access or disclosure (APP Guidelines, p.188; OAIC AI Selection Checklist, p.2).

*Citations: [APP Guidelines, p.188], [OAIC AI Selection Checklist, p.2]*

## 7.2

The completed privacy threshold assessment for the Legacy Code Modernization Assistant (Run ID: WT-SX76-K5) is stored in the agency's secure Document Management System (DMS) under record reference [insert reference, e.g., DMS-2026-WT-SX76-K5]. Because the threshold assessment has computed an overall inherent risk rating of High, a full Privacy Impact Assessment (PIA) is required in accordance with OAIC guidelines (OAIC PIA Guide, p.8). Once the full PIA is completed, it will be registered and stored in the same secure DMS folder alongside this threshold assessment to maintain a complete compliance trail.

*Citations: [OAIC PIA Guide, p.8]*
