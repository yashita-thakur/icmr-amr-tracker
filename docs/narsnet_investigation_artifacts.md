# NARS-Net V3 investigation — retained artifacts

Untracked scratch record from the V3 investigation phase. Not part of the
dataset or the build. Kept so the fetched source material and the 2024 site
roster are not lost when the session scratchpad is cleared.

## 1. The 8 NARS-Net annual report PDFs

All eight were fetched from NCDC on 2026-09-01, verified to be valid PDFs
(`%PDF-` header), and text-/table-extracted with the repo's own `.venv`
pdfplumber (0.11.10). Cite by **reporting period**, not by the cover-page year
(the 2019-data edition's cover says "AMR Annual report -2020"; the 2020-data
edition's cover says "Annual Report-2021").

| Reporting period | Local filename | NCDC URL | SHA-256 |
|---|---|---|---|
| Jan–Dec 2017 | `narsnet_2017.pdf` | https://ncdc.mohfw.gov.in/uploads/pdf/amr39.pdf | `0070d1b36c314a235bf1b744170e8e7bc95655db064c57cbb485f8301ffff6b2` |
| Jan–Dec 2018 | `narsnet_2018.pdf` | https://ncdc.mohfw.gov.in/uploads/pdf/amr38.pdf | `a09987ec16fe77b10438cd3340bf1c2c4aae1cd330ba0601b33231453693836f` |
| Jan–Dec 2019 | `narsnet_2019.pdf` | https://ncdc.mohfw.gov.in/uploads/pdf/amr37.pdf | `6056c836ea739dd02cfc0af39295a49c41bffd4da31cfe302085b53a19fd3097` |
| Jan–Dec 2020 | `narsnet_2020.pdf` | https://ncdc.mohfw.gov.in/uploads/pdf/amr36.pdf | `159858e8674efc6ee4c800a34ef494ddc7d3e88a920f54e4c867a65aba2ec9ad` |
| Jan–Dec 2021 | `narsnet_2021.pdf` | https://ncdc.mohfw.gov.in/uploads/pdf/amr35.pdf | `976a985af372cbd2f59a5afb7381a6a68edb0bcca33e95b98bc0b3deea306785` |
| Jan–Dec 2022 | `narsnet_2022.pdf` | https://ncdc.mohfw.gov.in/uploads/pdf/amr34.pdf | `5d3734e4dbcc32fc4070e0b85ae0e164ff4fbcc90df4813ffc5c632a130867e7` |
| Jan–Dec 2023 | `narsnet_2023.pdf` | https://ncdc.mohfw.gov.in/uploads/pdf/amr32.pdf | `1c5c9fbe3c6320c9b1e31852f0892aecf705d10c243fbb4505551b4032ebca56` |
| Jan–Dec 2024 | `narsnet_2024.pdf` | https://ncdc.mohfw.gov.in/uploads/pdf/amr30.pdf | `48b4bdf8f7f8706a110f9f8b3b95aa792b813b18ecedc7b1bb94b49c8a63c4e5` |

### Local save path

The 8 PDFs, the per-page text dumps (`text_2017.txt` … `text_2024.txt`), the
extraction helper scripts, and the rendered image of the 2021 E. coli table
were saved under:

```
C:\Users\yashi\AppData\Local\Temp\claude\C--Users-yashi\159f0dcb-e4a6-40d6-b731-608abc4a34eb\scratchpad\narsnet\
```

This is a session scratchpad and will not survive indefinitely. When V3 work
begins, re-fetch from the URLs above, confirm the SHA-256 values match, and
archive each PDF (Wayback or Zenodo) — NCDC has migrated these URLs twice
before.

## 2. NARS-Net 2024 edition — Annexure I, full site list (entries 1–54)

Transcribed verbatim from `narsnet_2024.pdf` (Annexure I, pp. 57–58), including
the original spelling and the trailing `*` markers.

Header note as printed:

> List of NARS-Net sites that contributed AMR surveillance data for priority
> bacterial pathogens for the period Jan 2024 to Dec 2024. AMR Surveillance
> Data for fungal pathogens is from the sites with star in the list below.

1. BJ Medical College, Ahmedabad, Gujarat*
2. BJ Medical college, Pune, Maharashtra
3. Government Medical College and Hospital, Chandigarh*
4. GSVM Medical College, Kanpur, Uttar Pradesh*
5. Lady Hardinge Medical College and Associated hospitals, Delhi*
6. Mysore Medical college, Mysuru, Karnataka
7. SMS Medical College, Jaipur, Rajasthan*
8. Vardhman Mahavir Medical college and SJ Hospital, Delhi
9. Government Medical College, Thiruvananthapuram, Kerala*
10. KAPV. Government Medical College, Tiruchirappalli, Tamil Nadu*
11. Gauhati Medical College and Hospital, Guwahati, Assam*
12. NEIGRIHMS, Shillong, Meghalaya*
13. MGM College and Hospital, Indore, Madhya Pradesh
14. Indira Gandhi Medical College, Shimla, Himachal Pradesh*
15. Govt. Medical College and Hospital, Aurangabad, Maharashtra*
16. Osmania Medical College, Hyderabad, Telangana*
17. Guntur Medical College, Guntur, Andhra Pradesh
18. Agartala Govt. Medical College, Agartala, Tripura
19. SCB Medical College & Hospital, Cuttack, Odisha
20. Government Medical College & Hospital, Jammu, Jammu and Kashmir*
21. Pandit Bhagwat Dayal Sharma, Post Graduate Institute of Medical Sciences (PGIMS) Rohtak, Haryana*
22. Rajendra Institute of Medical Sciences, Ranchi, Jharkhand*
23. Indira Gandhi Institute of Medical Sciences, Sheikpura, Patna, Bihar*
24. Government Medical College, Haldwani, Uttarakhand*
25. Pt. Jawaharlal Nehru Memorial Medical College, Raipur, Chhattisgarh*
26. Gandhi Medical College, Bhopal, Madhya Pradesh*
27. Calcutta School of Tropical Medicine, Kolkata, West Bengal*
28. GMERS Medical College and Civil Hospital, Valsad, Gujarat
29. Lala Lajpat Rai Memorial (LLRM) Medical College, Meerut, Uttar Pradesh
30. Coimbatore Medical College & Hospital, Coimbatore, Tamil Nadu
31. Maulana Azad Medical College (MAMC) and Associated Hospitals, Delhi*
32. Sardar Patel Medical College (SPMC) and Hospital, Bikaner, Rajasthan*
33. Karnataka Institute of Medical Sciences (KIMS), Hubli, Karnataka*
34. Indira Gandhi Medical College & Research Institute (IGMC & RI) Puducherry
35. NAMO Medical Education and Research Institute (MERI), Silvassa, Dadra & Nagar Haveli*
36. Goa Medical College & Hospital, Bambolim, Goa
37. STNM Medical College & Hospital, Gangtok, Sikkim*
38. Government Medical College, Patiala, Punjab
39. Zoram Medical College, Falkawn, Mizoram*
40. Andaman & Nicobar Islands Institute of Medical Sciences (ANIIMS), Andaman & Nicobar Islands
41. Jawahar Lal Nehru Institute of Medical Sciences (JNIMS), Manipur
42. Govt. Medical College Srinagar, Jammu and Kashmir
43. Rabindranath Tagore Medical College, Udaipur, Rajasthan
44. Andhra Medical College, Vishakhapatnam, Andhra Pradesh
45. Vijayanagar Institute of Medical Sciences Ballari, Karnataka*
46. Burdwan Medical College & Hospital Burdwan, West Bengal*
47. Grant Govt Medical College & Sir JJ Group of Hospitals, Byculla, Mumbai
48. Pt. Raghunath Murmu Medical College & Hospital Baripada, Odisha
49. Government Medical College, Thrissur, Kerala
50. S.V medical College, Tirupati, Andhra Pradesh
51. Jorhat Medical College and Hospital, Jorhat, Assam
52. University College of Medical Sciences & GTB Hospital, Delhi
53. Pandit Dindayal Upadhyay Medical College, Rajkot, Gujarat
54. Netaji Subash Chandra Bose Medical College, Jabalpur, Madhya Pradesh

Notes:
- 54 sites submitted bacterial AMR data for 2024; the NARS-Net roster stood at
  60 laboratories as of March 2025.
- 28 sites (those marked `*`) also submitted Candida bloodstream isolates for
  the fungal AMR section, new in the 2024 edition.
- Entry 42, "Govt. Medical College Srinagar", is the same-city / different-
  institution counterpart to SKIMS (an ICMR-AMRSN centre, not on NARS-Net).

## 3. Corrections to narsnet_v3_research.md

EUCAST. The research file states "EUCAST never used" / "CLSI in every edition, EUCAST never". The correct position is narrower: EUCAST is named exactly once, in the 2023 edition's methods text, as one of the "International Guidelines such as CLSI ... and EUCAST documents" that the NARS-Net standard operating procedures are built on. It is not used to interpret results. Every edition that names an interpretive basis at all names CLSI, and only CLSI. So "EUCAST is never the interpretive standard" is right; "EUCAST never appears" is not.

The "CLSI document M02 and M100" sentence. The research file attributes the citation "CLSI document M02 and M100 ... only for colistin broth microdilution" to the 2018 edition. Full-text search of all eight editions shows the 2018 edition contains no occurrence of "CLSI" at all — it names no interpretive standard. That exact "CLSI document M02 and M100" phrasing first appears in the 2019 edition and recurs in 2020, 2021, 2022 and 2023. The 2024 edition is the only one to name a CLSI edition ("M100 34th Ed.").

The reconciliation window. The research file says the repository's printed-percentage-versus-counts reconciliation check is possible for the "2019-2021 window" because only those editions print a numerator. Narrow this to: 2019 and 2020 fully; 2021 only for S. aureus and, for E. coli, only the Pus Aspirate and OSBF specimen columns. The 2021 E. coli Blood "Number Resistant" sub-column is corrupt in the printed source (rows where Number Resistant exceeds Number Tested, and rows whose Number Resistant implies a percentage far from both the printed percentage and the corroborating figure), and two 2021 E. coli Urine cells (piperacillin/tazobactam, trimethoprim/sulfamethoxazole) print Number Resistant equal to Number Tested with a percentage that is not 100. This was confirmed by rendering the page to an image.

The E. coli panel overlap denominator. The research file carries a provisional "7 of the 8 AMRSN drugs named" for E. coli. Against the repository's actual ten-drug Enterobacterales CANONICAL_PANEL the figure is 7 of 10 for the 2021-2024 editions (5 of 10 for 2017, 4 of 10 for 2018-2020). The two AMRSN Enterobacterales drugs that are never in any NARS-Net E. coli panel are cefazolin and levofloxacin; a third, ceftazidime, appears in a NARS-Net E. coli table in 2017 only (and in the 2019 E. coli figures but not the 2019 table).
