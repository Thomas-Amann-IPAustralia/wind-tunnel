# it_security — owned sections

## 6.7

Yes. The agency has established clear processes and administrative mechanisms to safely disengage or intervene in the operation of the conversion utility. Specifically, an administrative interface and 'kill-switch' are planned to allow IT security teams to immediately suspend the service or disable specific parsers if a vulnerability, critical error, or unresolvable issue is detected. Furthermore, standard operating procedures (SOPs) and a cyber security incident response plan will be developed and maintained to guide human intervention, ensuring that roles and responsibilities for managing system anomalies or disengagement are clearly defined and exercised.

*Citations: [AI in OT Principles, p.11], [ISM, p.24], [ISM, p.44]*

## 7.3

Yes. The system implements robust measures to address security risks arising from its operation. To mitigate Server-Side Request Forgery (SSRF) risks associated with fetching external URLs, the deployment environment will implement network-level egress controls, restricting the parser from fetching internal or private IP addresses. This aligns with secure sandboxing techniques that restrict network access to internal services and APIs. Additionally, the system's architecture is designed to be strictly ephemeral, processing all files and URLs in volatile memory and purging them immediately upon completion to prevent persistent data exposure. Strict input validation and sanitisation protocols will also be enforced on all user uploads and URL inputs to protect against malicious file execution and parser exploits.

*Citations: [OWASP LLM Top 10, p.40]*
