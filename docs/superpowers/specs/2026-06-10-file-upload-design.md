# File Upload UI — Design Spec
**Date:** 2026-06-10
**Status:** Approved

---

## Overview

Replace the current file upload widgets in the Setup page with a reusable `FileDropZone` component. Files appear as a list of rows (icon, name, size, × remove). Clicking the dropzone appends files (qual docs) or replaces (xlsx). Users can add more files in subsequent clicks without losing previously selected files.

---

## Component: `FileDropZone`

### Props

```ts
interface FileDropZoneProps {
  label: string;
  accept: string;          // e.g. ".xlsx" or ".pdf,.png,.jpg,.jpeg"
  multiple: boolean;       // false = replace on new pick; true = append
  files: File[];           // controlled
  onChange: (files: File[]) => void;
}
```

### Behavior

- Dropzone area always visible at top of the widget
  - Empty state: icon + "Drop or click to add"
  - Files present: icon + "Add more" (only shown when `multiple=true`)
- Click dropzone → opens hidden `<input type="file">` with correct `accept` + `multiple`
- On file pick:
  - `multiple=false`: replace `files` with the single new file
  - `multiple=true`: append new files to existing list (deduplicate by name+size)
- File rows rendered below the dropzone:
  - File-type icon (spreadsheet for xlsx, document for pdf, image for jpg/png)
  - Filename (truncated at 40 chars with ellipsis if longer)
  - File size (formatted: bytes → KB → MB)
  - × button removes that file from the list
- No drag-and-drop required (click-only is sufficient)

### File type icons (lucide-react)

| Extension | Icon |
|-----------|------|
| `.xlsx`   | `FileSpreadsheet` |
| `.pdf`    | `FileText` |
| `.png` `.jpg` `.jpeg` | `Image` |
| other     | `File` |

---

## Setup Page Changes

Replace ref-based state with controlled state arrays:

| Before | After |
|--------|-------|
| `xlsxRef + xlsxName: string\|null` | `xlsxFiles: File[]` |
| `docsRef + docsCount: number` | `qualFiles: File[]` |

FormData built from state arrays:
```ts
form.append('xlsx', xlsxFiles[0]);
qualFiles.forEach((f) => form.append('qual_docs', f));
```

Run button disabled when `xlsxFiles.length === 0`.

---

## File Size Formatter

```ts
function formatSize(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${(bytes / 1_000).toFixed(0)} KB`;
  return `${bytes} B`;
}
```

---

## Files

| File | Action |
|------|--------|
| `dashboard/src/components/FileDropZone.tsx` | Create |
| `dashboard/src/pages/Setup.tsx` | Modify |

---

## Out of Scope

- Drag-and-drop
- File validation (type/size limits)
- Upload progress per file
