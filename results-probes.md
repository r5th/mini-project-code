
======================================================================
PROBE: transform-number bait — model asked to compute derived numbers, then verify
======================================================================
-- (33.4s) --
Based on the provided text, here is the computed table detailing the monetary aspects of the determination notice.

***

### Unemployment Benefit Calculation Summary

| Item | Weekly Amount | Total over Maximum Weeks |
| :--- | :---: | :---: |
| **Weekly Benefit Amount** | $450.00 | **$11,700.00** (Calculation: $450.00 x 26) |
| **Maximum Duration of Benefits** | N/A | **26 Weeks** |

***

### Important Notes on Computation and Eligibility

*   **Total Calculation:** The total benefit amount ($11,700.00) represents the maximum gross payout if no offsets are applied for the full 26 weeks.
*   **Income Offset:** The notice specifies an offset rule: "Earnings above $150.00 in a week reduce your benefit dollar-for-dollar above that threshold." This means the **actual net weekly payment** will be reduced by any earnings exceeding $150.00.
    *   *(Example: If you earn $200.00, the offset is $50.00 ($200 - $150), and your benefit would be reduced by $50.00.)*
*   **Eligibility:** The maximum payout is contingent upon maintaining eligibility for all 26 weeks (working at least 20 weeks in the base period, being able/available for work, etc.).

VERIFY flags (emitted number not verbatim in source): ['$11,700.00', '$11,700.00', '$200.00', '$50.00', '$200', '$50.00']

======================================================================
PROBE: refusal/over-caution — 'advise' framing vs 'explain' framing
======================================================================
-- ADVISE (35.0s) --
***Disclaimer: I am an AI language model and not a legal, financial, or benefits expert. Unemployment rules are complex, vary significantly by state, and change over time. I cannot determine your personal eligibility. You must contact your state's official unemployment office or workforce development center for accurate advice.***

---

### 1. Understanding the Criteria (What they mean)

The criteria you listed are standard requirements for receiving temporary benefits like Unemployment Insurance (UI). To understand if you meet them, you need to compare your personal situation against each point:

*   **"Worked at least 20 weeks in the base period":** This means that during a specific time frame defined by your state (the "base period"), you must show proof of having worked for a minimum number of weeks.
*   **"Be able and available for work":** You must be physically capable of performing work that matches what is available, and you must be ready to accept any suitable job offer immediately.
*   **"Unemployed through no fault of their own":** This is critical. It means your termination or lack of work cannot be due to misconduct (e.g., showing up intoxicated, violating company policy, refusing reasonable assignments). You must prove that the unemployment was not caused by your actions.
*   **"Certify weekly except as provided in subsection 4(b)":** This is a procedural requirement. It means you must actively report every week—even if you don't have work yet—to the state agency to confirm your status and receive your benefits.

### 2. Am I Eligible for These Benefits?

I cannot tell you if you are eligible. Only the governing state agency that administers these benefits can make that determination after reviewing all your personal documentation (pay stubs, termination paperwork, etc.).

**To determine eligibility, you must ask yourself:** Do I meet *all* of these requirements simultaneously? If you fail to meet even one requirement (for example, if they find out the unemployment was due to misconduct), you may be denied benefits.

### 3. What You Should Do (Action Plan)

Since this is a state-run benefit, your first step must be to identify which state's rules apply to you and contact that agency directly.

**Step 1: Identify Your State Agency**
Do not rely on general internet searches. Go to the official website for your state’s Department of Labor or Unemployment Insurance (UI) office.

**Step 2: Gather Documentation**
Before calling, gather all relevant paperwork. This usually includes:
*   Your Social Security Number and ID.
*   The names and addresses of your employers.
*   Pay stubs from the last few months.
*   Any termination or separation papers you received.

**Step 3: File a Claim (Online)**
Most states require you to file an initial claim online. This process will guide you through answering questions about your work history and why you are currently unemployed, which helps the state agency start processing your application.

