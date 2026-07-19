# solution_architect — owned sections

## 6.3

Yes. While the specific model to be procured or utilized (e.g., a commercial LLM or open-source model hosted on business.gov infrastructure) is not finalized in the outline, any procurement will be subject to a formal AI Suitability Assessment. This process pattern ensures that using AI adds clear value over non-AI alternatives (such as static self-help guides) and that the model's capabilities align with the natural language processing requirements of parsing unstructured legal text. Furthermore, in accordance with Statement 20 of the AI Technical Standard, model selection will evaluate trade-offs including data residency, privacy concerns (ensuring uploaded documents are not used for training), and operational assurance.

*Citations: [AI Suitability Assessment, §(document start)], [AI Technical Standard, DTA-Tech-Standards!r73]*

## 6.4

No. The AI system is currently in the conceptual/design phase and has not yet been built or tested. However, a comprehensive testing regime is planned prior to deployment. This will include Responsible AI (RAI) Acceptance Testing to verify that ethical and safety requirements are met, such as testing the accuracy of the legal analysis to prevent incorrect guidance (which could lead to severe legal or financial harm). Additionally, in alignment with Statement 28 of the AI Technical Standard, we will undertake negative testing, failure testing, and fault injection to identify and mitigate security and privacy weaknesses, particularly regarding prompt injection attacks and document parsing vulnerabilities.

*Citations: [RAI Acceptance Testing, §(document start)], [AI Technical Standard, DTA-Tech-Standards!r103]*

## 6.5

Yes. Given the high inherent risk of the C&D Claim Evaluator (particularly the potential for financial and legal harm if users rely on incorrect advice), a structured pilot phase will be conducted before full public deployment. This is consistent with emerging public sector practices where AI deployments are initially trialed as pilots (such as the French Court of Audit's ChatJF prototype) to bridge the gap between development and production, allowing for the refinement of model accuracy, user interface disclaimers, and data handling controls in a restricted environment.

*Citations: [OECD AI in Public Audit, p.25]*

## 6.6

Yes. A comprehensive post-deployment monitoring and evaluation plan will be established. This will incorporate a Continuous RAI Validator pattern to continuously monitor and validate the chatbot's outcomes against safety and reliability requirements (e.g., tracking hallucination rates and accuracy of legal guidance). In accordance with Statement 33 of the AI Technical Standard, the plan will define disaster recovery, backup, and monitoring processes to ensure system resilience.

*Citations: [Continuous RAI Validator, §(document start)], [AI Technical Standard, DTA-Tech-Standards!r114]*

## 6.8

Yes. A formal training and skill-development process will be established for the business.gov operators and legal team members who oversee the system, as confirmed by the project team. This aligns with Statement 10 of the AI Technical Standard, which requires defining human oversight and control mechanisms, including identifying required personas and training them to supervise, monitor, and intervene or override AI decisions when necessary. It also reflects international best practices where public institutions invest heavily in effective training and communication efforts to manage expectations and encourage proper use.

*Citations: [AI Technical Standard, DTA-Tech-Standards!r37], [OECD AI in Public Audit, p.25]*
