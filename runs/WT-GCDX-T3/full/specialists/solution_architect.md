# solution_architect — owned sections

## 6.3

Not applicable. The Policy Impact Mapper is currently being developed as an internal Proof of Concept (POC) using a manually curated, frozen document set, and the outline does not indicate that an external AI model or system is being procured. If procurement of a commercial model or third-party system is considered in future phases, a formal suitability assessment will be required to ensure the technology aligns with the agency's specific compliance and operational needs, and that its benefits outweigh the complexity and risks of adoption.

*Citations: [AI Suitability Assessment, §(document start)]*

## 6.4

Yes. The AI system's reliability and safety will be tested using a 'gold standard' set of 10-15 historical changes to calibrate retrieval rules, glossary usage, and confidence thresholds before any live testing occurs. Additionally, the project plan incorporates regression testing against this fixed example set after every iteration to ensure that updates do not degrade performance, which aligns with established responsible AI acceptance testing practices to verify that ethical and operational requirements are met.

*Citations: [RAI Acceptance Testing, §(document start)]*

## 6.5

Yes. The project is currently in a Proof of Concept (POC) stage, which serves as a controlled pilot. During this phase, the system will be restricted to unclassified internal data and a frozen document set to safely evaluate whether the tool can identify a useful proportion of known dependencies and speed up the discovery process compared to manual review before any broader deployment is considered.

## 6.6

Yes. A performance monitoring and evaluation plan has been established. The system will track key metrics, including the ratio of confirmed versus rejected suggestions and the categorization of false positives to continuously refine the retrieval logic. This continuous validation approach is essential for identifying potential drift and ensuring the system's outputs remain accurate and aligned with defined objectives over time.

*Citations: [Continuous RAI Validator, §(document start)], [Agentic AI Addendum, p.7]*

## 6.8

No. Although the threshold assessment strongly recommends implementing mandatory training and clear guidelines to address automation bias and ensure policy officers critically evaluate AI-generated suggestions, the current use-case outline does not state that a formal training process or curriculum has been established yet. To comply with government standards, a structured training program must be developed prior to deployment to ensure operators are sufficiently skilled in interpreting AI outputs and understanding the tool's limitations.

*Citations: [AI Technical Standard, DTA-Tech-Standards!r8]*