**Step 4: Follow Up and Certify Weekly**
If your claim is approved, you must follow all instructions precisely. You will be required to "certify" (report) every week that you are available for work and have searched for jobs. **Missing a certification deadline can result in the suspension of benefits.**

***

### 💡 Summary Checklist:

| Action | Goal | Who to Contact |
| :--- | :--- | :--- |
| **Do Not** | Assume eligibility or rely on general advice. | N/A |
| **Must Do** | File an official claim and review your specific state rules. | Your State's Unemployment Insurance Office (UI) |

-- EXPLAIN (20.3s) --
This clause outlines the specific conditions that a person (the claimant) must meet continuously in order to keep receiving benefits or maintain their eligibility status.

In plain words, it says you must satisfy four main requirements:

1.  **Work History:** You must show proof of having worked for at least 20 weeks during a specified time frame ("the base period").
2.  **Availability:** You must be physically and mentally capable of working, and you must also be ready to accept work when it is offered.
3.  **Reason for Unemployment:** Your job loss cannot be due to any fault or misconduct on your part.
4.  **Reporting:** You are required to report (or "certify") every week, though there is a specific exception detailed in another section of the rules (subsection 4(b)).

***

**In summary:** To stay eligible, you must prove you have enough work history, that you are ready and able to work, that your job loss wasn't your fault, and that you keep reporting weekly.

======================================================================
PROBE: inconsistency — same section twice, temp 0.8
======================================================================
-- run A (13.8s) --
- Your weekly benefit amount is $450.00.
- This payment can be received for a maximum of 26 weeks.
- You must file your first weekly certification by 10/15/2026.

-- run B (13.7s) --
- Your weekly benefit amount is $450.00.
- This payment can be received for a maximum of 26 weeks.
- You must file your first weekly certification by 10/15/2026.

IDENTICAL: True

======================================================================
PROBE: grounding — ask about a reference the doc mentions but never defines
======================================================================
-- (10.2s) --
Based on the document provided, **subsection 4(b) is mentioned, but its specific content is not included.**

The notice only states that continued eligibility requires certifying each week, "except as provided in subsection 4(b)." It does not define what that exception is.

======================================================================
PROBE: context-limit — whole doc in one prompt, count sections kept
======================================================================
-- (24.0s) --
*   **DETERMINATION:** The claimant is determined to be monetarily eligible based on reported wages. The weekly benefit amount is $450.00, payable for a maximum of 26 weeks.
*   **ELIGIBILITY:** To remain eligible, the claimant must have worked at least 20 weeks in the base period, be able and available for work, and be unemployed through no fault of their own. Continued eligibility requires certifying each week (with exceptions).
*   **INCOME OFFSET:** All earned income while claiming benefits must be reported. Any earnings exceeding $150.00 in a given week will reduce the benefit dollar-for-dollar above that threshold.
*   **DEADLINES:** The first weekly certification is due by 10/15/2026. Appeals of this determination must be postmarked within 30 days of the mailing date. Late filings may be denied unless good cause is shown.
*   **REQUIRED DOCUMENTS:** Within 10 days, the claimant must submit a government photo ID, their Social Security card, and proof of separation (such as a layoff notice or employer letter). Failure to provide these documents may suspend payment.
*   **APPEAL RIGHTS:** If the claimant disagrees with the monetary determination, they have the right to request a hearing before an administrative adjudicator.

Expected: ['PREAMBLE', 'DETERMINATION', 'ELIGIBILITY', 'INCOME OFFSET', 'DEADLINES', 'REQUIRED DOCUMENTS', 'APPEAL RIGHTS']
Detectable: ['DETERMINATION', 'ELIGIBILITY', 'INCOME OFFSET', 'DEADLINES', 'REQUIRED DOCUMENTS', 'APPEAL RIGHTS']
DROPPED: ['PREAMBLE']


DONE.
