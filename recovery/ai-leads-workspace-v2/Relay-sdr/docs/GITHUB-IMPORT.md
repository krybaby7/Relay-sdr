# GitHub source import

This repository imports the Relay SDR v0.1.0 application source, browser assets, tests, configuration template, and documentation from the original conversation ZIP. It does not include credentials, runtime data, or a deployment.

The five original preview PNGs under `docs/screenshots/` were not uploaded in this import. They remain in `Relay-SDR-v0.1.0.zip` supplied in the conversation. They are documentation captures, not application runtime assets.

`SHA256SUMS.txt` is the unmodified original archive manifest, including those five screenshots. For this source import, GNU coreutils can check the original files that are present with:

```bash
sha256sum --ignore-missing -c SHA256SUMS.txt
```

The original verification report and saved test outputs are retained as historical release records. This import alone is not a new test run and does not establish live OpenAI or Twilio operation.
