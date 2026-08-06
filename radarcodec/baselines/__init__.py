"""Classical codec baselines. Each exposes:

    compress_decompress(iq: complex64 [H,W], **params) -> (iq_hat, rate_bits_per_complex_sample)

Rate is measured, not nominal, wherever the format allows (encoded byte count);
BAQ rate is exact by construction.
"""

from radarcodec.baselines.baq import baq_codec
from radarcodec.baselines.jpeg2000 import jpeg2000_codec
from radarcodec.baselines.hevc import hevc_codec

CODECS = {
    "baq": baq_codec,
    "jpeg2000": jpeg2000_codec,
    "hevc": hevc_codec,
}
