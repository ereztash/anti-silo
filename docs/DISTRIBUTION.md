# Distribution and Publisher Trust

## Windows

The release workflow builds `Anti-Silo-Setup.exe` as the primary download and
keeps `Anti-Silo-Windows.zip` for a portable option. To sign both Windows
executables in production, configure Azure Artifact Signing and add these GitHub Actions
secrets:

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TRUSTED_SIGNING_ENDPOINT`
- `AZURE_CODE_SIGNING_NAME`
- `AZURE_CERT_PROFILE_NAME`

The workflow signs automatically only when every value is present. Never store
a certificate, password, or Azure credential in the repository. A verified
publisher identity improves SmartScreen reputation, but Microsoft notes that a
new publisher can still receive warnings until it has accumulated clean
download history.

## macOS

The macOS workflow produces `Anti-Silo-macOS.dmg`. For a Gatekeeper-friendly
release, configure these GitHub Actions secrets from an Apple Developer account:

- `APPLE_CERTIFICATE_P12_BASE64`
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_SIGNING_IDENTITY`
- `APPLE_ID`
- `APPLE_APP_SPECIFIC_PASSWORD`
- `APPLE_TEAM_ID`

When the certificate secrets are present, the app bundle is signed with a
Developer ID identity. When the notarization secrets are also present, the DMG
is submitted through `notarytool` and stapled after approval. Do not distribute
Apple certificates or passwords with the project.
