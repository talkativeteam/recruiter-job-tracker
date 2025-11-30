# 🎯 YOUR NEXT STEPS

Great! You've already completed:
- ✅ Created Supabase table (ran the SQL)
- ✅ Saved API keys to `.env`

## Now let's test the system! Here's what to do:

---

## Step 1: Install Dependencies (5 minutes)

```bash
cd "/Users/sidneykennedy/Documents/AI Agents/Scrape Linkedin Jobs - Recruiter Lead Magnet"

# Run the automated setup script
./setup.sh
```

Or manually:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

---

## Step 2: Update Supabase Table (1 minute)

Since I just updated the schema to capture MORE data, you need to add the new columns:

Go to Supabase SQL Editor and run:

```sql
-- Add new columns to existing table
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS client_website TEXT;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS exa_webset TEXT;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS icp TEXT;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS job_identified_by TEXT DEFAULT 'LinkedIn Jobs Scraper';
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS job_posting_links TEXT[];
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS job_posting_date TIMESTAMP WITH TIME ZONE;
```

**What this gives you**:
- ✅ Client website URL (for reference)
- ✅ Full ICP data (industries, sizes, roles) as JSON
- ✅ All job posting URLs (for verification)
- ✅ Job posting dates (when jobs were posted)
- ✅ Exa webset (if used - can be null)

**Cost**: $0.00 - We're already collecting this data, just logging it now!

---

## Step 3: Test the System (15 minutes)

### Option A: Quick Validation Test
```bash
# Activate virtual environment
source venv/bin/activate

# Test input validation (should create Supabase entry)
python execution/validate_input.py \
  --input sample_input.json \
  --output .tmp/test_validated.json

# Check output
cat .tmp/test_validated.json

# Check Supabase
# Go to: https://supabase.com/dashboard → Table Editor → agent_logs
# You should see a new row with run_id and client info
```

### Option B: Full End-to-End Test (Real Run)

**⚠️ This will cost ~$0.25-0.35 and take 15-20 minutes**

Update `sample_input.json` with a REAL recruiter website:
```json
{
  "client_name": "Test Recruiter",
  "client_email": "test@example.com",
  "client_website": "https://[REAL-RECRUITING-WEBSITE].com",
  "max_jobs_to_scrape": 20,
  "callback_webhook_url": null
}
```

Then run:
```bash
# Get the run_id from validation
python execution/validate_input.py \
  --input sample_input.json \
  --output .tmp/validated_input.json

RUN_ID=$(python -c "import json; print(json.load(open('.tmp/validated_input.json'))['run_id'])")
echo "Run ID: $RUN_ID"

# Phase 1: Scrape website (FREE - uses HTTP or Playwright)
python execution/scrape_website.py \
  --url "$(python -c "import json; print(json.load(open('.tmp/validated_input.json'))['client_website'])")" \
  --output .tmp/recruiter_website.md \
  --run-id "$RUN_ID"

# Phase 2: Identify ICP (~$0.005)
python execution/call_openai.py \
  --prompt-type identify_icp \
  --input .tmp/recruiter_website.md \
  --output .tmp/recruiter_icp.json \
  --run-id "$RUN_ID"

# Phase 3: Generate LinkedIn URL (~$0.003)
python execution/generate_linkedin_url.py \
  --icp .tmp/recruiter_icp.json \
  --output .tmp/linkedin_boolean_search.json \
  --run-id "$RUN_ID"

# Phase 4: Scrape LinkedIn (1-2 min, ~$0.05)
python execution/call_apify_linkedin_scraper.py \
  --url-file .tmp/linkedin_boolean_search.json \
  --output .tmp/scraped_jobs/linkedin_jobs_raw.json \
  --max-jobs 20 \
  --run-id "$RUN_ID"

# Phase 5: Filter companies (2-3 min, ~$0.10)
python execution/filter_companies.py \
  --input .tmp/scraped_jobs/linkedin_jobs_raw.json \
  --output .tmp/filtered_companies/direct_hirers.json \
  --run-id "$RUN_ID"

# Phase 6 & 7: Prioritize and select top 4 (~$0.02)
python execution/prioritize_companies.py \
  --input .tmp/filtered_companies/direct_hirers.json \
  --icp .tmp/recruiter_icp.json \
  --output .tmp/final_output/selected_companies.json \
  --count 4 \
  --validate-icp \
  --run-id "$RUN_ID"

# Phase 8: Find decision-makers (~$0.004)
python execution/find_contact_person.py \
  --companies .tmp/final_output/selected_companies.json \
  --output .tmp/decision_makers/contacts.json \
  --run-id "$RUN_ID"

echo "✅ Test complete! Check Supabase for full logs."
```

