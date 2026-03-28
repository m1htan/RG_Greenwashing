# Task: Gemini 2.5-Pro PDF Extraction Pipeline

## Planning
- [x] Analyze PDF content structure and extractable fields
- [x] Analyze file sizes and distribution (823 files, 12.3GB total)
- [x] Write implementation plan
- [x] Get user approval on plan

## Implementation
- [/] Update [config/.env](file:///d:/Github/RG_Greenwashing/config/.env) with Gemini API key placeholder
- [/] Update [requirements.txt](file:///d:/Github/RG_Greenwashing/requirements.txt) with new dependencies
- [ ] Create `scripts/extract_esg_fields.py` — main extraction script
  - [ ] Gemini API client setup
  - [ ] PDF upload + extraction prompt
  - [ ] JSON response parsing to flat row
  - [ ] CSV output writing
  - [ ] Resume/skip-existing logic
  - [ ] Rate limiting + error handling
  - [ ] Progress logging
- [ ] Create `config/esg_extraction_prompt.txt` — reusable prompt template

## Verification
- [ ] Test with 1-2 sample PDFs manually
- [ ] Verify CSV output structure
- [ ] Verify resume/skip-existing works
- [ ] Run on small batch (~10 PDFs)
