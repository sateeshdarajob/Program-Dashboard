# Offer letter update (dummy test doc)

Updates `candidate_fad9.pdf` from the uploaded employment letter:

1. **Designation:** `Manager - Program Management` → `Sr.Technical Program Manager - Program Management`
2. **Emoluments:** `INR 36,00,000/-` → `INR 47,00,000/-`
3. **Annexure I (page 9):** salary breakup scaled with the same mapping used for 36L

## Salary mapping (same structure as 36,00,000)

| Rule | Mapping |
| --- | --- |
| Monthly CTC | `round(Annual CTC / 12)` → `3,91,667` |
| Basic | same % of CTC as original (`~36.131%`) → `1,41,513` |
| HRA | `60%` of Basic → `84,908` |
| Employer PF | `12%` of Basic → `16,982` |
| Gratuity | `6.5%` of Basic → `9,198` |
| LTA | same ratio to Basic as original → `26,773` |
| Conveyance (Flexi) | residual so monthly components sum to CTC → `1,12,293` |
| Annual component | `monthly × 12` (CTC/Gross annual stated as `47,00,000`) |

## Regenerate

```bash
python3 update_offer_letter.py candidate_fad9_original.pdf candidate_fad9.pdf
```

Requires `pymupdf` and Noto Sans fonts at `/usr/share/fonts/truetype/noto/`.
