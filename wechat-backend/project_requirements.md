# Project Requirements: WeChat MiniApp for Retail Issue Management

## 1. Backend & Data Schema (SQLite)

The backend should manage a table named `issues` with the following fields:

| Field Name | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | Integer | Primary Key, Auto-increment | Unique ID for each issue. |
| `submit_date` | Date | NOT NULL | Date when the issue was reported. |
| `store` | String | NOT NULL | Format: "4 digits - Store Name". |
| `content` | String(500) | NOT NULL | Description of the issue. |
| `issue_photo` | String | NOT NULL | File path/URL of the issue photo (jpg/png). |
| `fix_photo` | String | Nullable | File path/URL of the rectification photo. |
| `fix_date` | DateTime | Nullable | Timestamp when the rectification was submitted. |
| `status` | String | Default: 'pending' | Status: 'pending' (if fix_photo is NULL) or 'completed'. |

---

## 2. Frontend Structure (Landing Page)

The landing page should feature three primary navigation buttons:

1. **Issue Submission**
2. **Rectification Feedback**
3. **Status Tracking**

---

## 3. Page Logic & UI Requirements

### A. Issue Submission Page

* **Inputs:**
* **Submission Date:** Date picker (Default: Current Date).
* **Store:** Dropdown/Picker (Pre-filled list of "4 digits - Name").
* **Issue Content:** Multi-line text input with a "Voice-to-Text" button.
* **Issue Photo:** Camera/Album upload control. Display thumbnail after upload.


* **Logic:**
* "Submit" button is disabled if any required field is empty.
* Upon successful submission, stay on the page but **retain** the selected "Submission Date" and "Store" values for the next entry.



### B. Rectification Feedback Page

* **Workflow:**
1. User selects a **Store**.
2. User clicks **"Get Pending Issues"**.
3. App retrieves issues for that store where `fix_photo` is NULL.


* **Display:**
* Show a list/table of pending issues: `[Date] | [Content] | [Issue Photo Thumbnail] | [Upload Fix Photo Button]`.
* **In-place Update:** Uploading a rectification photo should only refresh that specific row, not the entire page.


* **Submission:**
* A global **"Submit All Rectifications"** button at the bottom.
* Updates the database for all rows that have a new `fix_photo`.
* Automatically sets `fix_date` to the current system time for updated records.



### C. Status Tracking Page

* **Filters:**
* **Store:** Specific store or "All".
* **Status:** "Pending", "Rectified", or "All".


* **Action:**
* **"Download Issue List"** button: Generates a `.xlsx` file based on filters.
* **Share Function:** Provide a button to forward the generated Excel file to a WeChat contact or group.


* **Excel Export Content:**
* Fields: ID, Submit Date, Store, Content, Issue Photo (Link/Path), Fix Photo (Link/Path), Fix Date.



---

## 4. Technical Constraints (Vibe Coding Focus)

* **Backend:** FastAPI with SQLAlchemy and SQLite.
* **Storage:** Local file system for images (path stored in DB).
* **Static Files:** Backend must serve the `uploads/` folder as a static directory.
* **Excel Generation:** Use `pandas` or `openpyxl` for exporting data.
