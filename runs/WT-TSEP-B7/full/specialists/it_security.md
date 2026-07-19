# it_security — owned sections

## 6.7

No. The current project outline does not indicate that clear processes for human intervention or safely disengaging the AI system have been established yet. To mitigate the high inherent risks of incorrect legal guidance and public confidence damage, the project team must establish these protocols before deployment. Specifically, they should prepare for automated rollbacks and implement a human-in-the-loop failsafe to quickly revert the system to a last known good state if the model is compromised or exhibits anomalous behavior (Deploying AI Securely, p.6). Furthermore, the team should integrate AI-specific failure states—such as model drift or adversarial manipulation—into their existing incident response and business continuity plans, ensuring there is a clear mechanism to bypass or temporarily disable the chatbot without disrupting the broader business.gov portal (AI in OT Principles, p.20).

*Citations: [Deploying AI Securely, p.6], [AI in OT Principles, p.20]*

## 7.3

No. While the project outline specifies that the chatbot will be hosted on business.gov infrastructure and requires strict data privacy controls to prevent uploaded documents from being used for model training, it does not detail comprehensive measures to address operational AI security risks. To secure the system, several critical measures must be implemented. First, the team must address prompt injection vulnerabilities, where malicious inputs in uploaded documents or chat prompts could manipulate the model's behavior, leading to content manipulation or unauthorized access (OWASP LLM Top 10, p.7; ISM, p.171). Second, pre-trained or external models must be thoroughly inspected in a secure development zone using approved scanners before deployment to detect malicious code (Deploying AI Securely, p.6). Finally, the system's operation must be continuously monitored, with logging configured to track AI decisions for compliance and forensic analysis, ensuring the AI's identity is distinct from typical user identifiers (AI in OT Principles, p.19).

*Citations: [OWASP LLM Top 10, p.7], [ISM, p.171], [Deploying AI Securely, p.6], [AI in OT Principles, p.19]*
