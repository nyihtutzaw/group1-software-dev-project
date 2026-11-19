// Tutorial walkthroughs, one per feature. Screenshots were taken from the running app with a
// fictional sample project ("Nam Wa Hillside Reforestation") taken through the whole flow.
// Mark positions are percentages of each screenshot. To refresh a screenshot, retake it at
// 1280 px wide and update its `size` and marks. See docs/features/F5-security-audit.md.
import type { Role } from '@/auth/types'

import f1Additionality from './images/f1-additionality.webp'
import f1Details from './images/f1-details.webp'
import f1Evidence from './images/f1-evidence.webp'
import f1Home from './images/f1-home.webp'
import f1Review from './images/f1-review.webp'
import f1Submitted from './images/f1-submitted.webp'
import f2Empty from './images/f2-empty.webp'
import f2Overlap from './images/f2-overlap.webp'
import f2Saved from './images/f2-saved.webp'
import f2Upload from './images/f2-upload.webp'
import f3Assign from './images/f3-assign.webp'
import f3Awaiting from './images/f3-awaiting.webp'
import f3Checklist from './images/f3-checklist.webp'
import f3Decision from './images/f3-decision.webp'
import f3Evidence from './images/f3-evidence.webp'
import f3History from './images/f3-history.webp'
import f3Issue from './images/f3-issue.webp'
import f3Queue from './images/f3-queue.webp'
import f4Allocate from './images/f4-allocate.webp'
import f4Credit from './images/f4-credit.webp'
import f4Grant from './images/f4-grant.webp'
import f4Retire from './images/f4-retire.webp'
import f4Retired from './images/f4-retired.webp'
import f4Search from './images/f4-search.webp'
import f5Ledger from './images/f5-ledger.webp'
import f5Login from './images/f5-login.webp'
import f5Roles from './images/f5-roles.webp'
import f5Users from './images/f5-users.webp'
import type { Tutorial } from './types'

const SAMPLES = '/tutorials/samples'

/**
 * The PDF user manual. It is generated from /system/tutorials/manual (Print → Save as PDF, A4)
 * and saved to frontend/public/tutorials/. Regenerate it whenever TUTORIALS change.
 */
export const MANUAL = {
  file: '/tutorials/CRVR-User-Manual.pdf',
  downloadName: 'CRVR-User-Manual.pdf',
  version: '1.0',
  date: '19 November 2026',
}

/** What each role does, for the manual's introduction. */
export const ROLE_GUIDE: { role: Role; duties: string }[] = [
  {
    role: 'developer',
    duties: 'Registers projects, draws their land boundaries and uploads evidence.',
  },
  { role: 'verifier', duties: 'Reviews assigned projects, completes the checklist and signs off.' },
  {
    role: 'registry_staff',
    duties:
      'Assigns verifiers, approves or rejects sign-offs, issues credits, grants buyer access.',
  },
  { role: 'buyer', duties: 'Traces credits to their evidence and retires the credits they hold.' },
  { role: 'admin', duties: 'Manages user accounts and has every registry staff permission.' },
]

const SAMPLE_PROJECT = 'Nam Wa Hillside Reforestation'

