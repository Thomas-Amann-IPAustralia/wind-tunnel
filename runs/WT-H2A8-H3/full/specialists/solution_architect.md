# solution_architect — owned sections

## 6.3

Not applicable. The APS Markdown Conversion Service does not procure or utilize an AI model. Instead, it relies entirely on deterministic parsing libraries to transform web and document formats into standardized Markdown. As detailed in the AI Suitability Assessment pattern, a heuristic-based or deterministic approach is often more appropriate than an AI-based system because it is easier and cheaper to develop, and provides better predictability, transparency, and reliability for structured document conversion tasks.

*Citations: [AI Suitability Assessment, §(document start)]*

## 6.8

Not applicable. The APS Markdown Conversion Service is designed as a simple, self-service web utility for public servants across all APS agencies, rather than a system requiring specialized operators. There are no dedicated 'AI system operators' to train. However, to ensure safe and effective use, clear user guidance and warnings against uploading sensitive or classified information will be displayed on the user interface, and feedback is facilitated via a public GitHub repository with automated PII scanning.

*Citations: [OECD AI in Public Audit, p.48], [AI Technical Standard, DTA-Tech-Standards!r37]*

## Gaps

- **6.4**: The outline does not state whether testing of the deterministic parsing libraries or the web interface has been completed or planned.
- **6.5**: The outline does not specify whether a pilot phase is planned before full deployment across the APS.
- **6.6**: The outline does not detail any performance monitoring or evaluation plans for the conversion service.
