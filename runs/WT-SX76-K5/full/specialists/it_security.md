# it_security — owned sections

## 6.7

Yes. The project has established clear human-in-the-loop (HITL) intervention points. According to the use-case outline, all AI-generated outputs—including baseline Software Bills of Materials (SBOMs), architectural maps, and draft compliance attestations—must undergo strict, line-by-line human verification by qualified engineers and auditors before final sign-off. Furthermore, when integrated into the CI/CD pipeline, the tool does not execute automated changes; instead, any detected configuration drift or deviation is flagged as a conflict for manual triage by the Architecture Decision Group. This aligns with cyber security guidance recommending human-in-the-loop intervention points to enhance reliability and safety (AI in OT Principles, p.19) and configuring AI applications to flag risky actions for human approval prior to execution (ISM, p.120). However, a formal protocol for emergency disengagement (such as immediately taking the LLM endpoint offline or disabling the CI/CD integration during an incident) is still being finalized to align with best practices (LLMSVS, V3.3).

*Citations: [AI in OT Principles, p.19], [ISM, p.120], [LLMSVS, V3.3]*

## 7.3

Yes. Several robust measures are in place or planned to address security risks arising from the operation of the AI system. First, the system is designed to operate within a sovereign, air-gapped, or highly secure environment, with the LLM endpoint hosted on sovereign or self-managed infrastructure to protect sensitive legacy source code and configuration files from external exposure. Second, strict access controls and data management processes are applied to limit what data the AI system can access (Secure AI Dev Guidelines, p.12). Third, the system implements human-in-the-loop controls for high-risk operations, ensuring that no automated refactoring or compliance approvals occur without human verification (ISM, p.120; OWASP LLM Top 10, p.9). Finally, robust logging and monitoring will be integrated to track system behavior, inputs, and outputs, enabling the detection of anomalies, data drift, or potential security incidents (Deploying AI Securely, p.8).

*Citations: [Secure AI Dev Guidelines, p.12], [ISM, p.120], [OWASP LLM Top 10, p.9], [Deploying AI Securely, p.8]*
