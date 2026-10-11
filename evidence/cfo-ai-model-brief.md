# cfo.ai model brief — TestGap Agent

**Status:** pending cfo.ai work. This prompt has not yet been entered into cfo.ai;
the resulting model/export and screenshot still need to be created there.

## Prompt for Ari

```text
Build an 18-month, driver-based business model for TestGap Agent, a developer
tool that finds high-risk untested Python code, drafts pytest tests, repairs
failing candidates, and verifies useful tests with controlled mutations.

Business model to evaluate:
- Open-source self-hosted edition for individual developers.
- Paid hosted/team edition, with team subscription pricing tested at $19, $29,
  and $49 per team per month as illustrative price points, not validated prices.
- Include monthly customer growth, churn, and scans per paid team as editable
  assumptions. Create downside, base, and upside scenarios; clearly label every
  unvalidated assumption and do not present it as market research.

Model revenue from paid teams and realized monthly price. Model variable costs
from analyses per team and measured model tokens/cost per analysis. Add hosting,
storage, observability, support, payment fees, and any other material operating
costs as separate drivers. Treat event credits as temporary credits and show
them separately from sustainable unit economics. Leave unknown starting cash
as an explicit input rather than inventing a value.

Show monthly revenue, gross profit and margin, contribution per analysis,
operating expenses, net burn, ending cash, and runway for each scenario. Make
the formulas and assumptions inspectable. Identify which measured usage data we
need to replace the placeholders before treating this plan as a forecast.
```

## Inputs to replace with measured values

- Bedrock/model input and output tokens per successful run.
- Model cost per run using the selected model and current regional rates.
- Runs per team per month, including repair attempts and mutation checks.
- Compute/storage/observability cost per run.
- Starting cash and any recurring support or labor costs.
- Trial-to-paid conversion, churn, and willingness to pay from user interviews.

Save the cfo.ai model or an export/screenshot here after the team completes it.
