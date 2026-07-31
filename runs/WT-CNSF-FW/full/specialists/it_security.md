# it_security — owned sections

## 6.7

No. The current project outline does not indicate that processes for human intervention or safe disengagement have been established. To ensure reliability and safety, the department should implement human-in-the-loop controls and rollback capabilities. Specifically, the AI system should be configured to flag risky actions or sensitive relationship extractions for human approval prior to execution (ISM, p.120; OWASP LLM Top 10, p.9). Furthermore, the department should prepare for automated rollbacks and human-in-the-loop failsafes to quickly revert the system to a last known good state if the model introduces errors or is compromised (Deploying AI Securely, p.6). Finally, new failure states and procedures for bypassing or disengaging the AI system must be integrated into the department's existing incident response and business continuity plans (AI in OT Principles, p.20).

*Citations: [ISM, p.120], [OWASP LLM Top 10, p.9], [Deploying AI Securely, p.6], [AI in OT Principles, p.20]*

## 7.3

No. The current project outline does not specify the operational security measures in place for the AI system. To address security risks arising from the operation of the AI, the following measures should be implemented: 
1. **Data Sanitization and Anomaly Detection:** Since the system ingests highly sensitive unstructured data (such as email archives), the department should apply data sanitization (filtering, normalization) and anomaly detection algorithms during pre-processing to identify and remove poisoned or malicious inputs before they affect the knowledge graph (AI Data Security CSI, p.14).
2. **Access Control and Least Privilege:** Apply strict least privilege principles to limit the AI system's access to data repositories and restrict user access to the system's output based on existing security classifications (Secure AI Dev Guidelines, p.10; OWASP LLM Top 10, p.9).
3. **Continuous Monitoring and Logging:** Implement continuous monitoring of model behavior and configure comprehensive logging of all AI decisions, inputs, and outputs to track anomalies and support incident response (Deploying AI Securely, p.6; AI in OT Principles, p.19).
4. **Supply Chain and Asset Security:** Store all code, configurations, and model artifacts in a secure version control system, and thoroughly inspect any imported pre-trained models in a secure development zone prior to deployment (Deploying AI Securely, p.6).

*Citations: [AI Data Security CSI, p.14], [Secure AI Dev Guidelines, p.10], [OWASP LLM Top 10, p.9], [Deploying AI Securely, p.6], [AI in OT Principles, p.19]*
