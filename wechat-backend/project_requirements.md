
# Project Requirements: MD-Trace Store Inspection System (H5)

## 1. Project Overview
A mobile-first web application designed for retail store staff to report issues, track statuses, submit rectification proof, and export data. This is a browser-based H5 application (not a WeChat Mini-program) optimized for mobile browsers and older Android devices.

## 2. Tech Stack
* **Frontend**: Vue 3 (Composition API), Vite, Vant UI (Mobile Component Library), Vue Router.
* **Backend**: Python 3.12+, FastAPI, SQLAlchemy.
* **Database**: SQLite (`issues.db`).
* **Infrastructure**: Ubuntu Server, Nginx (Reverse Proxy), Gunicorn (Production Server), Systemd.
* **Version Control**: Git/GitHub (with strict `.gitignore` for `__pycache__`, `node_modules`, `dist`, `data/`, and `uploads/`).

## 3. Data Schema (SQLite)
The backend manages a table named `issues` with the following schema:

| Column Name    | Type     | Constraints                 | Description                                                    |
| :------------- | :------- | :-------------------------- | :------------------------------------------------------------- |
| `id`           | INTEGER  | Primary Key, Auto-increment | Unique ID for each issue.                                      |
| `submitted_at` | DATETIME | NOT NULL                    | Timestamp when the issue was reported.                         |
| `store`        | VARCHAR  | NOT NULL                    | Format: "4 digits - Store Name".                               |
| `content`      | TEXT     | NOT NULL                    | Detailed description of the issue.                             |
| `issue_photo`  | VARCHAR  | NOT NULL                    | **Relative path** (e.g., `/uploads/xxx.jpg`). No absolute IPs. |
| `fix_photo`    | VARCHAR  | Nullable                    | Relative path of the rectification photo.                      |
| `fix_date`     | DATETIME | Nullable                    | Timestamp when the rectification was submitted.                |
| `status`       | VARCHAR  | Default: 'pending'          | Current status ('pending' or 'completed').                     |

---

## 4. Frontend Requirements & UI Logic

### 4.1 Navigation & Landing Page
* **Three Primary Buttons**: Issue Submission, Rectification Feedback, Status Tracking.
* **Sticky Header**: Must include a prominent "Back/Home" button on the left.
    * **Styling**: Bright orange (`#ff9800`) icon (`wap-home-o`) and text ("返回").
    * **Font Size**: 12px-14px for the "返回" text.
    * **Context**: This is critical for users on older Android devices who intuitively look for a visual back button rather than using gesture/navigation bars.

### 4.2 Page-Specific Logic
* **Issue Submission**:
    * **Inputs**: 
	    * Date picker (default: today)
	    * Store dropdown (Pre-filled list of "4 digits - Name")
	    * Multi-line text (Voice-to-Text support)
	    * Photo upload (Pop up Camera/Album option selection. Display thumbnail after upload.).
    * **Logic**: 
	    * "Submit" button is disabled if any required field is empty.
	    * "Retention": After submission, stay on the page but **retain** the selected "Date" and "Store" values to speed up bulk entries.

* **Rectification Feedback**:
    * **Workflow**: 
	    1. User selects a **Store** (a dropdown, pre-filled list of "4 digits - Name", like in the Issue Submission page)
	    2. User clicks **"Get Pending Issues"** button
	    3. App retrieves issues for that store where `status` is pending.
	- **Display**：
		- Show a list/table of pending issues in **cards**: `[ID](included but invisible) | [Date] | [Content] | [Issue Photo Thumbnail] | [Upload Fix Photo Button]`.
	- **In-place Update**: Uploading a rectification photo should only refresh that specific row (to display the thumbnail of the rectificaiton photo), but not the entire page.
	- **Visual Feedback (Card Background)**: When a rectification photo is successfully uploaded for a pending issue, the background color of that specific issue card must change (e.g., to a light green `#f0f9eb`) to visually signal that the record is ready for final submission.
	- **Bulk Submission (Floating Action Button)**: *
		- **Shape/Position**: A prominent, round Floating Action Button (FAB) at the bottom-right of the screen. 
		- **Text**: "确认提交" (Confirm Submission). 
		- **Interactive Logic** : The button must remain **Disabled/Inactive** (greyed out) if not any rectification photo has been uploaded for any issue in the current view. It becomes **Active** (primary color) only when at least one change is detected. 

    
* **Status Tracking**:
    * **Filters**: 
	    * Store (Pre-filled list of "4 digits - Name", default: "全部门店")
	    * Status ("全部", "待整改", "已整改"， defaut to "待整改").
    * **Constraint**: The "All Stores" option must display as **"全部门店"** in Chinese, not "All".
    * **Action**: **"Download Issue List"** button: Generates a `.xlsx` file based on filters.
    * **Excel Export Content:** Fields should include: 
	    * ID (问题编号): `id`
	    * Submitted At (提交时间): `submitted_at`
	    * Store (门店): `store`
	    * Status (问题状态): `status`
	    * Content (问题描述): `content`
	    * Issue Photo (问题照片)：thumbnail of resized issue photo (from `./uploads`), not the relevant path from `issue_photo`
	    * Fix Photo (整改照片): thumbnail of resized rectification photo (from `./uploads`), not the relevant path from `fix_photo`
	    * Fix Date (整改时间): `fix_date`


