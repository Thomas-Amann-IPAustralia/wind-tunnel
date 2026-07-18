# Appendix — Implementation Plan

The implementation of the APS Markdown Conversion Service follows a phased approach, prioritizing security, accessibility, and strict data ephemerality. The architecture centers on a stateless, containerized web application that processes inputs entirely in volatile memory. Network egress controls and strict input validation form the primary defense against Server-Side Request Forgery (SSRF) and malicious payloads. Sequencing begins with establishing a multidisciplinary team and consulting stakeholders, followed by core development of the ephemeral parser and security controls. The system will then undergo rigorous acceptance testing and a limited pilot phase before full cross-agency deployment, supported by real-time monitoring and an administrative kill-switch.

## Implementation steps

### 1. Establish Governance and Multidisciplinary Team

Appoint an Accountable Official and Accountable Use Case Owner. Form a multidisciplinary project team comprising UX designers, accessibility specialists, policy/legal professionals, and technical developers. Establish an automated pipeline to export lifecycle records (administrative, development, and governance) from GitHub into the agency's approved records management system (e.g., AFDA Express Version 2) to ensure compliance with the Archives Act.

*Answers: [Legal & Administrative Law specialist, §11.1] — Designate an Accountable Official and Accountable Use Case Owner.; [Ethics & Fairness specialist, §10.1] — Establish a multidisciplinary team including UX, accessibility, and policy/legal professionals.; [Data Governance specialist, §8.3] — Establish a formal process to export and capture lifecycle records from GitHub into an approved records management system.*

### 2. Conduct Stakeholder Consultation and Define Accessibility Standards

Engage IT security teams to vet cross-departmental data handling and consult representative end-users, including those using assistive technologies. Define fairness explicitly around accessibility: configure the deterministic parsers to preserve alt text and semantic headers. Conduct formal accessibility and human rights reviews to ensure outputs comply with the Disability Discrimination Act 1992 (Cth).

*Answers: [Ethics & Fairness specialist, §8.1] — Conduct structured engagement with IT security teams and representative end-users during design and testing.; [Ethics & Fairness specialist, §5.1] — Define fairness in terms of accessibility, ensuring parsers do not strip critical features like alt text or semantic headers.; [Legal & Administrative Law specialist, §10.2] — Conduct accessibility and human rights reviews to ensure compliance with obligations such as the Disability Discrimination Act.*

### 3. Implement Ephemeral Architecture and Egress Controls

Deploy the application using containerized environments configured with `tmpfs` mounts to ensure all document processing occurs strictly in volatile memory, with immediate purging post-conversion. To prevent SSRF, implement strict network-level egress controls blocking the parser from accessing internal or private IP ranges.

```yaml
# Example Kubernetes NetworkPolicy snippet for egress control
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-internal-egress
spec:
  podSelector:
    matchLabels:
      app: markdown-parser
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
        - 10.0.0.0/8
        - 172.16.0.0/12
        - 192.168.0.0/16
        - 169.254.169.254/32
```

*Answers: [IT Security specialist, §7.3] — Implement network-level egress controls to restrict fetching internal/private IPs and process files in volatile memory.; [Privacy specialist, §7.1] — Process documents in volatile memory and purge immediately to ensure no persistent storage.*

### 4. Enforce Input Validation and UI Disclosures

Implement strict input validation and sanitisation on all URL and file uploads to prevent malicious execution. On the user interface, display a clear disclosure that the tool uses deterministic parsing (avoiding LLMs entirely). Add prominent warnings instructing users not to upload sensitive or classified information, and advise them to ensure input files are accurate and complete for reliable parsing.

*Answers: [IT Security specialist, §7.3] — Enforce strict input validation and sanitisation protocols on user uploads and URLs.; [Ethics & Fairness specialist, §8.4] — Display a clear UI disclosure explaining the use of deterministic parsing and the avoidance of LLM processing.; [Solution Architect (sections), §6.8] — Display clear user guidance and warnings against uploading sensitive or classified information.; [Data Governance specialist, §6.1] — Provide user guidance to ensure input files are accurate, complete, and conform to expected formats.*

### 5. Configure GitHub Feedback Safeguards and Open Source Release

Release the source code to a public GitHub repository to allow external scrutiny. Configure the issue tracker to enforce a 250-character limit on feedback submissions. Deploy and rigorously test an automated GitHub Action to scan for and redact PII in incoming issues. Schedule regular audits of this feedback channel to ensure no personal information is inadvertently collected or disclosed.

*Answers: [Ethics & Fairness specialist, §8.2] — Make the source code publicly available on GitHub for external inspection and transparency.; [Privacy specialist, §7.1] — Rigorously test and audit the GitHub feedback mechanism, including the 250-character limit and automated PII scanning.*

### 6. Develop Admin Kill-Switch and Incident Response Plan

Build an administrative interface featuring a 'kill-switch' that allows IT security teams to immediately suspend the entire service or disable specific parsing libraries if a vulnerability is detected. Draft Standard Operating Procedures (SOPs) and a cyber security incident response plan detailing roles and responsibilities for system disengagement.

*Answers: [IT Security specialist, §6.7] — Implement an administrative interface and 'kill-switch', and develop SOPs and an incident response plan.*

### 7. Conduct Acceptance Testing and Accessibility Auditing

Develop an audit toolkit to quantitatively and qualitatively measure the accessibility of the Markdown outputs. Before deployment, conduct comprehensive acceptance testing covering security (SSRF, malicious uploads), reliability (formatting corruption), and accessibility to verify system requirements and detect design flaws.

*Answers: [Ethics & Fairness specialist, §5.2] — Implement a structured mechanism/audit toolkit to measure the fairness and accessibility of outputs.; [Solution Architect (sections), §6.4] — Conduct acceptance testing (security, reliability, accessibility) to detect flaws before deployment.*

### 8. Deploy Pilot and Implement Real-Time Monitoring

Roll out the conversion service to a limited pilot group of APS users to identify undetected parsing errors or usability issues. Concurrently, deploy robust monitoring tools and automated alerting to track system performance, error rates, and security events in real-time. Proceed to full cross-agency deployment only after pilot success criteria are met.

*Answers: [Solution Architect (sections), §6.5] — Conduct a pilot with a limited group of APS users before full deployment.; [Solution Architect (sections), §6.6] — Implement robust monitoring tools and automated alerting to track system performance, error rates, and security events.*
