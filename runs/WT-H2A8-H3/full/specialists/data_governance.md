# data_governance — owned sections

## 6.1

Yes. The system does not train or evaluate an AI model, as it relies entirely on deterministic parsing libraries rather than machine learning or LLMs (Outline §1.4). However, for operation, it accepts user-provided URLs or uploaded files. This input data is suitable because it is directly selected by the public servant user who requires the conversion. Since the system is strictly ephemeral and processes data in volatile memory, purging it immediately upon completion, there is no persistent storage or reuse of this data (Outline §4). Data suitability and coverage are therefore determined dynamically by the user's immediate conversion needs, though users should verify that the input files are compatible with the parser to ensure accurate outputs.

## 6.2

Not applicable. The APS Markdown Conversion Service is a general-purpose, ephemeral utility that does not target, collect, or persistently store Indigenous data. It processes user-provided documents in volatile memory and purges them immediately upon completion (Outline §4). It does not maintain any data repositories or datasets. Therefore, the Framework for Governance of Indigenous Data is not directly applicable to the tool's core operations. However, if individual agencies use the tool to process documents containing Indigenous data, those agencies remain responsible for ensuring their broader data handling practices align with the Framework and Closing the Gap Priority Reforms (DDGS, p.13).

*Citations: [DDGS, p.13]*

## 8.3

No. While the system's operational data is strictly ephemeral and is purged immediately from volatile memory (Outline §4), the project outline does not yet specify processes for maintaining administrative, development, and system governance records. Under the Archives Act 1983 and National Archives of Australia (NAA) guidance, agencies must capture and retain records supporting the development, implementation, and governance of systems (including deterministic parsers evaluated under AI frameworks) (NAA AI Records Guidance, §More information on the use of AI in Australian Government). These records—such as system design specifications, testing logs, and configuration rules—should be captured in an approved records management system and managed under AFDA Express (NAA AI Records Guidance, §Example: AI technologies incorporated into a regulatory compliance assessment business system). A formal process must be established to document the system's lifecycle compliance.

*Citations: [NAA AI Records Guidance, §More information on the use of AI in Australian Government], [NAA AI Records Guidance, §Example: AI technologies incorporated into a regulatory compliance assessment business system]*
