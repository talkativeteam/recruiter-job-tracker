# Quick Start: Exa Fallback for Niche ICPs

## What Is This?

Automatic fallback system that activates when LinkedIn can't find enough jobs for your niche ICP. Instead of failing, the system switches to finding companies directly and scraping their career pages.

## When Does It Activate?

**Automatically triggers when:**
- LinkedIn returns fewer than 10 jobs
- Indicates ICP is too specialized for LinkedIn job boards

**Examples of niche ICPs:**
- Quantum computing roles
- Rare medical specialties  
- Emerging technologies (Web3, AR/VR)
- Highly specialized engineering

## Setup (One-Time)

### 1. Get Exa API Key

```bash
# Sign up at https://exa.ai
# Get your API key from dashboard
```

### 2. Add to .env File

```bash
EXA_API_KEY=your-actual-key-here
```

That's it! No code changes needed.

## How to Use

### Option 1: Use Normally (Recommended)

Just run your workflow as usual:

```bash
python execution/orchestrator.py --input input.json
```

The system will:
1. Try LinkedIn first
2. If insufficient results → automatically use Exa fallback
3. Continue pipeline normally

**You don't need to do anything special!**

### Option 2: Test with Niche ICP

Create `test_niche_icp.json`:

```json
{
  "client_name": "Quantum Talent Group",
  "client_email": "hire@quantumtalent.com",
  "client_website": "https://quantumtalent.com",
  "max_jobs_to_scrape": 100
}
```

Run:
```bash
python execution/orchestrator.py --input test_niche_icp.json
```

Expected output:
```
📊 Phase 4: Scraping LinkedIn jobs...
🔄 Attempt 1: Scraping past 24 hours...
⚠️ Only 3 jobs found in 24h (need 30)
🔄 Attempt 2: Retrying with past 7 days...
⚠️ Only 5 jobs found in 7d

🔄 ICP TOO NICHE: Only 5 jobs found on LinkedIn
🌐 Activating Exa fallback workflow...
🔍 Exa search query: companies hiring Quantum Software Engineer...
✅ Exa found 18 potential companies
🔍 Extracting jobs from IonQ...
✅ Found 4 jobs at IonQ
🔍 Extracting jobs from Rigetti Computing...
✅ Found 3 jobs at Rigetti Computing
...
✅ Exa fallback successful: 12 companies actively hiring
✅ Total: 42 jobs scraped (source: exa_fallback)
```

## Monitoring

### Check Which Source Was Used

Look for this in output:
```python
"stats": {
  "data_source": "exa_fallback"  # or "linkedin"
}
```

### Check Logs

```bash
# Standard run
✅ Total: 87 jobs scraped (source: linkedin)

# Fallback run  
✅ Total: 42 jobs scraped (source: exa_fallback)
```

## Cost Comparison

### Normal LinkedIn Run
```
Total: $0.30
- OpenAI: $0.20
- Apify: $0.05  
- Exa: $0.004
```

### Exa Fallback Run
```
Total: $0.35
- OpenAI: $0.25 (more calls for job extraction)
- Exa: $0.001 (company search)
- Apify: $0.00 (not used)
- Scraping: $0.00 (free)
```

**Difference:** +$0.05 per niche ICP run

## Troubleshooting

### "Exa API key not configured"

**Problem:** Missing EXA_API_KEY in .env

**Solution:**
```bash
# Add to .env file
EXA_API_KEY=your-key-here
```

### "Exa found 0 companies"

**Problem:** ICP might be too niche even for Exa

**Solution:** 
- Check if ICP has real companies hiring
- Try broader industries/roles
- May need manual research

### "No jobs found via LinkedIn or Exa fallback"

**Problem:** Truly no companies hiring for this ICP

**Solution:**
- ICP might be too specific
- Suggest broader roles to client
- Check if industry exists

## Configuration

### Adjust Fallback Threshold

Edit `execution/orchestrator.py`:

```python
# Current: Triggers at < 10 jobs
exa_fallback_threshold = 10

# More aggressive: Triggers at < 20 jobs  
exa_fallback_threshold = 20

# Less aggressive: Triggers at < 5 jobs
exa_fallback_threshold = 5

# Disable fallback: Never triggers
exa_fallback_threshold = 0
```

### Adjust Company Search Count

Edit `execution/call_exa_api.py`:

```python
# Current: Search 30 companies
max_results = 30

# Search more companies (slower but more options)
max_results = 50

# Search fewer companies (faster but fewer options)
max_results = 20
```

## Best Practices

### ✅ DO:
- Let system decide automatically
- Monitor costs for niche ICPs
- Check Supabase logs for fallback usage
- Test with real niche ICPs

### ❌ DON'T:
- Disable fallback unless necessary
- Set threshold too low (< 5)
- Assume all runs will use fallback
- Skip Exa API key setup

## Example Scenarios

### Scenario 1: Normal Tech Recruiter
```
ICP: Software Engineers in Tech
LinkedIn Result: 150 jobs ✅
Fallback: Not triggered
Cost: $0.30
```

### Scenario 2: Specialized Medical Recruiter  
```
ICP: Pediatric Neuro-Oncologists
LinkedIn Result: 3 jobs ❌
Fallback: Triggered ✅
Exa Result: 8 companies, 22 jobs
Cost: $0.35
```

### Scenario 3: Quantum Computing Recruiter
```
ICP: Quantum Software Engineers
LinkedIn Result: 6 jobs ❌
Fallback: Triggered ✅
Exa Result: 12 companies, 45 jobs  
Cost: $0.36
```

## FAQ

**Q: Will this slow down my pipeline?**
A: Fallback adds ~30-60 seconds for company scraping. Only activates when needed.

**Q: Can I force using Exa instead of LinkedIn?**
A: Not directly, but you can set `exa_fallback_threshold = 999` to always trigger.

**Q: What if Exa also fails?**
A: Pipeline fails gracefully with clear error message. Manual research needed.

**Q: Is my data from Exa as good as LinkedIn?**
A: Often better! Direct from company websites, fresher, more accurate.

**Q: Can I use both LinkedIn AND Exa results?**
A: Currently either/or. Hybrid approach is possible future enhancement.

## Support

**Check these first:**
1. Exa API key in .env
2. System has internet access
3. OpenAI API key working (needed for job extraction)

**Still having issues?**
- Check `directives/exa_fallback_workflow.md` for details
- Review Supabase logs for error messages
- Test with provided niche ICP examples

---

**Remember:** This is fully automatic. Just ensure EXA_API_KEY is set and the system handles the rest!
