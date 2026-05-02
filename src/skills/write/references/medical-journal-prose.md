# Medical Journal Prose Reference

Use this reference when writing MAS-controlled English medical original-research manuscripts.

## Runtime Authority

Before full drafting, `artifact.get_paper_contract_health(detail='full')` must show the MAS
medical writing preflight as ready. The subjective style authority is the AI-owned
`medical_prose_review`, read together with `medical_manuscript_blueprint`, claim-evidence,
results narrative, figure semantics, the `medical_journal_style_corpus`, the AI prose review
request bundle, and any `retrospective_medical_prose_audit` replay findings. If the style corpus,
AI review request, or AI prose review is missing, not AI reviewer-owned where applicable, or not
clear, produce a route-back plan instead of a full manuscript draft. When the AI review contains
representative rewrites, use them as the concrete revision target and write that target back into
the paper-facing revision plan.

## Target Voice

Write in a JAMA/NEJM/BMJ/Lancet-style original research voice: neutral, concrete, clinically
framed, and restrained. The manuscript should sound like a medical paper written for clinicians,
statistical reviewers, and editors, not a project progress report.

Style sources: Zeiger's biomedical paper text model, Gopen and Swan's reader-expectation
information flow, JAMA concise/specific/informative wording, Elsevier medical manuscript
audience/relevance/avoid-overstatement guidance, and JAMA Network Open original investigation
examples. The MAS style corpus is the runtime-consumable form of these sources; use it for voice
and rhythm, not as a checklist.

## Reader Flow

- Introduction: move from clinical problem to specific evidence gap to present objective.
- Sentences: use old-to-new information flow so known context appears before the new claim.
- Results: make the clinical finding the grammatical subject, give the quantitative result, then
  cite the figure or table.
- Discussion: state the principal finding, relate it to prior work, interpret clinical meaning,
  name limitations, and close without upgrading the claim.

## Avoid

- Avoid unsupported no-difference or no-association statements. If a comparison is imprecise, report the
  estimate, uncertainty, and boundary rather than saying there was no difference.
- Figure-led or table-led Results prose such as "Figure 1 shows..." when the sentence is meant to
  report the finding.
- Controller, run-log, package, artifact, pipeline, or checklist language in the manuscript body.
- Broad "best", "novel", "first", "unique", or practice-changing language unless the evidence map
  explicitly supports that exact claim.
- Treating regex or pattern hits as the final style verdict. Mechanical checks are safety rails and
  evidence snippets; the AI prose review owns the subjective medical-journal voice judgment.
- Ignoring retrospective audit warnings. NF-PitNET 003, DPCC 003, and DPCC 004 replay findings
  are regression baselines for work-report residue, figure-led Results, and Discussion restraint.
