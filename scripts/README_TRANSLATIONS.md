# LiPan Auto Translation Builder

## 🎯 Overview

Automated system for extracting Chinese automotive terms from che168.com and building comprehensive Chinese→Russian translations for the LiPan Auto platform.

### Features

✅ **Safe Scraping** - Anti-detection with proxy rotation and rate limiting
✅ **Smart Extraction** - Extracts terms from car listings, specs, and tags
✅ **Auto Translation** - Supports Yandex, DeepL, and Google Translate APIs
✅ **Progress Tracking** - Resume from last checkpoint if interrupted
✅ **Conflict Detection** - Reviews existing translations before merging
✅ **Backup Creation** - Automatic backups before modifying files

---

## 🚀 Quick Start

### 1. Setup Dependencies

```bash
cd lipanauto-proxy/scripts

# Install required Python packages
pip install requests
```

No additional packages needed! The script uses only Python standard library + requests.

### 2. Configure API Key

```bash
# Copy the environment template
cp .env.translation.template .env.translation

# Edit and add your API key
nano .env.translation
```

**Get a FREE Yandex API Key** (Recommended):
1. Go to https://yandex.com/dev/translate/
2. Sign up for a free account
3. Create an API key (free tier: 1M characters/month)
4. Paste it in `.env.translation`

### 3. Test with Dry Run

```bash
# Test without making real API calls
python translation_builder.py --dry-run --pages 5
```

Expected output:
```
🚀 Starting extraction from 5 pages...
🔍 DRY RUN MODE - No actual API calls
✅ Extraction complete! Total unique Chinese terms: 3
💾 Saved 3 terms to chinese_terms.json
```

### 4. Run Full Extraction

```bash
# Extract terms and translate (20 pages = ~400 cars)
python translation_builder.py --extract --translate --pages 20
```

This will:
- Fetch 20 pages from che168.com API
- Extract ~1,500-2,500 unique Chinese terms
- Filter out existing translations
- Translate ~500-1,000 NEW terms to Russian
- Save results to `new_translations.json`

### 5. Review and Merge

```bash
# Review translations before merging
python translation_builder.py --merge --review

# Merge into translations.ts
python translation_builder.py --merge
```

---

## 📖 Usage Guide

### Command Line Options

```bash
python translation_builder.py [OPTIONS]

# Operation Modes:
  --dry-run          Test mode (no API calls)
  --extract          Extract Chinese terms from che168
  --translate        Translate extracted terms
  --merge            Merge translations into translations.ts
  --review           Show conflicts before merging

# Parameters:
  --pages N          Number of pages to scrape (default: 20)
  --service SERVICE  Translation service: yandex|deepl|google|manual
  --verbose, -v      Enable debug logging

# Examples:
  python translation_builder.py --dry-run --pages 5
  python translation_builder.py --extract --translate --pages 20
  python translation_builder.py --merge --review
  python translation_builder.py --extract --translate --service deepl
```

### Typical Workflow

#### **Step 1: Dry Run Test** (1 minute)
```bash
python translation_builder.py --dry-run --pages 5
```
Validates setup without making real API calls.

#### **Step 2: Extract & Translate** (15-30 minutes for 20 pages)
```bash
python translation_builder.py --extract --translate --pages 20 --verbose
```
Scrapes che168, extracts Chinese terms, translates to Russian.

**Progress Output:**
```
🚀 LiPan Auto Translation Builder
📡 Fetching page 1...
✅ Page 1 fetched successfully
📊 Page 1: Found 87 unique terms (Total: 87)
⏳ Waiting 4.23s before next request
📡 Fetching page 2...
...
✅ Extraction complete! Total unique Chinese terms: 1,847
🔍 Found 623 NEW terms to translate
🌐 Translating 623 terms using yandex...
✅ Translation complete! Translated 623 terms
📊 Report generated: translation_report.md
```

#### **Step 3: Review Results**
```bash
# Check the report
cat translation_report.md

# Review translations
head -n 50 new_translations.json
```

#### **Step 4: Merge Translations**
```bash
# Preview conflicts
python translation_builder.py --merge --review

# Merge (creates backup automatically)
python translation_builder.py --merge
```

---

## 📁 Generated Files

After running extraction and translation:

