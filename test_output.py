import json
from pathlib import Path

f = Path(r'd:\Github\RG_Greenwashing\data\esg_extracted.jsonl')
print("Reading file:", f)

with open(f, 'r', encoding='utf-8') as file:
    lines = file.readlines()
    print(f"Total lines: {len(lines)}")
    
    # Just take up to the first 6 lines
    for i, line in enumerate(lines[:6]):
        record = json.loads(line)
        print('================================================')
        print('File ' + str(i+1) + ': ' + str(record.get('pdf_filename')) + ' (' + str(record.get('model_used')) + ')')
        print('Status: ' + str(record.get('extraction_status')))
        print('Scope1: ' + str(record.get('ghg_scope1')))
        print('Scope2: ' + str(record.get('ghg_scope2')))
        print('Total Energy: ' + str(record.get('total_energy_consumption')))
        print('Recycled Waste: ' + str(record.get('waste_recycled_pct')))
        print('Vagueness: ' + str(record.get('vagueness_assessment')))
        print('Quantitative Richness: ' + str(record.get('quantitative_data_richness')))
        claims = record.get('claims', [])
        print('Claims count: ' + str(len(claims)))
        for j, c in enumerate(claims):
            print('  - Claim ' + str(j+1) + ': ' + str(c.get('claim_summary')))
            print('    Gap: ' + str(c.get('claim_evidence_gap')) + ' | Vagueness: ' + str(c.get('vagueness_piece')))
            evs = c.get('evidence_lines', [{}])
            ev_text = evs[0].get('quote') if evs else ''
            print('    Quote: ' + str(ev_text))
