# 0010 — Personal data leaves sealed evidence by destroying its key

**Date:** 2026-11-19 · **Status:** Accepted · **Builds on:** [0009](0009-evidence-storage-backend.md)

## Context

Change request #45: a landowner found that an uploaded land-title scan shows their national ID
number and home address, and asks under data protection law that the personal data be removed.

The system was built so that this is impossible. Evidence is write-once three times over — no
update or delete in the API or the service, a storage interface with no delete method, a
PostgreSQL trigger that rejects UPDATE and DELETE on `evidence_files` — and in production the
bucket carries a retention lock that refuses deletion even to a project owner with console
access. That is not an oversight to work around; it is the reason buyers are expected to trust
the registry at all.

So the request and the design are in direct conflict, and only three kinds of answer exist:

1. **Delete the file.** Honest about the law, dishonest about the registry: it breaks the
   guarantee every credit depends on, and the retention lock makes it impossible anyway.
2. **Refuse, and restrict access instead.** Honest about the registry, but the personal data is
   still in the system, so it does not answer the request.
3. **Keep the file and make its content unreadable.** Needs the content to have been encrypted
   before it was sealed.

A fourth problem sits underneath all three: erasing the whole file also destroys the evidence
the project's credits rest on. A verifier who opens the project later finds a hole.

## Decision

- **Every evidence file is encrypted with its own AES-256-GCM key before it is sealed.** The
  ciphertext goes to the write-once backend; the key goes to `evidence_keys`, an ordinary table
  with no trigger and `ON DELETE CASCADE`.
- **Erasure destroys the key, and nothing else.** The ciphertext stays in the bucket under its
  retention lock, the `evidence_files` row is untouched, and the ledger entry keeps the original
  SHA-256. What the file was, who uploaded it, when it was sealed and what it hashed to all
  remain provable. The bytes become unrecoverable.
- **A redaction is uploaded first, and recorded as the replacement.** `evidence_erasures` holds
  the reason, who erased it, and the id of the redacted file uploaded in its place. A download of
  an erased file answers **410 Gone** with the reason and a pointer to the replacement, so a
  verifier sees a deliberate erasure rather than a missing file.
- **`evidence_erasures` is append-only**, with the same kind of trigger as `evidence_files`: the
  record that content was destroyed on purpose must be as permanent as the evidence it describes.
- **Admin only.** Erasure is a data-protection decision, not a correction a developer makes to
  their own project, and it cannot be undone.
- **Keys never repeat.** One key per file, so erasing one file cannot affect another.

## Consequences

- The data subject's request is answered: the national ID and address are unreadable to everyone,
  including us, with no key left anywhere to recover them.
- The registry's guarantee survives intact. Nothing was updated, nothing was deleted, and the
  hash chain still verifies. An auditor can still see that evidence existed, what it hashed to,
  and that it was erased on a stated date for a stated reason.
- GCM authenticates as well as encrypts, so a ciphertext altered in the bucket now fails to
  decrypt instead of returning wrong bytes. Downloads answer 409 in that case.
- **Lost keys are indistinguishable from erasures in effect, but not in the record.** A missing
  key with no erasure row answers 404 "its key is missing", not 410. A key lost by accident is a
  fault to investigate, not a data-protection decision to report — conflating them would let a
  bug look like a lawful erasure.
- `evidence_keys` is now the most sensitive table in the database. A database backup holds the
  keys next to the ciphertext, so the backup is as sensitive as the evidence. Moving the keys to
  Cloud KMS would separate them; it is not done here and is listed as an open question in F1.
- Files sealed before this change are stored in clear text and have no key, so they cannot be
  crypto-erased. There is no such evidence in the pilot. A production system would re-encrypt
  during a maintenance window before locking the retention policy.
- Encryption is one-shot over the whole file rather than streamed, so a 50 MB upload is held in
  memory twice while it is sealed. Acceptable at the evidence size limit and the Cloud Run memory
  we run with; it would need a streaming cipher before the limit is raised.
