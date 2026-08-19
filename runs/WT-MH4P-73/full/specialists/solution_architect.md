# solution_architect — owned sections

## 6.3

Not applicable. The current project outline does not specify whether the Agentic Data Synthesis Tool will be procured from a third-party vendor or developed entirely in-house. Furthermore, details regarding the selection of specific AI models or agentic technologies are not yet defined (Agentic AI Addendum, p.25; AI Suitability Assessment, §(document start)). A formal AI suitability assessment should be conducted once procurement or development pathways are clarified to ensure the selected model adds value and aligns with the operational context.

*Citations: [Agentic AI Addendum, p.25], [AI Suitability Assessment, §(document start)]*

## 6.4

No. As the project is currently in the conceptual stage with significant outline placeholders (such as 'Data' and 'Happy path'), no testing has been conducted. Before deployment, the agency must establish a robust testing framework. This must include testing individual agents for robustness against unexpected inputs, evaluating agent-tool, agent-environment, and agent-memory interactions (Agentic AI Addendum, p.27-28), and conducting Responsible AI (RAI) acceptance testing to verify that ethical and safety requirements are met (RAI Acceptance Testing, §(document start)). System-level simulation should also be considered to assess behaviors and prevent unintended consequences before real-world deployment (System-Level RAI Simulation, §(document start)).

*Citations: [Agentic AI Addendum, p.27-28], [RAI Acceptance Testing, §(document start)], [System-Level RAI Simulation, §(document start)]*

## 6.6

No. The current outline does not specify a monitoring plan. To ensure reliability and safety, a comprehensive monitoring plan must be established prior to deployment. In accordance with agentic AI standards, this plan must continuously monitor individual agents and their environment, tracking goal drift, tool usage, memory management, and inter-agent conflicts (Agentic AI Addendum, p.31). Additionally, the agency should implement a centralized 'control tower' for system oversight (Agentic AI Addendum, p.31) and deploy a continuous RAI validator to monitor and validate agent outcomes against ethical and safety requirements at runtime (Continuous RAI Validator, §(document start)).

*Citations: [Agentic AI Addendum, p.31], [Continuous RAI Validator, §(document start)]*

## 6.8

No. The outline identifies policy analysts and data officers as primary users, but does not specify any training process or capability-building program. To comply with government standards, the agency must establish regular training programs to keep staff updated on the latest tools, methodologies, ethical guidelines, and regulatory requirements (AI Technical Standard, DTA-Tech-Standards!r8). This should include specialized AI ethics training tailored to their roles, and could leverage interactive workshops, simulations, or computing sandpit environments to provide hands-on experience with complex agentic workflows (AI Technical Standard, DTA-Tech-Standards!r8).

*Citations: [AI Technical Standard, DTA-Tech-Standards!r8]*

## Gaps

- **6.5**: The outline does not state whether a pilot is planned or has been conducted for this use case.
