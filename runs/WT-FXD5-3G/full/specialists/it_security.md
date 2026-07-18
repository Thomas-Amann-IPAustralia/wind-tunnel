# it_security — owned sections

## 6.7

Yes. The ATO is establishing clear processes for human intervention and safe disengagement of the ATO Deduction Assistant. Because the system is public-facing and advisory, the ATO will implement a kill-switch capability to immediately disconnect all inbound connections to the AI model or disable the chat interface on the ATO portal if an unresolvable issue, major hallucination, or security compromise is identified (Deploying AI Securely, p.5). Failsafe mechanisms are being integrated into existing incident response and business continuity processes, allowing the system to fail gracefully by reverting to non-AI alternatives, such as a static FAQ wizard or interactive decision tree (AI in OT Principles, p.20). Furthermore, incident management procedures will be updated to reflect AI-specific failure modes, and responders will be trained to assess and remediate AI-related incidents (Secure AI Dev Guidelines, p.14). A structured feedback loop with ATO policy teams will also allow stakeholders to flag concerns and trigger manual intervention or model disengagement if necessary.

*Citations: [Deploying AI Securely, p.5], [AI in OT Principles, p.20], [Secure AI Dev Guidelines, p.14]*

## 7.3

Yes. Multiple security measures are being established to address the unique security risks arising from the operation of the public-facing LLM. To mitigate prompt injection and jailbreaking vulnerabilities—where malicious user prompts force the model to bypass safety guidelines or generate harmful content (OWASP LLM Top 10, p.7; ISM, p.171)—the ATO will implement robust input sanitization and output guardrails (Secure AI Dev Guidelines, p.10). The 'creativity' dial's parameters will be strictly bounded to prevent unpredictable outputs, and the system will be completely isolated from live taxpayer account data to maintain security boundaries. To detect and analyze security incidents, the ATO will configure comprehensive logging of all user interactions and model decisions (AI in OT Principles, p.19). These logs will be treated as sensitive data with strict access controls to protect user privacy (Secure AI Dev Guidelines, p.12). Finally, the ATO will conduct regular offensive security assessments, including AI red-teaming and penetration testing, to evaluate the system's resilience before and during active deployment (AI in OT Principles, p.19).

*Citations: [OWASP LLM Top 10, p.7], [ISM, p.171], [Secure AI Dev Guidelines, p.10], [AI in OT Principles, p.19], [Secure AI Dev Guidelines, p.12]*
