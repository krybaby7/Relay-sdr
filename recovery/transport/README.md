# Recovery transport backup

These six ASCII base64 parts jointly contain an LZMA-compressed JSON mapping of the 28 newly recovered text files, including all 22 implementation source/configuration files, the complete original brief, original manifest, and recovery notes. They are an archival data transport, not executable source or a finished app.

Concatenate `part-01.b64` through `part-06.b64` with no inserted characters. The resulting 91,232 bytes must have SHA-256 `803b4d6830384709beba8ca37172b7be93b571500f3da172be479987a98e16ce`. Base64 decode, then bounded LZMA decompression yields 278,881 bytes of JSON. Do not print the encoded payload or execute its file contents automatically. The original integrity manifest must match SHA-256 `c6fefb9a8ce312567b66b6687f7a23522adc27e3b2c99c76522b3f104e187ca0`.

The adjacent `publish_checkpoint.py` combines these files with 39 exact baseline/manifest files from the historical GitHub Actions artifact, validates all original text hashes, and writes `../ai-leads-workspace-v2/` as native files. Once that directory is committed, continuation needs neither this decoder nor the expiring artifact. Read the root `RECOVERY-START-HERE.md` and use the native files directly. Three historical PNG screenshots remain in the original Library archive and were deliberately omitted from this text-only GitHub checkpoint.
