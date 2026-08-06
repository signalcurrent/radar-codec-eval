"""FDBAQ accounting note (not a codec implementation).

Sentinel-1 L0 data on the ground has ALREADY been through onboard FDBAQ once —
what we decode is the FDBAQ reconstruction, not the pristine ADC output. Two
consequences for the study:

1. FDBAQ's own operating point (~3.4 bits/sample average in IW) is a documented
   reference rate, and fixed-rate BAQ at 2-4 bits (baq.py) brackets its
   rate-distortion behavior for curve purposes.
2. All codecs — classical and learned — start from the same FDBAQ-decoded
   samples, so comparisons are fair. But absolute distortion vs. "true raw" is
   unknowable from public data; say so explicitly in the report. The honest
   claim is "re-compression of operationally-compressed raw data," which is
   itself the relevant downlink scenario.

Reference: ESA S1 SAR Space Packet Protocol Data Unit spec (S1-IF-ASD-PL-0007),
which documents FDBAQ's Huffman-coded, SNR-adaptive quantization.
"""