---

## Step 4: Check Your Results

### View Output Files
```bash
# View ICP data
cat .tmp/recruiter_icp.json | python -m json.tool

# View final companies
cat .tmp/final_output/selected_companies.json | python -m json.tool

# View decision-makers
cat .tmp/decision_makers/contacts.json | python -m json.tool
```

### Check Supabase Logs

Go to: https://supabase.com/dashboard → Table Editor → `agent_logs`

You should see:
- ✅ `run_id` - Your unique run ID
- ✅ `run_status` - "running" or "completed"
- ✅ `client_name`, `client_email`, `client_website` - Recruiter info
- ✅ `icp` - Full ICP JSON (industries, sizes, roles)
- ✅ `job_posting_links` - Array of all LinkedIn job URLs
- ✅ `job_posting_date` - When jobs were posted
- ✅ `companies_found` - Total companies scraped
- ✅ `companies_validated` - Direct hirers only
- ✅ `final_companies_selected` - Should be 4 (or fewer)
- ✅ `cost_of_run` - Total cost breakdown
- ✅ `phase` - Current phase

---

## Step 5: What to Expect

### If Everything Works ✅
- Supabase will have a complete log with ALL the data
- You'll have 4 companies in `.tmp/final_output/selected_companies.json`
- You'll have decision-makers in `.tmp/decision_makers/contacts.json`
- Total cost: ~$0.25-0.35

### Common Issues

**"Module not found" errors**
```bash
pip install -r requirements.txt
```

**"Playwright not installed"**
```bash
playwright install chromium
```

**"Supabase error: relation does not exist"**
- Make sure you ran the ALTER TABLE commands above

**"OpenAI API key not found"**
- Check `.env` has `OPENAI_API_KEY=sk-...` (real key)

**"Apify timeout"**
- Normal for first run. Wait 2-3 minutes.

---

## Step 6: Production Setup (After Testing)

Once your test works:

1. **Create orchestration script** (I can help with this)
   - Runs all phases automatically
   - Handles errors gracefully
   - Sends results to webhook

2. **Set up monitoring**
   - Create Supabase dashboard to track runs
   - Set up alerts for failed runs
   - Monitor costs

3. **Deploy webhook endpoint** (if needed)
   - Receive results in your app
   - Store in your database
   - Trigger email sending

4. **Scale up**
   - Run multiple times per day
   - Process batch of recruiters
   - Monitor cost trends

---

## 🎯 Quick Commands Reference

```bash
# Activate virtual environment
source venv/bin/activate

# Test validation
python execution/validate_input.py --input sample_input.json --output .tmp/test.json

# View Supabase logs
# Go to: https://supabase.com/dashboard → Table Editor → agent_logs

# Check a specific run
# SELECT * FROM agent_logs WHERE run_id = 'your-run-id';
```

---

## 💡 What Changed

### New Logged Data (No Extra Cost!)
- ✅ **Client website** - Reference for future runs
- ✅ **ICP JSON** - Full industries, sizes, roles, keywords
- ✅ **Job posting links** - Array of all LinkedIn URLs (for verification)
- ✅ **Job posting date** - When jobs were posted
- ✅ **Job identified by** - Always "LinkedIn Jobs Scraper"
- ✅ **Exa webset** - If Exa API is used (can be null)

### Why This Is Useful
- **Debugging**: See exact ICP extracted, verify job links
- **Analytics**: Track which ICPs find more companies
- **Verification**: Customer can check job links are real
- **Audit**: Complete trail of what was scraped and when
- **Cost**: $0.00 extra - we already have this data!

---

## Need Help?

1. **Setup issues**: Check `.env` has all API keys
2. **Supabase issues**: Make sure you ran both SQL scripts
3. **Test fails**: Run each phase individually to find the error
4. **Questions**: Check `QUICKSTART.md` or `README.md`

---

**Ready to test? Start with Step 1!** 🚀
