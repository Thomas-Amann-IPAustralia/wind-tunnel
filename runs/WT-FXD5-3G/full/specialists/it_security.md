# it_security — owned sections

## 6.7

Yes. The ATO is establishing clear processes for human intervention and safe disengagement of the ATO Deduction Assistant. Because the system is public-facing and advisory, the ATO will implement protocols for immediate intervention, including a kill-switch capability to quickly take the system offline or disable the chat interface on the ATO portal if an unresolvable issue, major hallucination, or security compromise is identified (LLMSVS, §Control objective). Failsafe mechanisms are being integrated into existing incident response and business continuity processes, allowing the system to fail gracefully by reverting to non-AI alternatives, such as a static FAQ wizard or interactive decision tree (AI in OT Principles, p.19). Rollback capabilities will be prepared to ensure that if a model update introduces problems or if the system is compromised, the ATO can quickly revert to the last known good state (Deploying AI Securely, p.6). Furthermore, incident management procedures will be updated to reflect AI-specific failure modes, and responders will be trained to assess and address AI-related incidents (Secure AI Dev Guidelines, p.14). A structured feedback loop with ATO policy teams will also allow stakeholders to flag concerns and trigger manual intervention or model disengagement if necessary.

*Citations: [LLMSVS, §Control objective], [AI in OT Principles, p.19], [Deploying AI Securely, p.6], [Secure AI Dev Guidelines, p.14]*

## 7.3

Yes. Multiple security measures are being established to address the security risks arising from the operation of the public-facing LLM.

To address jurisdictional, governance, privacy, and security risks associated with offshore hosting and foreign legal frameworks, all data—including prompt logs, RAG source documents, and model interactions—will be stored exclusively on Australian soil (ISM, p.31; AI in OT Principles, p.12). This sovereign hosting strategy ensures the ATO maintains complete control over the data, mitigating risks of covert foreign data collection or sudden changes in foreign laws (ISM, p.31; AI in OT Principles, p.12).

To protect the RAG architecture and prevent data leakage, the ATO will implement strict access controls and authentication for external storage components, such as vector databases and caches, enforcing the principle of least privilege (LLMSVS, §Control objective). The system will also implement controls to detect and prevent the leakage of sensitive data from internal knowledge bases, ensuring users cannot coerce the LLM into leaking restricted information (LLMSVS, §Control objective). Furthermore, conversational memory mechanisms will be configured to ensure prior prompts from different users are never mixed (LLMSVS, §Control objective).

To secure data at rest, in transit, and during processing, the ATO will utilize robust encryption protocols, such as AES-256, and store data in certified storage devices (AI Data Security CSI, p.7). The system will be completely isolated from live taxpayer account data to maintain security boundaries. Finally, to ensure the integrity of security monitoring, the ATO will implement robust logging of model behavior and system events, utilizing immutable backup storage systems to ensure that log data cannot be altered or tampered with (Deploying AI Securely, p.9).

*Citations: [ISM, p.31], [AI in OT Principles, p.12], [LLMSVS, §Control objective], [AI Data Security CSI, p.7], [Deploying AI Securely, p.9]*
