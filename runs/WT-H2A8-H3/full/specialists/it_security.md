# it_security — owned sections

## 6.7

No. Currently, there are no documented processes or administrative mechanisms (such as a 'kill-switch' or service suspension protocol) to safely disengage or intervene in the operation of the conversion utility if stakeholders raise valid concerns or if an unresolvable security issue is identified. While the tool is designed as a stateless, ephemeral utility with low operational risk, integrating a clear disengagement and bypass procedure into the agency's incident response plan is necessary to manage potential system failures or exploits gracefully.

*Citations: [AI in OT Principles, p.20], [ISM, p.24]*

## 7.3

No. While the system implements architectural mitigations such as stateless, ephemeral processing in volatile memory and strict data isolation, it lacks specific operational security measures to address risks arising from its operation. Specifically, because the service fetches external URLs and parses user-uploaded files, it is highly vulnerable to Server-Side Request Forgery (SSRF), malicious file uploads, and parser exploits. Robust input validation and sanitisation protocols and secure API controls have not yet been fully established.

*Citations: [ISM, p.165], [ISM, p.231], [Deploying AI Securely, p.7]*