```
scripts/
├── chinese_terms.json          # All extracted Chinese terms
├── new_terms.json              # Terms not in existing dictionary
├── new_translations.json       # Newly translated terms (ready to merge)
├── translation_report.md       # Summary report
├── progress.json               # Resume checkpoint
├── scraping.log                # Detailed execution log
└── .env.translation            # Your API keys (gitignored)
```

### File Descriptions

| File | Purpose | Sample |
|------|---------|--------|
| `chinese_terms.json` | All unique Chinese terms extracted | `["奔驰", "宝马", "排量", ...]` |
| `new_terms.json` | Terms missing from dictionary | `["电动机", "续航里程", ...]` |
| `new_translations.json` | **Main output** - translations to merge | `{"电动机": "Электродвигатель"}` |
| `translation_report.md` | Statistics and next steps | See below |
| `progress.json` | Resume point if interrupted | `{"last_page": 15, ...}` |

### Sample Report

```markdown
# Translation Builder Report
Generated: 2025-01-15 14:32:45

## Summary
- **Total Chinese Terms Extracted**: 1,847
- **New Terms (not in dictionary)**: 623
- **Successfully Translated**: 623
- **Translation Rate**: 100.0%

## Statistics
- **Extraction Pages**: 20
- **API Requests Made**: 92
- **Translation Service**: yandex
```

---

## ⚙️ Configuration

### `config.json` Settings

```json
{
  "max_pages": 20,              // Pages to scrape (20 = ~400 cars)
  "page_size": 20,              // Cars per page
  "min_delay": 3,               // Min seconds between requests
  "max_delay": 7,               // Max seconds between requests
  "max_requests_per_proxy": 20, // Rotate proxy after N requests
  "max_daily_requests": 500,    // Daily safety limit
  "translation_service": "yandex",
  "batch_size": 100             // Terms per translation batch
}
```

### Preset Configurations

**Conservative** (Safest, slowest):
```json
{
  "max_pages": 10,
  "min_delay": 5,
  "max_delay": 10,
  "max_requests_per_proxy": 15
}
```

**Balanced** (Default):
```json
{
  "max_pages": 20,
  "min_delay": 3,
  "max_delay": 7,
  "max_requests_per_proxy": 20
}
```

**Aggressive** (Faster, higher risk):
```json
{
  "max_pages": 50,
  "min_delay": 2,
  "max_delay": 5,
  "max_requests_per_proxy": 30
}
```

---

## 🛡️ Safety Features

### Anti-Detection Measures

✅ **Proxy Rotation** - Switches proxies every 20 requests
✅ **Random Delays** - 3-7 second waits between requests
✅ **Realistic Headers** - Mimics real browser
✅ **Session Management** - Maintains cookies like a user
✅ **Rate Limit Handling** - Backs off on 429 responses
✅ **Daily Request Limit** - Stops at 500 requests/day

### Error Handling

- **429 Rate Limited** → Wait 60s, retry
- **Network Error** → Log error, continue to next page
- **Translation API Error** → Skip term, continue batch
- **Interrupted Execution** → Resume from `progress.json`

### Resume Capability

If the script is interrupted:

```bash
# Progress is auto-saved every 5 pages
# Simply re-run the command to resume
python translation_builder.py --extract --translate --pages 20
```

The script will:
1. Load `progress.json`
2. Skip already processed pages
3. Continue from last checkpoint

---

## 🌐 Translation Services

### Yandex Translate (RECOMMENDED)

**Why Yandex?**
- Best for Chinese→Russian translations
- FREE tier: 1,000,000 chars/month
- Excellent automotive term accuracy

**Setup:**
1. Visit: https://yandex.com/dev/translate/
2. Create free account
3. Get API key
4. Add to `.env.translation`: `YANDEX_API_KEY=...`

### DeepL API (Alternative)

**Why DeepL?**
- Premium translation quality
- FREE tier: 500,000 chars/month
- Better for technical descriptions

**Setup:**
1. Visit: https://www.deepl.com/pro-api
2. Sign up for free API
3. Get API key
4. Add to `.env.translation`: `DEEPL_API_KEY=...`
5. Run with: `--service deepl`

### Manual Translation

For automotive-specific terms that need human review:

```bash
# Export to CSV for manual translation
python translation_builder.py --extract --service manual

# Fill in translations in: terms_for_manual_translation.csv
# Then import (future feature)
```

---

