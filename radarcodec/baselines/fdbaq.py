"""FDBAQ accounting note (not a codec implementation).

Sentinel-1 L0 data on the ground has ALREADY been through onboard FDBAQ once —
what we decode is the FDBAQ reconstruction, not the pristine ADC output. Two
consequences for the study:

1. FDBAQ's own operating point (~3.4 bits/sample average in IW) is a documented
   reference rate, and fixed-rate BAQ at 2-4 bits (baq.py) brackets its
   rate-distortion behavior for curve purposes.
2. All codecs — classical and learned — start from the same FDBAQ-decoded
   samples, so comparisons are fair. Absolute distortion vs. "true raw" is
   unknowable FROM SENTINEL-1; the honest claim for S1 results is
   "re-compression of operationally-compressed raw data," which is itself the
   relevant spaceborne downlink scenario.
3. CORRECTION 2026-08-08 — this limitation is NOT general to public raw SAR,
   as an earlier version of this note implied. AFRL's publicly released
   Gotcha GMTI airborne phase history carries no BAQ signature (153,443
   distinct values in 153,600 samples; every value distinct within a block),
   i.e. it is effectively unquantized. Unencoded public raw data exists and
   is in hand — the caveat can be escaped by evaluating there, not merely
   disclosed. See reports/afrl_data_opportunities.md.

Reference: ESA S1 SAR Space Packet Protocol Data Unit spec (S1-IF-ASD-PL-0007),
which documents FDBAQ's Huffman-coded, SNR-adaptive quantization.
"""
