# ethics — owned sections

## 5.1

No. The project does not currently have a formally documented definition of what constitutes a fair process or outcome. Because the system is a deterministic parser rather than a decision-making AI, traditional algorithmic fairness definitions (such as group fairness or predictive parity) do not apply. However, in this context, fairness must be defined in terms of accessibility and inclusion—specifically, ensuring that the parser does not strip critical accessibility features (such as alt text or semantic headers) and that the output Markdown is compatible with screen readers used by diverse public servants, in line with Australia's AI Ethics Principles and inclusive design obligations.

*Citations: [AI Ethics Principles, §AI Ethics Principles at a glance], [VAISS, s 10]*

## 5.2

No. There is currently no structured mechanism to quantitatively or qualitatively measure the fairness or accessibility of the system's outputs. While a general feedback mechanism is planned via a public GitHub repository to report parsing issues, the project lacks a systematic validation process or audit toolkit to evaluate whether the parser consistently preserves accessibility features across different document formats or if it disproportionately degrades content relied upon by users with diverse needs.

*Citations: [VAISS, s 10], [NAIC RAI Tools, p.20]*

## 8.1

No. While the primary users (public servants across all APS agencies) and key stakeholders (agency IT security teams) have been identified, the project documentation does not indicate that formal consultation has yet taken place. To align with responsible AI practices, structured engagement should be conducted with both IT security teams (to vet cross-departmental data handling) and representative end-users (including those with accessibility requirements) to evaluate their needs and identify potential operational harms.

*Citations: [VAISS, s 10]*

## 8.2

Yes. Appropriate information regarding the system's scope, goals, and technical implementation will be made publicly available. The project's development and issue-tracking are hosted on a public GitHub repository, and the source code will be open to outside inspection. This open-source approach provides high public visibility, allows external scrutiny of the deterministic parsing rules, and helps build trust across participating agencies.

*Citations: [ADM Guide (earlier ed.), p.25], [Diversity & Inclusion in AI, p.14]*

## 8.4

Yes. (8.4.1) Users will be inherently informed when they interact with the system, as the tool is a dedicated, user-initiated web utility where public servants must actively paste a URL or upload a file to receive a Markdown output. To ensure complete transparency, the user interface should display a clear disclosure explaining that the tool uses deterministic parsing libraries and explicitly avoids LLM-based processing, thereby setting accurate expectations regarding its capabilities and limitations. (8.4.2) This tool is an internal utility for public servants rather than a public-facing service interacting with the general public, making a public-facing non-AI alternative not applicable. However, for public servants, traditional non-automated alternatives (such as manual re-typing or using standard desktop software like Pandoc) remain fully available.

*Citations: [VAISS, s 10], [NAIC RAI Tools, p.33]*

## 8.5

Not applicable. The system is a deterministic parser that performs direct, rule-based document conversion and does not generate decisions, recommendations, or insights. Consequently, there are no underlying decision-making factors, weights, or statistical models to explain. However, because the source code is publicly available on GitHub, the exact rules governing the conversion process are fully transparent and explainable to technical stakeholders.

*Citations: [ADM Guide (earlier ed.), p.30], [NAIC RAI Tools, p.33]*

## 10.1

No. Based on the current project outline, it is not yet clear if diversity has been incorporated into the project lifecycle. The documentation does not specify the composition of the design and development team. To safeguard against unintentional accessibility barriers and ensure compliance with public sector standards, the project should establish a multidisciplinary team that includes user experience designers, accessibility specialists, and policy/legal professionals alongside technical developers.

*Citations: [ADM Better Practice Guide, p.29], [Diversity & Inclusion in AI, p.16]*