- **Data Maintenance (Hidden UI & Safety Controls)**: 
	* **Trigger**: Triggered by the `.maintenance-trigger` element. 
	* **Warning Tag/Card**: At the top of the maintenance view, display a prominent warning message: *"⚠️ 警告：此操作将永久删除指定日期之前的问题记录及对应的图片文件，且无法恢复。请谨慎操作！"* 
	* **Cutoff Date Picker**: Select a date; records before this date will be targeted. 
	* **Status Filter**: Choose scope: "已整改" (Completed only) or "全部" (All records before the date). 
	* **Final Confirmation Pop-up**: Clicking the delete button must trigger a final modal/dialog: 
		* **Title**: "确认删除" 
		* **Message**: *"此操作不可逆，确定要永久删除 [Selected Date] 之前的 [Selected Status] 数据及图片吗？"* 
		* **Buttons**: Custom "确定删除" (Danger style) and "取消".

### 4.3 Image Upload Constraint
* **`van-uploader`**: **DO NOT** use the `capture="camera"` attribute. Only use `accept="image/*"`. This prevents browsers from forcing a camera-only view and allows users to choose between the camera and the photo gallery.

---

## 5. Backend Logic & Image Processing Pipeline

### 5.1 The "Golden" Image Pipeline
To ensure high-resolution photos are handled correctly and watermarks remain legible, the pipeline **must** follow this order:
1.  **Resize/Compress FIRST**: Downscale and compress the image to ensure the file size is **under 1MB**.
2.  **Add Watermark SECOND**: Apply the watermark *after* the image is at its final resolution.
    * **Font**: Explicitly load `/usr/share/fonts/truetype/wqy/wqy-microhei.ttc` for CJK character support.
    * **Dynamic Sizing**: `font_size = image_width // 25` (minimum 40px).
    * **Visibility (Outline)**: Draw the text 8 times in black with an offset (`font_size // 15`) to create an outline/shadow, then draw white text on top.
    * **Positioning**: Bottom-right corner with padding equal to `font_size`.

### 5.2 The "Issue Submission"
When the "Submit" button in **Issue Submission** page is pressed: 
- String from the Datepicker should be combined with the current system time and be stored in `submitted_at`; 
- Issue photo should be names as `问题照片 - [门店] - [#ID] - [submitted_at]`, and saved to `./uploads` folder, **after being processed with image processing pipe line defined in 5.1 above**. Photo's relevant file path shall be recorded in `issue_photo` in db.

### 5.3 The "Bulk Submission"
When the "Buik Submission" button in **Rectification Feedback** page is pressed: For all cards that have a new `fix_photo` uploaded ready, recursively submits those rectification photos and updates the corresponding issues entries in database. 
- Refer to the *invisible* ID attribute in each card, to find the corresponding issue of the rectification photo, update the relevant entry in database (using ID to match)
	- Rectification photo should be names as `整改照片 - [门店] - [#ID] - [submitted_at]`, and saved to `./uploads`, **after being processed with image processing pipe line defined in 5.1 above**; The rectification hoto's relevant file path shall be recorded in `fix_photo` in db.
	- Automatically sets `fix_date` to the current system time for updated records.
	
### 5.4 Excel Export
* **Encoding**: Filenames must be encoded using `urllib.parse.quote`.
* **Headers**: Use RFC 6266 `Content-Disposition`: `filename*=UTF-8''{encoded_filename}.xlsx`.
* **Library**: Use `xlsxwriter` for the core Excel generation. *
* **Image Embedding (Cell Anchoring)**: Maintain existing `xlsxwriter` logic for image anchoring and cell dimensions to prevent "floating" or missing images. Do not refactor the cell-sizing logic, as it is calibrated for proper visual alignment. 
* **Enhanced Cleanup Logic**: * The system must implement a **"Delete After Send"** approach for the generated Excel file. 
	* It must also track and delete **ALL** intermediate temporary files (PNGs, JPEGs, etc.) created during the export process within the `data/exports/` folder to prevent server storage bloat. 
	* **Encoding**: Filenames must be encoded using `urllib.parse.quote`. *


### 5.5 Storage & Cleanup Logic 
- **Physical Deletion**: When records are deleted via the "Data Maintenance" function, the backend **MUST** also physically delete the corresponding image files from the disk (the `uploads/` folder) to reclaim storage space. * 
- **Relative Paths**: The SQLite database must ONLY store the filename or relative path (e.g., `/uploads/photo_123.jpg`). **NEVER** hardcode server IPs in the database.


### 5.6 API Endpoints in back-end
- **POST** `/api/submit-issues`: Creates a new issue record
- **POST** `/api/issues/rectifications`: Updates an issue with a rectification photo and status.
- **POST** `/api/delete-issues`: Delete deprecated issues and relevant images to reclaim back the disk space
- **GET** `/api/issues/pending`: Retrieves issues (with filtering).
- **GET** `/api/export-issues`: Generates and returns an Excel (.xlsx) file of filtered issues.

---

## 6. Deployment & Automation

### 6.1 Directory Structure (for reference only)
```text
md-issues-tracking-project/
├── wechat-backend/       # FastAPI application
│   ├── data/             # SQLite database location (Git ignored)
│   ├── uploads/          # Uploaded photos (Git ignored)
│   ├── exports/          # Generated Excel files (Git ignored)
│   ├── main.py           # Core API logic
│   └── requirements.txt  # Python dependencies
└── wechat-h5/            # Vue3 Frontend
    ├── src/              # Vue components and assets
    ├── package.json      # Node dependencies
    └── vite.config.js    # Vite configuration