# NSAF Technical Guide Preferences

Preferences for generating technical-guide topic ideas (consumed by the techguide pipeline).

A techguide is a self-contained piece of web content published to seanmahoney.ai/guides.
Per-idea, the model picks one of three variants:
- **deep** — a multi-section deep-dive HTML guide
- **comparison** — a head-to-head product/technology comparison with a feature matrix
- **explainer** — a single-page deep explanation of one concept

The variant is chosen per idea based on the topic; do not bias the mix here.

## Subject Domains
- enterprise networking — routing, switching, SD-WAN, SASE, SSE, segmentation
- network operations and automation (Ansible, Terraform, NetBox, Python netdev)
- cloud platforms — services and reference architectures (AWS, Azure, GCP)
- container platforms — Kubernetes, service mesh, ingress, CNI
- security tooling and product categories (EDR, NDR, ZTNA, CASB, SIEM, SOAR)
- observability and SRE tooling (Prometheus, OTel, Grafana, log pipelines)
- developer tooling and language runtimes
- AI infrastructure and LLM application patterns
- vendor product spotlights for the above

## Levels
- Min: intro
- Max: advanced

## Source Material Tendency
- prefer topics with authoritative public source documents (RFCs, vendor whitepapers, official docs, well-maintained reference architectures)
- product comparisons should ground in publicly available datasheets / docs
- single-concept explainers can stand alone without a source URL

## Length Hints
- deep: 5 to 12 sections, 2 to 3 inline SVG/Mermaid diagrams per section
- comparison: feature matrix + 3 to 5 per-product writeups
- explainer: single page, 3 to 5 concept blocks, SVG-heavy

## Exclusions
- topics already covered as a study-guide track (no duplication with SWS)
- certification exam prep tracks (those belong in SWS)
- pure marketing fluff with no technical substance
- topics that age out within 6 months (release-note-style posts)
- consumer-grade tech reviews

## Tone
- technical, precise, opinion only when grounded in tradeoffs
- comparative-but-fair for product comparisons — name strengths AND weaknesses
- show why this matters for a working engineer or operator

## Model Profile
balanced

## On-Demand Quota
5
