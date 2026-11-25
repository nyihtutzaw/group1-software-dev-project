# 1 · Feature workflow

[← Diagrams](README.md)

## Who does what

```mermaid
flowchart LR
    subgraph F1["F1 · Register"]
        A["👷 Developer<br/>project details + evidence<br/><i>files sealed: SHA-256 + own key</i>"]
    end
    subgraph F2["F2 · Boundary"]
        B["👷 Developer<br/>draws the land on the map"]
        B2{"overlap<br/>> 0.5 %?"}
    end
    subgraph F3["F3 · Verify (maker-checker)"]
        C["🗂️ Registry staff<br/>assigns a verifier"]
        D["🔍 Verifier<br/>checklist · risk rating · sign-off"]
        E["🗂️ Another staff<br/>approves + issues credits<br/><i>+ insurance buffer</i>"]
    end
    subgraph F4["F4 · Registry"]
        G["🌐 Anyone<br/>looks up a credit"]
        H["💳 Buyer<br/>receives + retires credits"]
    end
    subgraph F5["F5 · Audit"]
        I["🛡️ Admin<br/>hash-chained ledger<br/>+ role access"]
    end

    A --> B --> B2
    B2 -- "yes: blocked" --> B
    B2 -- "no: submit" --> C --> D
    D -- "changes requested" --> A
    D -- "signed off" --> E
    E -- "rejected" --> A
    E -- "issued" --> G --> H
    F1 & F2 & F3 & F4 -. "every action logged" .-> I
```

## Status of a project

```mermaid
stateDiagram-v2
    direction LR
    [*] --> draft: developer registers
    draft --> submitted: boundary OK → submit (evidence sealed)
    submitted --> draft: verifier requests changes
    submitted --> verified: verifier signs off → staff approves
    submitted --> draft: staff rejects
    verified --> issued: staff issues credits
    issued --> [*]
```

## Life of a credit

```mermaid
stateDiagram-v2
    direction LR
    [*] --> active: issued (serial range)
    [*] --> buffer: insurance buffer 10 / 15 / 20 %
    active --> held: staff allocates units to a buyer
    held --> retired: buyer retires for a claim
    retired --> [*]: shown publicly, can never be sold again
```

**Rules that make it trustworthy**

| | Rule |
|---|---|
| F1 | Evidence is write-once: a DB trigger blocks edits; personal data erased by destroying the file's key |
| F2 | Same land can't earn twice: PostGIS checks every boundary against all others |
| F3 | No one creates credits alone: verifier ≠ approver ≠ project owner |
| F4 | Retired units are locked; the public sees the claim, not the buyer's name |
| F5 | Each ledger entry stores the hash of the previous one: change one and the chain breaks |
