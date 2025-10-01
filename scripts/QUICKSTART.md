# Translation Builder - Quick Start Guide
## Manual Translation Edition

## 🚀 Get 1,000+ Translations in 3 Simple Steps

### NO API Keys Required! ✅
### NO External Services! ✅
### Full Control Over Translations! ✅

---

## Step 1: Extract Data (20-30 minutes)

```bash
cd /Users/shindmitriy/Desktop/Coding/LipanAuto/Lipanauto\ Website/lipanauto-proxy/scripts

# Extract from 20 pages (~400 cars)
python3 translation_builder.py --extract --pages 20
```

**What This Does:**
- Fetches 400 cars from che168.com
- Extracts ~1,500-2,500 unique Chinese terms
- Categorizes terms (brands, specs, features, etc.)
- Tracks frequency (most common first)
- Preserves usage context
- Generates CSV file ready for translation

**Output Files:**
- `car_data.json` - Complete car database (useful for future features!)
- `chinese_terms_categorized.json` - Terms organized by category
- `translation_template.csv` - **Open this next!**
- `translation_report.md` - Summary report

---

## Step 2: Translate in Excel/Google Sheets (1-4 hours)

```bash
# Open the CSV file
open translation_template.csv
```

**The CSV includes:**
- **Chinese** - The term to translate
- **Category** - Type (brand/spec/feature/etc.)
- **Frequency** - How often it appears
- **Context** - Example usage
- **Russian** - **Fill this column!** (terms marked ⚠️ NEW)
- **Status** - ✓ Exists (already translated) or ⚠️ NEW
- **Notes** - Your notes

**Translation Tips:**
- Focus on ⚠️ NEW terms only
- High frequency = translate first
- Check "Context" column to understand usage
- **Brands**: Keep Latin (BMW, Mercedes-Benz)
- **Models**: Hybrid (奥迪A4 → Audi A4)
- **Specs**: Translate (排量 → Объем двигателя)
- **Features**: Translate (天窗 → Люк)

**You can translate incrementally:**
- Session 1: Top 100 most frequent terms (30 min)
- Session 2: Next 200 terms (1 hour)
- Session 3: Remaining terms (as needed)

---

## Step 3: Import & Merge (1 minute)

```bash
# Import your translations and merge into project
python3 translation_builder.py --import translation_template.csv --merge
```

**Done!** ✅ Your translations are now live!

---

## 📊 Expected Results

### From 20 Pages:
- **Total Chinese Terms**: 1,500-2,500
- **Already Translated**: 500-1,000 (from existing dictionary)
- **NEW Terms to Translate**: 500-1,000
- **Runtime**: 20-30 minutes
- **Cost**: FREE! 💰

### Term Categories:
- Brands/Models: 200-300 terms
- Specifications: 300-500 terms
- Features/Options: 400-600 terms
- Condition/Tags: 200-300 terms

---

## 🎯 Quick Commands

```bash
# Extract 5 pages (test mode)
python3 translation_builder.py --extract --pages 5

# Extract 20 pages (standard)
python3 translation_builder.py --extract --pages 20

# Extract 50 pages (comprehensive)
python3 translation_builder.py --extract --pages 50

# Preview import (no merge)
python3 translation_builder.py --import translation_template.csv

# Import and merge
python3 translation_builder.py --import translation_template.csv --merge

# Verbose logging
python3 translation_builder.py --extract --pages 20 -v
```

---

## ⚡ Super Quick Test (5 minutes)

Want to see it in action first?

```bash
# 1. Extract 5 pages
python3 translation_builder.py --extract --pages 5

# 2. Open CSV
open translation_template.csv

# 3. Translate 10 terms marked ⚠️ NEW

# 4. Import
python3 translation_builder.py --import translation_template.csv --merge
```

---

## 🔧 Troubleshooting

### Script runs but no terms extracted?
Check the log:
```bash
tail -50 scraping.log
```

### Can't open CSV in Excel?
Try:
```bash
# Convert to UTF-8 if needed
iconv -f UTF-8 -t UTF-8 translation_template.csv > temp.csv
mv temp.csv translation_template.csv
```

### Want to re-extract?
```bash
# Just run extract again, it will overwrite
python3 translation_builder.py --extract --pages 20
```

---

## 💡 Pro Tips

### 1. Translate in Batches
Sort CSV by "Frequency" column (highest first) and translate top 100 terms first - these cover most of the content!

### 2. Use Find & Replace
If you have repeating patterns like "款" (model year), translate once and use Find & Replace in Excel.

### 3. Keep Notes
Use the "Notes" column to mark uncertain translations for later review.

### 4. Incremental Approach
You don't have to translate everything at once:
- Run #1: Translate brands/models only
- Run #2: Add specs
- Run #3: Add features
- Each time: `--import ... --merge`

### 5. Backup
The script auto-creates backups, but you can make your own:
```bash
cp ../../lipanmotorsapp/lib/translations.ts translations.ts.my-backup
```

---

## 📈 Scaling Strategy

### Day 1: Quick Coverage (5 pages)
```bash
python3 translation_builder.py --extract --pages 5
# Translate top 100 terms → 30 minutes total
```

### Day 2: Standard Coverage (20 pages)
```bash
python3 translation_builder.py --extract --pages 20
# Translate top 500 terms → 2-3 hours
```

### Day 3: Complete Coverage (50+ pages)
```bash
python3 translation_builder.py --extract --pages 50
# Translate remaining terms → Build comprehensive dictionary
```

---

## ✅ Success Checklist

- [ ] Ran extraction successfully
- [ ] Generated CSV file
- [ ] Opened CSV in Excel/Google Sheets
- [ ] Translated at least 50 NEW terms
- [ ] Saved CSV (UTF-8 encoding)
- [ ] Imported and merged translations
- [ ] Tested in frontend application
- [ ] No weird characters or broken translations

**All good?** Time to commit! 🎉

```bash
cd ../..
git add .
git commit -m "feat: add 500+ new Chinese→Russian translations via extraction tool"
git push
```

---

## 🆘 Need Help?

Check the full documentation:
```bash
cat README_TRANSLATIONS.md | less
```

View log for errors:
```bash
tail -100 scraping.log | less
```

---

*Simple, fast, and under your control* ✨
*No external APIs, no costs, just good translations* 🎯