## 📊 Expected Results

### From 20 Pages (~400 cars)

| Metric | Estimate |
|--------|----------|
| **Total Chinese Terms** | 1,500 - 2,500 |
| **New Terms** | 500 - 1,000 |
| **Translation Time** | 5 - 10 minutes |
| **API Cost** | $0 (FREE tier) |
| **Total Runtime** | 15 - 30 minutes |

### Term Categories

- **Car Brands/Models**: 200-300 terms
- **Specifications**: 300-500 terms (displacement, fuel type, etc.)
- **Features/Options**: 400-600 terms (sunroof, leather, etc.)
- **Condition/Tags**: 200-300 terms (certified, warranty, etc.)

---

## 🔧 Troubleshooting

### "YANDEX_API_KEY not found"

**Solution:**
```bash
# Ensure .env.translation exists
cp .env.translation.template .env.translation

# Add your API key
echo "YANDEX_API_KEY=your_actual_key" >> .env.translation
```

### "Rate limited on page X"

**Solution:**
```bash
# Script automatically waits 60s and continues
# Or increase delays in config.json:
{
  "min_delay": 5,
  "max_delay": 10
}
```

### "translations.ts not found"

**Solution:**
```bash
# Ensure you're in the correct directory
cd lipanauto-proxy/scripts

# Check path in script matches your setup
# Default: ../lipanmotorsapp/lib/translations.ts
```

### Script Interrupted / Crashed

**Solution:**
```bash
# Simply re-run - it will resume from progress.json
python translation_builder.py --extract --translate --pages 20
```

---

## 🎯 Best Practices

### 1. Start Small
```bash
# Test with 5 pages first
python translation_builder.py --extract --translate --pages 5
```

### 2. Use Dry Run
```bash
# Always test with dry-run before real scraping
python translation_builder.py --dry-run --pages 10
```

### 3. Review Before Merge
```bash
# Check for conflicts
python translation_builder.py --merge --review

# Review translations manually
cat new_translations.json | jq . | less
```

### 4. Backup Important
```bash
# Script auto-creates backup, but you can make your own:
cp ../lipanmotorsapp/lib/translations.ts translations.ts.manual-backup
```

### 5. Gradual Scaling
- **First run**: 5-10 pages (test)
- **Second run**: 20 pages (standard)
- **Third run**: 50 pages (comprehensive)
- **Fourth run**: 100 pages (complete coverage)

---

## 📈 Scaling Guide

### Single Run (20 pages)
```bash
python translation_builder.py --extract --translate --pages 20
# Result: ~1,000 new terms
# Time: 20-30 minutes
# Cost: FREE
```

### Comprehensive Coverage (Multiple Runs)

**Day 1**: General cars (pages 1-20)
```bash
python translation_builder.py --extract --translate --pages 20
python translation_builder.py --merge
```

**Day 2**: More variety (pages 21-40)
```bash
# Edit config.json to start from page 21
python translation_builder.py --extract --translate --pages 40
python translation_builder.py --merge
```

**Day 3**: Complete coverage (pages 41-100)
```bash
python translation_builder.py --extract --translate --pages 100
python translation_builder.py --merge
```

**Total**: ~10,000+ comprehensive automotive terms

---

## 🤝 Contributing

Found a better translation for an automotive term?

1. Edit `lipanmotorsapp/lib/translations.ts` manually
2. Or create `custom_translations.json` with overrides
3. Run merge with `--prefer-custom` flag (future feature)

---

## 📝 License

Part of LiPan Auto platform - Internal use only

---

## 🆘 Support

Issues? Contact the development team or check `scraping.log` for detailed error messages.

**Log Analysis:**
```bash
# View recent errors
tail -n 50 scraping.log | grep ERROR

# View full log
cat scraping.log | less
```

---

## 🎉 Success Checklist

After running the translation builder:

- [x] Dry run completed successfully
- [x] Extracted 1,500+ Chinese terms
- [x] Translated 500+ new terms
- [x] Reviewed `translation_report.md`
- [x] Checked `new_translations.json` for quality
- [x] Merged into `translations.ts` (backup created)
- [x] Tested translations in frontend
- [x] Committed changes to git

**Ready to deploy!** 🚀

---

*Generated by LiPan Auto Translation Builder - Making Chinese cars speak Russian* 🇨🇳→🇷🇺
