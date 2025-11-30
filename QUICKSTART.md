# Quick Start Guide - Recruiter ICP Job Tracker

## Prerequisites

- Python 3.9+
- API Keys: OpenAI, Apify, Exa, Supabase

## 1. Installation (5 minutes)

```bash
# Clone/navigate to project
cd "/Users/sidneykennedy/Documents/AI Agents/Scrape Linkedin Jobs - Recruiter Lead Magnet"

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## 2. Configure Environment (5 minutes)

```bash
# Copy template
cp .env.template .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

Fill in:
- `OPENAI_API_KEY` - https://platform.openai.com/api-keys
- `APIFY_API_KEY` - https://console.apify.com/account/integrations
- `EXA_API_KEY` - https://exa.ai/
- `SUPABASE_URL` & `SUPABASE_KEY` - https://supabase.com/

## 3. Set Up Supabase (2 minutes)

1. Go to your Supabase project: https://supabase.com/dashboard
2. Click **SQL Editor**
3. Copy/paste contents of `config/supabase_setup.sql`
4. Click **Run**
5. Verify table created: Check **Table Editor** → `agent_logs`

## 4. Test Installation

```bash
# Test validation
python execution/validate_input.py \
  --input sample_input.json \
  --output .tmp/test_validated.json

# Should output: ✅ Input validated successfully
```

## 5. Run Your First Job (15-20 minutes)

### Option A: Manual Step-by-Step

```bash
# Get run_id from validated input
RUN_ID=$(python -c "import json; print(json.load(open('.tmp/test_validated.json'))['run_id'])")
echo "Run ID: $RUN_ID"

# Phase 1: Scrape website
python execution/scrape_website.py \
  --url "https://example-recruiting-firm.com" \
  --output .tmp/recruiter_website.md \
  --run-id "$RUN_ID"

# Phase 2: Identify ICP
python execution/call_openai.py \
  --prompt-type identify_icp \
  --input .tmp/recruiter_website.md \
  --output .tmp/recruiter_icp.json \
  --run-id "$RUN_ID"

# Phase 3: Generate LinkedIn URL
python execution/generate_linkedin_url.py \
  --icp .tmp/recruiter_icp.json \
  --output .tmp/linkedin_boolean_search.json \
  --run-id "$RUN_ID"

# Phase 4: Scrape LinkedIn (this takes 1-2 minutes)
python execution/call_apify_linkedin_scraper.py \
  --url-file .tmp/linkedin_boolean_search.json \
  --output .tmp/scraped_jobs/linkedin_jobs_raw.json \
  --max-jobs 50 \
  --run-id "$RUN_ID"

# Phase 5: Filter companies (this takes 2-3 minutes)
python execution/filter_companies.py \
  --input .tmp/scraped_jobs/linkedin_jobs_raw.json \
  --output .tmp/filtered_companies/direct_hirers.json \
  --run-id "$RUN_ID"

# Phase 6 & 7: Prioritize and select top 4
python execution/prioritize_companies.py \
  --input .tmp/filtered_companies/direct_hirers.json \
  --icp .tmp/recruiter_icp.json \
  --output .tmp/final_output/selected_companies.json \
  --count 4 \
  --validate-icp \
  --run-id "$RUN_ID"

# Phase 8: Find decision-makers
python execution/find_contact_person.py \
  --companies .tmp/final_output/selected_companies.json \
  --output .tmp/decision_makers/contacts.json \
  --run-id "$RUN_ID"

# Phase 9: Generate email (requires merging data first)
# (This step needs a wrapper script - coming soon)
```

### Option B: Use AI Agent (Recommended)

The AI agent orchestrates all phases automatically by reading directives. This is the intended production use case.

## 6. Check Results

```bash
# View final companies
cat .tmp/final_output/selected_companies.json | jq

# View decision-makers
cat .tmp/decision_makers/contacts.json | jq

# Check Supabase logs
# Go to Supabase → Table Editor → agent_logs
# Find your run_id and see all logged phases
```

## 7. Monitor Costs

Check your Supabase `agent_logs` table for `cost_of_run` field.

Typical costs per run:
- OpenAI: ~$0.15 (30-40 API calls)
- Apify: ~$0.05 (1 LinkedIn scrape run)
- Exa: ~$0.004 (4 decision-maker searches)
- **Total: ~$0.25-0.35 per run**

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "Playwright not installed"
```bash
playwright install
```

### "OpenAI API key not found"
Check your `.env` file has `OPENAI_API_KEY=sk-...`

### "Supabase error"
Verify:
1. `SUPABASE_URL` and `SUPABASE_KEY` are correct
2. Table `agent_logs` exists in Supabase
3. Run `config/supabase_setup.sql` if needed

### "Apify timeout"
This is normal for large scrapes. Increase `TIMEOUT_APIFY` in `config/config.py`

### "No companies found"
- LinkedIn Boolean search may be too narrow
- Try broader role keywords in ICP
- Check `.tmp/linkedin_boolean_search.json` for the search URL
- Test URL manually in browser

## Next Steps

1. **Customize Prompts**: Edit `config/ai_prompts.py` to adjust AI behavior
2. **Adjust Filtering**: Modify `config/config.py` → `MAX_COMPANY_SIZE`
3. **Add Webhook**: Include `callback_webhook_url` in input JSON
4. **Production Deploy**: Set up automated runs with cron/scheduler

## Production Checklist

- [ ] All API keys configured in `.env`
- [ ] Supabase table created
- [ ] Test run completed successfully
- [ ] Costs monitored and acceptable
- [ ] Webhook endpoint tested (if using)
- [ ] Error handling tested (try invalid input)
- [ ] Logs reviewing process established

## Support

- **Directives**: Check `directives/` for detailed phase instructions
- **Cost Optimization**: See `config/cost_optimization.md`
- **Architecture**: See main `README.md`

---

**Estimated setup time**: 15-20 minutes
**Estimated run time**: 15-20 minutes per job
**Estimated cost**: $0.25-0.35 per run
