from datetime import date


def build_prompt(order) -> str:
    """Build the plain-text LLM prompt from an Order and its linked records.

    The prompt uses only fields currently stored on Order/Patient/Provider and
    asks the model to show placeholders instead of inventing missing facts.
    """
    today = date.today().isoformat()

    return f"""
You are generating a pharmacist-review draft care plan for a specialty pharmacy workflow.
This is NOT final medical advice. The output will be reviewed by a licensed pharmacist before use.

Use ONLY the provided order, patient, and provider information. Do not invent or assume missing clinical facts.
If a field is unavailable, use an explicit placeholder such as [NOT PROVIDED].

Available information:
- Generated date: {today}
- Patient name: {order.patient.name or "[NOT PROVIDED]"}
- Patient MRN: {order.patient.mrn or "[NOT PROVIDED]"}
- Medication: {order.medication or "[NOT PROVIDED]"}
- Referring provider: {order.provider.name or "[NOT PROVIDED]"}
- Referring provider NPI: {order.provider.npi or "[NOT PROVIDED]"}
- Diagnosis: {order.diagnosis or "[NOT PROVIDED]"}
- Clinical notes: {order.clinical_notes or "[NOT PROVIDED]"}

Missing information rules:
- If weight is needed, write [WEIGHT NOT PROVIDED].
- If medication history/current medications are needed, write [CURRENT MEDICATION LIST NOT PROVIDED].
- If allergies are needed, write [ALLERGIES NOT PROVIDED].
- If provider fax is needed, write [PROVIDER FAX NOT PROVIDED].
- If lab values are needed but not present in clinical notes, write [LAB VALUES NOT PROVIDED].
- If pharmacist license is needed, write [LICENSE NUMBER].
- Do not fabricate patient phone number, insurance details, provider fax, lab results, dates beyond the generated date, allergies, medication history, or weight.

Output requirements:
- Plain text only.
- No Markdown code fences.
- No JSON.
- No extra explanation before or after the care plan.
- Use the exact section headers and separator lines shown below.
- Keep recommendations general and tied to the provided diagnosis, medication, and clinical notes.

SPECIALTY PHARMACY CARE PLAN
Generated: {today}
Patient: {order.patient.name or "[NOT PROVIDED]"} (MRN: {order.patient.mrn or "[NOT PROVIDED]"})
Medication: {order.medication or "[NOT PROVIDED]"}
Referring Provider: {order.provider.name or "[NOT PROVIDED]"} (NPI: {order.provider.npi or "[NOT PROVIDED]"})

================================================================================
PROBLEM LIST / DRUG THERAPY PROBLEMS (DTPs)
================================================================================
[numbered list based only on the provided diagnosis, medication, and clinical notes]

================================================================================
GOALS (SMART)
================================================================================
PRIMARY GOAL:
[primary measurable therapy goal based on the provided diagnosis and medication]

SAFETY GOALS:
- [safety goal]
- [safety goal]

PROCESS GOALS:
- [process goal]
- [process goal]

================================================================================
PHARMACIST INTERVENTIONS / PLAN
================================================================================

1. DOSING & ADMINISTRATION
   - [recommend pharmacist verification of dose, route, frequency, and appropriateness]
   - If weight is required for dosing, state [WEIGHT NOT PROVIDED].

2. PREMEDICATION / ADMINISTRATION SUPPORT
   - [administration support considerations based on medication class when appropriate]

3. ADVERSE EVENT MONITORING
   - [monitoring considerations based on the medication and provided notes]

4. LABORATORY MONITORING SCHEDULE
   - [recommended monitoring categories]
   - Use [LAB VALUES NOT PROVIDED] if actual values are not included.

5. DRUG INTERACTION MANAGEMENT
   - [interaction review plan]
   - Use [CURRENT MEDICATION LIST NOT PROVIDED] if no medication list appears in the clinical notes.

6. PATIENT EDUCATION CHECKLIST
   [ ] [education item]
   [ ] [education item]
   [ ] [education item]

7. COORDINATION OF CARE
   - [coordination step with referring provider]
   - Provider fax: [PROVIDER FAX NOT PROVIDED]

================================================================================
MONITORING PLAN & FOLLOW-UP SCHEDULE
================================================================================
WEEK 1: [early tolerance/adherence follow-up]
WEEK 2: [continued tolerance/adherence follow-up]
WEEK 4: [clinical response and monitoring review]
WEEK 8: [refill/adherence and safety check]
WEEK 12: [therapy effectiveness and provider update]
ONGOING: [ongoing monitoring plan]

================================================================================
CLINICAL NOTES
================================================================================
[briefly summarize only the provided clinical notes and do not add unsupported facts]

Pharmacist Signature: _________________________ Date: {today}
RPh License #: [LICENSE NUMBER]

================================================================================
END OF CARE PLAN
================================================================================
""".strip()