export const TUTORIALS: Tutorial[] = [
  {
    id: 'registration',
    feature: 'F1',
    title: 'Project registration & evidence',
    summary:
      'A developer registers a carbon-removal project in four steps, uploads evidence that is sealed on upload, and submits it for verification.',
    icon: 'submit',
    roles: ['developer'],
    sample: [
      { label: 'Project name', value: SAMPLE_PROJECT },
      { label: 'Methodology', value: 'VM0047 Reforestation' },
      { label: 'Crediting period', value: '2025 – 2044' },
      { label: 'Area', value: '368 ha' },
      { label: 'Est. removal', value: '52,000 tCO₂e' },
      {
        label: 'Baseline summary',
        value:
          'Degraded hillside cleared for maize in 2015; grass and scrub hold about 12 tC/ha. Native species will be planted across 368 ha.',
      },
    ],
    files: [
      {
        label: 'Land title (sample)',
        file: `${SAMPLES}/sample-land-title.pdf`,
        description: 'Upload in step 3 as “Land title”.',
      },
      {
        label: 'Additionality proof (sample)',
        file: `${SAMPLES}/sample-additionality-proof.pdf`,
        description: 'Upload in step 2 under “Proof”.',
      },
    ],
    steps: [
      {
        title: 'Start from Home',
        role: 'developer',
        path: '/',
        image: f1Home,
        size: [1280, 900],
        alt: 'Home page for a developer listing their projects with status chips',
        body: 'Sign in as a developer. Home lists your own projects with their status and a progress bar (registered → submitted → verified → issued). Open Submit to start a new registration.',
        marks: [
          { x: 0.9, y: 16.4, w: 17.4, h: 4, label: 'Submit opens the registration form' },
          {
            x: 21.9,
            y: 19.6,
            w: 75.6,
            h: 9.1,
            label: 'Your totals and the projects that need you',
          },
          {
            x: 21.9,
            y: 35.8,
            w: 75.5,
            h: 10.6,
            label: 'One row per project: open it to see details',
          },
          {
            x: 89.9,
            y: 38.4,
            w: 6.4,
            h: 2.5,
            label: 'Status chip: DRAFT, SUBMITTED, VERIFIED, ISSUED or OVERLAP',
            badge: 'tl',
          },
        ],
      },
      {
        title: 'Step 1 · Project details',
        role: 'developer',
        path: '/projects/new',
        image: f1Details,
        size: [1280, 800],
        alt: 'Registration form, step 1, filled in with the sample project',
        body: 'Fill in the project details from the sample. Only the name is needed to save a draft; the rest is needed before you can submit. Continue saves the draft and gives it a project code (CRVR-…).',
        marks: [
          {
            x: 21.9,
            y: 24.1,
            w: 75.6,
            h: 2.2,
            label: 'The four steps; you can come back to any of them',
          },
          { x: 23.2, y: 30.9, w: 73, h: 7.9, label: 'Project name' },
          { x: 23.2, y: 41.4, w: 73, h: 7.7, label: 'Methodology and crediting period' },
          { x: 23.2, y: 51.8, w: 73, h: 7.9, label: 'Area and estimated removal' },
          { x: 23.2, y: 62.2, w: 73, h: 12.9, label: 'Baseline: land use before the project' },
          { x: 60.1, y: 79.8, w: 37.4, h: 5.3, label: 'Continue saves the draft' },
        ],
        tip: 'Save draft keeps your work without moving on. Drafts are listed on Home.',
      },
      {
        title: 'Step 2 · Additionality',
        role: 'developer',
        image: f1Additionality,
        size: [1280, 839],
        alt: 'Additionality step with the reasoning filled in and a sealed proof file',
        body: 'Explain why the removals would not happen without carbon finance (at least 50 characters), then upload the sample additionality proof. Every file is sealed with a SHA-256 hash the moment it is uploaded and can never be changed or deleted.',
        marks: [
          {
            x: 23.2,
            y: 29.5,
            w: 73,
            h: 19.5,
            label: 'Additionality reasoning, at least 50 characters',
          },
          { x: 21.9, y: 62.1, w: 75.6, h: 16.6, label: 'Drop or pick the proof file' },
          { x: 21.9, y: 80.1, w: 75.5, h: 7.1, label: 'Uploaded file, marked SEALED' },
          { x: 60.1, y: 89.2, w: 37.4, h: 5, label: 'Continue to evidence' },
        ],
      },
      {
        title: 'Step 3 · Evidence and boundary',
        role: 'developer',
        image: f1Evidence,
        size: [1280, 831],
        alt: 'Evidence step with a sealed land title and a missing-boundary warning',
        body: 'Choose the type of evidence, then upload the sample land title. The Boundary box shows whether the land boundary is drawn and checked for overlaps; a project cannot be submitted without one. Follow “Draw the boundary” (see the Boundary tutorial).',
        marks: [
          {
            x: 23,
            y: 34.9,
            w: 73.3,
            h: 7.5,
            label: 'Type of evidence: land title, survey, photos, GPS…',
          },
          {
            x: 21.9,
            y: 45.2,
            w: 75.6,
            h: 14.3,
            label: 'Upload area (PDF, images, spreadsheets, GPS files)',
          },
          { x: 21.9, y: 61, w: 75.5, h: 7.2, label: 'Sealed evidence file' },
          { x: 21.9, y: 76.3, w: 75.6, h: 11, label: 'Boundary status, with a link to the map' },
        ],
      },
      {
        title: 'Step 4 · Review and submit',
        role: 'developer',
        image: f1Review,
        size: [1280, 800],
        alt: 'Review step showing the project facts and Ready to submit',
        body: 'Check the summary. If anything is missing, a red box lists it. When it says “Ready to submit”, submit the project. It is then sealed for independent verification and can no longer be edited.',
        marks: [
          { x: 22, y: 28.8, w: 75.5, h: 35.8, label: 'Everything you entered' },
          {
            x: 21.9,
            y: 66.5,
            w: 75.6,
            h: 7.6,
            label: 'Ready to submit, or a list of what is still needed',
          },
          { x: 60.1, y: 76.9, w: 37.4, h: 5.3, label: 'Submit project' },
        ],
      },
      {
        title: 'The submitted project',
        role: 'developer',
        image: f1Submitted,
        size: [1280, 1200],
        alt: 'Read-only project page with status SUBMITTED, sealed evidence and a clear boundary check',
        body: 'The project page is now read-only. Its status is SUBMITTED until registry staff assign a verifier (see the Verification tutorial). Verifiers, staff and admins see the same page.',
        marks: [
          { x: 21.9, y: 14.7, w: 7.6, h: 2, label: 'Status and progress' },
          { x: 21.9, y: 70.1, w: 75.6, h: 13.2, label: 'Sealed, read-only evidence' },
          { x: 21.9, y: 88.5, w: 75.6, h: 7.9, label: 'Boundary check result' },
        ],
      },
    ],
  },
  {
    id: 'boundary',
    feature: 'F2',
    title: 'Geospatial boundary & overlap detection',
    summary:
      'Draw or upload a project’s land boundary; it is checked against every registered boundary and overlaps above the tolerance are flagged.',
    icon: 'map',
    roles: ['developer', 'verifier', 'registry_staff', 'admin'],
    sample: [
      { label: 'Project', value: SAMPLE_PROJECT },
      { label: 'Boundary', value: 'Five-corner polygon near Nan, 367.7 ha' },
      { label: 'Overlap tolerance', value: '0.5% of the project area (per methodology)' },
    ],
    files: [
      {
        label: 'Boundary (GeoJSON sample)',
        file: `${SAMPLES}/sample-boundary.geojson`,
        description: 'Use with “Upload a file”. KML, KMZ and zipped shapefiles also work.',
      },
    ],
    steps: [
      {
        title: 'Open the map for your project',
        role: 'developer',
        path: '/boundary',
        image: f2Empty,
        size: [1280, 877],
        alt: 'Boundary page with a project chosen, the map of registered boundaries and draw and upload buttons',
        body: 'Open Map (or “Draw the boundary” from the registration form) and pick the project. The map shows every registered boundary in grey so you can see the neighbours.',
        marks: [
          { x: 23.2, y: 22.1, w: 73, h: 7.1, label: 'Project picker' },
          { x: 22, y: 32.6, w: 75.5, h: 52.5, label: 'Map with all registered boundaries' },
          {
            x: 21.9,
            y: 89.7,
            w: 37.4,
            h: 4.8,
            label: 'Draw boundary: tap each corner (works on a phone)',
            badge: 'tl',
          },
          {
            x: 60.1,
            y: 89.7,
            w: 37.4,
            h: 4.8,
            label: 'Upload a file: GeoJSON, KML, KMZ or shapefile',
          },
        ],
      },
      {
        title: 'Check it before saving',
        role: 'developer',
        image: f2Upload,
        size: [1280, 900],
        alt: 'Uploaded sample boundary on the map with the result Boundary drawn — no overlap',
        body: 'Upload the sample GeoJSON (or draw). The shape appears on the map and is checked straight away against every registered boundary. Nothing is saved yet: drag corners to adjust, then press Save boundary below the figures, or Discard changes.',
        marks: [
          { x: 22, y: 31.8, w: 75.5, h: 51.1, label: 'Your new shape; drag a corner to adjust it' },
          { x: 21.9, y: 87.1, w: 75.6, h: 7.5, label: 'Live overlap check result' },
        ],
        tip: 'Area, vertex count and the tolerance that applies are listed under the result.',
      },
      {
        title: 'Saved boundary',
        role: 'developer',
        image: f2Saved,
        size: [1280, 900],
        alt: 'Saved boundary on the map with layer and zoom controls',
        body: 'Once saved, the boundary is part of the registry and every later boundary is checked against it. The save is written to the audit ledger. Re-draw boundary replaces it while the project is still a draft.',
        marks: [
          { x: 22, y: 31.8, w: 75.5, h: 51.1, label: 'The saved boundary' },
          { x: 94, y: 37.3, w: 2.7, h: 3.8, label: 'Show or hide other boundaries' },
          { x: 94, y: 41.8, w: 2.7, h: 3.8, label: 'Zoom to this boundary', badge: 'br' },
        ],
      },
      {
        title: 'When an overlap is found',
        role: 'developer',
        path: '/boundary',
        image: f2Overlap,
        size: [1280, 1300],
        alt: 'Seeded project CRVR-0147 overlapping a neighbour, with the overlap alert and a flag to dispute',
        body: 'The seeded project CRVR-0147 overlaps its neighbour by 3.1%, above the 0.5% tolerance. The overlap is drawn in red and flagged. A flag blocks submission and issuance until registry staff resolve it; the developer can dispute it with a reason.',
        marks: [
          { x: 22, y: 22, w: 75.5, h: 35.4, label: 'The overlapping area, in red' },
          { x: 21.9, y: 60.3, w: 75.6, h: 6.7, label: 'Which project it overlaps and by how much' },
          { x: 22, y: 68, w: 75.5, h: 15.7, label: 'Area, overlap and the tolerance that applies' },
          {
            x: 21.9,
            y: 90.4,
            w: 75.6,
            h: 9,
            label: 'Overlap flag with Dispute (developer) or Resolve (staff)',
          },
        ],
      },
    ],
  },
  {
    id: 'verification',
    feature: 'F3',
    title: 'Verification workflow (maker-checker)',
    summary:
      'Registry staff assign a verifier, the verifier reviews and signs off, and a different staff member approves before credits are issued.',
    icon: 'verify',
    roles: ['registry_staff', 'verifier', 'admin'],
    sample: [
      { label: 'Project', value: `${SAMPLE_PROJECT} (submitted)` },
      { label: 'Verifier', value: 'Dr. Anna Weber' },
      { label: 'Due date', value: '18 Dec 2026' },
      { label: 'Reversal risk', value: 'Low · 10% buffer' },
      { label: 'Issued', value: 'Vintage 2026 · 4,800 tCO₂e (4,320 tradable + 480 buffer)' },
    ],
    files: [],
    steps: [
      {
        title: 'Assign a verifier',
        role: 'registry_staff',
        path: '/verify',
        image: f3Assign,
        size: [1280, 800],
        alt: 'Assign verifier tab with the sample project, Dr. Anna Weber and a due date',
        body: 'Sign in as registry staff, open Verify and the Assign verifier tab. Choose the submitted project, a verifier and a due date. Only submitted projects are listed.',
        marks: [
          { x: 55.3, y: 36.3, w: 9.4, h: 5.3, label: 'Assign verifier tab (staff and admin only)' },
          { x: 23.2, y: 53.3, w: 42.3, h: 7.7, label: 'Submitted project' },
          { x: 23.2, y: 63.6, w: 42.3, h: 7.7, label: 'Verifier' },
          { x: 23.2, y: 73.9, w: 42.3, h: 7.9, label: 'Due date; the queue flags it once overdue' },
          { x: 54.4, y: 85.9, w: 12.5, h: 5.3, label: 'Assign' },
        ],
      },
      {
        title: 'The verifier’s queue',
        role: 'verifier',
        path: '/verify',
        image: f3Queue,
        size: [1280, 800],
        alt: 'Verification queue for the verifier with the sample project marked NEW',
        body: 'Sign in as the verifier. Verify shows only the reviews assigned to you, oldest due date first, with overdue ones flagged. Open the project.',
        marks: [
          {
            x: 21.9,
            y: 22.1,
            w: 75.6,
            h: 10.2,
            label: 'Assigned, overdue and signed off this year',
          },
          { x: 21.9, y: 36.3, w: 75.6, h: 5.3, label: 'In progress, awaiting approval, approved' },
          { x: 22, y: 56.7, w: 75.5, h: 7.8, label: 'The new assignment' },
        ],
      },
      {
        title: 'Check the evidence',
        role: 'verifier',
        image: f3Evidence,
        size: [1280, 800],
        alt: 'Evidence and checks tab listing sealed files and the automatic boundary check',
        body: 'The Evidence & checks tab lists every sealed file with its hash, and the automatic checks (the boundary overlap check from F2). The summary on the right stays visible on every tab.',
        marks: [
          { x: 27.8, y: 25.9, w: 13.9, h: 5.3, label: 'Evidence & checks tab' },
          { x: 21.9, y: 34.8, w: 47, h: 26, label: 'Sealed evidence with SHA-256 hashes' },
          { x: 21.9, y: 68.1, w: 47, h: 9, label: 'Automatic checks' },
          { x: 75.6, y: 26, w: 21.9, h: 31.4, label: 'Summary' },
        ],
      },
      {
        title: 'Complete the checklist and sign off',
        role: 'verifier',
        image: f3Checklist,
        size: [1280, 1044],
        alt: 'Review tab with all five checklist items ticked, a verifier note and Low reversal risk',
        body: 'Tick each checklist item you confirmed, write a note and choose the reversal risk (it sets the buffer pool held back at issuance). Sign off sends it to registry staff; Request changes sends it back to the developer with your note.',
        marks: [
          { x: 22, y: 30, w: 51.7, h: 30.2, label: 'Checklist: confirm each item' },
          { x: 23.2, y: 63, w: 49.2, h: 9.9, label: 'Verifier note, seen by the developer' },
          { x: 23.2, y: 77.8, w: 49.2, h: 5.9, label: 'Reversal risk → buffer 10 / 15 / 20%' },
          { x: 21.9, y: 89, w: 25.6, h: 4, label: 'Request changes', badge: 'tl' },
          {
            x: 48.2,
            y: 89,
            w: 25.6,
            h: 4,
            label: 'Sign off (irreversible, written to the ledger)',
          },
        ],
      },
      {
        title: 'Awaiting approval',
        role: 'registry_staff',
        path: '/verify',
        image: f3Awaiting,
        size: [1280, 800],
        alt: 'Awaiting approval tab listing the signed-off sample project',
        body: 'Back as registry staff, the signed-off review is under Awaiting approval. The approver must be a different person from the verifier and the project owner; the system enforces this.',
        marks: [
          { x: 32.1, y: 36.3, w: 13.4, h: 5.3, label: 'Awaiting approval' },
          { x: 22, y: 48.8, w: 75.5, h: 7.8, label: 'Signed-off review' },
        ],
      },
      {
        title: 'Approve or reject',
        role: 'registry_staff',
        image: f3Decision,
        size: [1280, 1251],
        alt: 'Decision section with a rationale and Approve and Reject buttons',
        body: 'Read the checklist and note, write a rationale and approve or reject. Approval marks the project VERIFIED; it does not issue credits by itself.',
        marks: [
          { x: 23.2, y: 79.7, w: 49.2, h: 8.2, label: 'Rationale, at least 5 characters' },
          { x: 21.9, y: 92.8, w: 25.6, h: 3.4, label: 'Reject', badge: 'tl' },
          { x: 48.2, y: 92.8, w: 25.6, h: 3.4, label: 'Approve' },
        ],
      },
      {
        title: 'Issue the credits',
        role: 'registry_staff',
        image: f3Issue,
        size: [1280, 800],
        alt: 'API docs showing POST /api/verifications/projects/{project_id}/issue',
        body: 'Issuing is a deliberate staff action with the confirmed figures: country, vintage (within the crediting period and not in the future) and quantity. There is no button for it yet, so use the API docs (/api/docs) while signed in as staff. The buffer share is held back as a separate, non-tradable batch.',
        marks: [
          {
            x: 2.7,
            y: 10.2,
            w: 95,
            h: 5,
            label: 'POST /api/verifications/projects/{project_id}/issue',
          },
          { x: 87.7, y: 16.2, w: 8.5, h: 3.8, label: 'Try it out' },
          { x: 3.8, y: 50.5, w: 92.4, h: 14.6, label: 'Body: country, vintage, quantity' },
        ],
        tip: 'Sample body: {"country": "Thailand", "vintage": 2026, "quantity": 4800}',
      },
      {
        title: 'The full chain',
        role: 'registry_staff',
        image: f3History,
        size: [1280, 800],
        alt: 'History tab listing the assignment, sign-off and approval',
        body: 'The History tab shows who did what, and when: assignment, sign-off and approval. Each event is also sealed in the audit ledger.',
        marks: [
          { x: 42.1, y: 25.9, w: 7.8, h: 5.3, label: 'History tab' },
          { x: 23.6, y: 35.4, w: 48.8, h: 5, label: 'Assigned by staff' },
          { x: 23.6, y: 43.3, w: 48.8, h: 8.6, label: 'Signed off by the verifier' },
          { x: 23.6, y: 54.1, w: 48.8, h: 8.6, label: 'Approved by a different staff member' },
        ],
      },
    ],
  },
  {
    id: 'registry',
    feature: 'F4',
    title: 'Public registry & buyer transparency',
    summary:
      'Anyone can search issued credits and trace them to their evidence; staff grant buyers access and allocate credits; buyers retire them.',
    icon: 'registry',
    roles: ['registry_staff', 'buyer', 'admin'],
    sample: [
      { label: 'Search', value: 'Nam Wa' },
      { label: 'Buyer', value: 'Maya Lindqvist · buyer@crvr.local' },
      { label: 'Allocated', value: '40 tCO₂e' },
      { label: 'Retired', value: '10 tCO₂e' },
      { label: 'Beneficiary', value: 'Example Airways — 2026 staff travel' },
      { label: 'Reason', value: 'Offsetting 2026 business travel emissions' },
      { label: 'Reporting year', value: '2026' },
    ],
    files: [],
    steps: [
      {
        title: 'Grant a buyer access',
        role: 'registry_staff',
        path: '/buyer-access',
        image: f4Grant,
        size: [1280, 800],
        alt: 'Buyer access page with the sample project and buyer selected',
        body: 'Buyers only see the projects they are granted. As registry staff, open Access, choose the project and the buyer and grant access. Revoke removes it again; both are written to the ledger.',
        marks: [
          { x: 23.2, y: 27.8, w: 27.1, h: 7.7, label: 'Project with published credits' },
          { x: 23.2, y: 38.1, w: 27.1, h: 7.7, label: 'Buyer account' },
          { x: 23.2, y: 47.1, w: 27.1, h: 5.3, label: 'Grant access' },
          { x: 52.9, y: 22.1, w: 44.6, h: 31.8, label: 'Current grants, each with Revoke' },
        ],
      },
      {
        title: 'Search the public registry',
        role: 'buyer',
        path: '/registry',
        image: f4Search,
        size: [1280, 800],
        alt: 'Public registry search for Nam Wa showing the active batch and the buffer batch',
        body: 'Registry is public: no account needed. Search by project, serial or country. The sample project shows two batches: the tradable one (active) and the buffer pool (buffer), which cannot be sold or retired.',
        marks: [
          { x: 21.9, y: 22.3, w: 67.3, h: 4.8, label: 'Search: project, serial or country' },
          {
            x: 22,
            y: 40.2,
            w: 75.5,
            h: 15.5,
            label: 'Batches with serial, vintage, quantity and status',
          },
        ],
      },
      {
        title: 'Trace a credit',
        role: 'buyer',
        image: f4Credit,
        size: [1280, 1100],
        alt: 'Credit page with origin, verification and approval, history, and an intact ledger result',
        body: 'The credit page shows where the credits come from, who verified and approved them, and their history. Verify authenticity checks the tamper-evident ledger: the result says whether the chain is intact and shows the sealed issuance entry.',
        marks: [
          {
            x: 21.9,
            y: 19.3,
            w: 50.5,
            h: 24,
            label: 'Origin: project, country, methodology, vintage',
          },
          { x: 21.9, y: 47.8, w: 50.5, h: 32, label: 'Verification & approval references' },
          { x: 21.9, y: 83.7, w: 50.5, h: 6, label: 'Credit history' },
          {
            x: 74.1,
            y: 18.9,
            w: 23.4,
            h: 46.8,
            label: 'Verify authenticity and the evidence pack',
          },
        ],
      },
      {
        title: 'Allocate credits to a buyer',
        role: 'registry_staff',
        image: f4Allocate,
        size: [1280, 1456],
        alt: 'Holdings section with the allocate form filled in for the sample buyer',
        body: 'Staff see Holdings at the bottom of the credit page. Enter the buyer’s email and a quantity; the next contiguous unit range of serial numbers is allocated. The buyer must already have access to the project.',
        marks: [
          { x: 23.2, y: 85.7, w: 23.2, h: 4.3, label: 'Buyer email', badge: 'tl' },
          { x: 47.7, y: 85.7, w: 23.2, h: 4.3, label: 'Quantity (tCO₂e)' },
          { x: 23.2, y: 92.7, w: 47.7, h: 2.9, label: 'Allocate to buyer' },
        ],
      },
      {
        title: 'Retire credits',
        role: 'buyer',
        image: f4Retire,
        size: [1280, 800],
        alt: 'Retire credits dialog with a permanence warning and the sample retirement details',
        body: 'As the buyer, open the credit and press Retire next to your holding. Enter how many tonnes, the beneficiary, the reason and the reporting year. Retirement is permanent.',
        marks: [
          { x: 31.6, y: 21.6, w: 36.7, h: 11.4, label: 'Retirement is permanent' },
          {
            x: 31.6,
            y: 36.7,
            w: 36.7,
            h: 7.9,
            label: 'Quantity: part of a holding splits the range',
          },
          { x: 31.6, y: 49.8, w: 36.7, h: 7.9, label: 'Beneficiary, reason and reporting year' },
          { x: 50.4, y: 88.2, w: 18, h: 5.3, label: 'Retire permanently' },
        ],
      },
      {
        title: 'Public retirement record',
        role: 'buyer',
        image: f4Retired,
        size: [1280, 1400],
        alt: 'Credit page showing the public retirement record and the buyer’s remaining credits',
        body: 'The retirement is now public on the credit page (serial range, quantity, beneficiary and reason, never the buyer’s identity). Your credits shows the retired part as locked and the rest still held.',
        marks: [
          { x: 21.9, y: 73.5, w: 50.5, h: 9, label: 'Public retirement record' },
          {
            x: 21.9,
            y: 85.9,
            w: 50.5,
            h: 12.5,
            label: 'Your credits: retired (locked) and still held',
          },
        ],
      },
    ],
  },
  {
    id: 'security',
    feature: 'F5',
    title: 'Security & auditability',
    summary:
      'Sign-in with five roles, a tamper-evident audit ledger of every critical action, and admin tools for accounts and access.',
    icon: 'shield',
    roles: ['admin', 'registry_staff', 'verifier', 'buyer'],
    sample: [
      { label: 'Admin account', value: 'admin@crvr.local (local demo only)' },
      { label: 'Roles', value: 'Developer, verifier, registry staff, buyer, admin' },
    ],
    files: [],
    steps: [
      {
        title: 'Sign in',
        role: 'admin',
        path: '/login',
        image: f5Login,
        size: [1280, 825],
        alt: 'Sign-in page with email and password filled in',
        body: 'Everyone signs in with email and password. What you see next depends on your role. Locally the demo accounts are listed; on the hosted demo they are not.',
        marks: [
          { x: 58.4, y: 17.7, w: 28.6, h: 7.6, label: 'Email' },
          { x: 58.4, y: 27.9, w: 28.6, h: 7.6, label: 'Password' },
          { x: 57.1, y: 39.5, w: 31.3, h: 5.1, label: 'Sign in' },
        ],
        tip: 'Five failed sign-ins in 15 minutes block that account from that address for 15 minutes.',
      },
      {
        title: 'Read the audit ledger',
        role: 'admin',
        path: '/ledger',
        image: f5Ledger,
        size: [1280, 900],
        alt: 'Audit ledger with Chain intact and the newest entries from the sample walkthrough',
        body: 'Ledger lists every critical action, newest first: submissions, boundary saves, sign-offs, approvals, issuance, access grants, retirements. Each entry contains the hash of the one before, so any change to history breaks the chain and shows here.',
        marks: [
          { x: 21.9, y: 19.6, w: 75.6, h: 7.5, label: 'Chain integrity result' },
          {
            x: 23,
            y: 28.6,
            w: 73.3,
            h: 68,
            label: 'Entries: action, actor and role, time, short hash',
          },
        ],
      },
      {
        title: 'Manage user accounts',
        role: 'admin',
        path: '/admin/users',
        image: f5Users,
        size: [1280, 915],
        alt: 'Users page with the create account form and the list of accounts',
        body: 'Admins create accounts, change roles and deactivate or reactivate users from Users. Every change is written to the ledger. You cannot change your own role or deactivate yourself.',
        marks: [
          { x: 21.9, y: 19.3, w: 29.8, h: 60, label: 'Create an account' },
          { x: 23.2, y: 51.7, w: 27.1, h: 6.7, label: 'Role' },
          {
            x: 52.9,
            y: 19.3,
            w: 44.6,
            h: 75.4,
            label: 'Accounts: change role, deactivate, reactivate',
          },
        ],
      },
      {
        title: 'Check who can do what',
        role: 'admin',
        path: '/system/roles-access',
        image: f5Roles,
        size: [1280, 1300],
        alt: 'System, Role & Access page with the roles table and the page access matrix',
        body: 'System › Role & Access shows the five roles and exactly which pages and API endpoints each can use, read from the running code. It is read-only: access rules change only through a reviewed pull request.',
        marks: [
          { x: 0.9, y: 31.9, w: 17.4, h: 2.8, label: 'System menu (admin only)' },
          { x: 22, y: 25.5, w: 75.5, h: 24.7, label: 'Roles and responsibilities' },
          { x: 22, y: 55.4, w: 75.5, h: 42.2, label: 'Page access per role' },
        ],
      },
    ],
  },
]

export function tutorialById(id: string | undefined): Tutorial | undefined {
  return TUTORIALS.find((t) => t.id === id)
}
