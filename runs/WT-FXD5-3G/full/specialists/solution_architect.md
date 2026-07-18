# solution_architect — owned sections

## 6.3

Yes. While the specific LLM model to be procured is not yet finalized, the ATO is conducting an AI Suitability Assessment to evaluate the appropriateness of using a generative AI model for this use case. This assessment ensures that the RAG-based LLM adds genuine value and is more suitable than non-AI alternatives (such as interactive decision trees or static FAQ wizards) which fail to capture the nuance of unique taxpayer scenarios.

*Citations: [AI Suitability Assessment, §(document start)]*

## 6.4

No. The AI system has not yet been tested sufficiently as it is currently in the design and assessment phase. However, a comprehensive testing plan is being established. This plan will include robust adversarial testing (red team testing) to identify weaknesses in security and privacy measures, specifically targeting risks like prompt injection, jailbreaking, and input attacks. Additionally, the system will undergo continuous validation of outcomes against responsible AI requirements to ensure reliability and safety before and during deployment.

*Citations: [AI Technical Standard, DTA-Tech-Standards!r105], [Continuous RAI Validator, §(document start)]*

## 6.5

Yes. Although the project outline does not explicitly detail the pilot phase, a pilot is planned (and highly recommended as part of the precautionary implementation strategy) before full public deployment. Conducting a pilot is a recognized good practice to bridge the gap between design and production, allowing the ATO to test the RAG pipeline, evaluate the 'creativity' dial's impact in a controlled environment, and gather initial user feedback without exposing the broader public to potential system fallibilities.

*Citations: [OECD AI in Public Audit, p.9]*

## 6.6

Yes. The ATO is establishing a comprehensive plan to monitor and evaluate the performance of the AI system post-deployment. This plan will leverage a continuous monitoring framework, such as a Continuous RAI Validator, to track model drift, data quality, and close-domain hallucinations. Furthermore, monitoring will track individual agent behaviors, prompt performance, token usage, latency, and potential security exploits (such as injection attacks or unauthorized use) to ensure the system operates strictly within its designated advisory boundaries.

*Citations: [Continuous RAI Validator, §(document start)], [Agentic AI Addendum, p.31]*

## 6.8

Yes. The ATO will establish a structured process to ensure that operators, support staff, and stakeholders of the AI system are sufficiently skilled and trained. In alignment with government standards, the ATO will provide regular training programs covering the latest tools, methodologies, and ethical guidelines. This training will be tailored to specific roles, ensuring that individuals responsible for managing, operating, and overseeing the AI system undergo specialized AI ethics training, potentially utilizing interactive workshops or sandpit environments for hands-on experience.

*Citations: [AI Technical Standard, DTA-Tech-Standards!r8]*
