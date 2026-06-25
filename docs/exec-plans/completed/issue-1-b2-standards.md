# Issue 1: B2 Standards Alignment

## Scope

Resolve the quality-keeper B2 standards failure from issue #1.

## Changes

- Standardized B2 credentials on `B2_APPLICATION_KEY_ID`,
  `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`, and optional
  `B2_PUBLIC_URL_BASE`.
- Derived the B2 S3 endpoint from `B2_REGION` instead of accepting a separate
  endpoint environment variable.
- Updated the boto3 S3 client user agent to include `(backblaze-b2-samples)`.
- Added regression tests for endpoint derivation and S3 client configuration.

## Verification

- `pnpm lint:api`
- `pnpm test:api`
- `pnpm check:structure`
