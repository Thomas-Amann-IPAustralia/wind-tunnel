# it_security — owned sections

## 6.7

No. While the system is designed with a human-in-the-loop pattern where managers must review, edit, and approve all AI-generated performance summaries before finalization, formal processes for human intervention or safely disengaging the AI system have not yet been fully established. To ensure reliability and safety, the project must establish clear protocols for managers or administrators to intervene, report anomalies, or bypass/disengage the AI system if unresolvable issues or stakeholder concerns arise. Implementing these processes aligns with best practices for maintaining human-in-the-loop oversight as a failsafe to boost reliability and correct anomalies.

*Citations: [Deploying AI Securely, p.6], [AI in OT Principles, p.19]*

## 7.3

No. As the project is currently in the conceptual phase, specific security measures to address risks arising from the operation of the AI have not yet been fully implemented. However, the threshold assessment identifies key security concerns, including insecure local data caching on mobile devices, API exploits, and unauthorized access. To address these risks during development and deployment, the project will need to implement robust security controls. These should include strict access controls, secure API configurations, continuous monitoring of model behavior, and protecting sensitive assets such as feedback logs and model inputs.

*Citations: [Secure AI Dev Guidelines, p.12], [Deploying AI Securely, p.6]*
