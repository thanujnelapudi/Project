console.log("Loaded script.js v10 - manual form type selector");

// ── Currently selected form type (default: auto-detect) ──────────────────────
let selectedFormType = "auto";

// ── Form type selector ────────────────────────────────────────────────────────
function selectFormType(type, btn) {
    selectedFormType = type;

    // Update button styles
    document.querySelectorAll(".form-type-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    // Update hint text
    const note = document.getElementById("auto-detect-note");
    if (type === "auto") {
        note.textContent = "Auto Detect is selected — the system will identify the form type from the image.";
    } else {
        const config = FORM_CONFIGS[type];
        note.textContent = `Selected: ${config.title} — the system will extract fields for this form type.`;
    }
}

// ── Image preview ─────────────────────────────────────────────────────────────
document.getElementById("imageInput").addEventListener("change", function () {
    const file = this.files[0];
    if (file) {
        document.getElementById("file-name").textContent = file.name;
        const preview = document.getElementById("preview");
        preview.src = URL.createObjectURL(file);
        preview.hidden = false;
    }
});

// =============================================================================
// Field definitions per form type
// =============================================================================
const FORM_CONFIGS = {
    generic: {
        title: "📄 Postal / General Form",
        fields: [
            { key: "name",    label: "Recipient Name",  type: "text",     placeholder: "E.g., Rahul Sharma" },
            { key: "pincode", label: "Pincode",         type: "text",     placeholder: "E.g., 500034" },
            { key: "remarks", label: "Remarks / Notes", type: "text",     placeholder: "E.g., Speed Post" },
            { key: "address", label: "Address",         type: "textarea", placeholder: "E.g., Banjara Hills, Hyderabad", fullWidth: true },
        ]
    },
    bank_kyc: {
        title: "🏦 Bank KYC Form",
        fields: [
            { type: "header", label: "Personal Details" },
            { key: "full_name",          label: "Full Name",            type: "text", placeholder: "Full Name", fullWidth: true },
            { key: "father_spouse_name", label: "Father / Spouse Name", type: "text", placeholder: "Father / Spouse Name", fullWidth: true },
            { key: "mother_name",        label: "Mother Name",          type: "text", placeholder: "Mother Name", fullWidth: true },
            { key: "date_of_birth",      label: "Date of Birth",        type: "text", placeholder: "Date of Birth" },
            { key: "pan_number",         label: "PAN Number",           type: "text", placeholder: "PAN Number" },
            { type: "header", label: "Identity Documents" },
            { key: "passport_number",    label: "Passport Number",      type: "text", placeholder: "Passport Number" },
            { key: "driving_licence",    label: "Driving Licence",      type: "text", placeholder: "Driving Licence" },
            { key: "aadhaar_number",     label: "Aadhaar Number",       type: "text", placeholder: "Aadhaar Number", fullWidth: true },
            { type: "header", label: "Address" },
            { key: "address_line1",      label: "Address Line 1",       type: "text", placeholder: "Address Line 1", fullWidth: true },
            { key: "address_line2",      label: "Address Line 2",       type: "text", placeholder: "Address Line 2", fullWidth: true },
            { key: "address_line3",      label: "Address Line 3",       type: "text", placeholder: "Address Line 3", fullWidth: true },
            { key: "city",               label: "City",                 type: "text", placeholder: "City" },
            { key: "district",           label: "District",             type: "text", placeholder: "District" },
            { key: "pin_code",           label: "Pin Code",             type: "text", placeholder: "Pin Code" },
            { key: "kyc_number",         label: "KYC Number",           type: "text", placeholder: "KYC Number" },
        ]
    },
    postal_speedpost: {
        title: "📮 Speed Post / Parcel Form",
        fields: [
            { key: "sender_name",      label: "Sender Name",      type: "text",     placeholder: "Sender full name" },
            { key: "sender_pincode",   label: "Sender Pincode",   type: "text",     placeholder: "6-digit PIN" },
            { key: "sender_city",      label: "Sender City",      type: "text",     placeholder: "City" },
            { key: "sender_state",     label: "Sender State",     type: "text",     placeholder: "State" },
            { key: "sender_address",   label: "Sender Address",   type: "textarea", placeholder: "Sender address", fullWidth: true },
            { key: "receiver_name",    label: "Receiver Name",    type: "text",     placeholder: "Receiver full name" },
            { key: "receiver_pincode", label: "Receiver Pincode", type: "text",     placeholder: "6-digit PIN" },
            { key: "receiver_city",    label: "Receiver City",    type: "text",     placeholder: "City" },
            { key: "receiver_state",   label: "Receiver State",   type: "text",     placeholder: "State" },
            { key: "receiver_address", label: "Receiver Address", type: "textarea", placeholder: "Receiver address", fullWidth: true },
        ]
    },
    postal_savings: {
        title: "🏧 Post Office Savings Bank Form",
        fields: [
            { key: "applicant_name", label: "Full Name",     type: "text", placeholder: "First + Middle + Last" },
            { key: "first_name",     label: "First Name",    type: "text", placeholder: "First name" },
            { key: "middle_name",    label: "Middle Name",   type: "text", placeholder: "Middle name" },
            { key: "last_name",      label: "Last Name",     type: "text", placeholder: "Last name" },
            { key: "email",          label: "Email ID",      type: "text", placeholder: "E.g., abc@gmail.com" },
            { key: "pan_number",     label: "PAN Number",    type: "text", placeholder: "E.g., ABCDE1234F" },
            { key: "mother_name",    label: "Mother's Name", type: "text", placeholder: "Mother's maiden name" },
            { key: "cif_id",         label: "CIF ID",        type: "text", placeholder: "CIF ID" },
        ]
    },
    courier: {
        title: "📦 Courier / Shipment Form",
        fields: [
            { key: "origin",          label: "Origin",           type: "text",     placeholder: "Origin city" },
            { key: "destination",     label: "Destination",      type: "text",     placeholder: "Destination city" },
            { key: "shipment_date",   label: "Date of Shipment", type: "text",     placeholder: "DD/MM/YYYY" },
            { key: "weight",          label: "Weight",           type: "text",     placeholder: "E.g., 2kg" },
            { key: "shipper_name",    label: "Shipper's Name",   type: "text",     placeholder: "Shipper full name" },
            { key: "shipper_address", label: "Shipper Address",  type: "textarea", placeholder: "Shipper address", fullWidth: true },
            { key: "receiver_name",   label: "Receiver's Name",  type: "text",     placeholder: "Receiver full name" },
            { key: "receiver_address",label: "Receiver Address", type: "textarea", placeholder: "Receiver address", fullWidth: true },
            { key: "postal_code",     label: "Postal Code",      type: "text",     placeholder: "6-digit PIN" },
        ]
    },
    education: {
        title: "🎓 Education / Admission Form",
        fields: [
            { key: "student_name",      label: "Student's Name",    type: "text",     placeholder: "Full name" },
            { key: "father_name",       label: "Father's Name",     type: "text",     placeholder: "Father's name" },
            { key: "mother_name",       label: "Mother's Name",     type: "text",     placeholder: "Mother's name" },
            { key: "guardian_name",     label: "Guardian's Name",   type: "text",     placeholder: "Guardian or nominee" },
            { key: "date_of_birth",     label: "Date of Birth",     type: "text",     placeholder: "DD/MM/YYYY" },
            { key: "phone_number",      label: "Phone Number",      type: "text",     placeholder: "10-digit number" },
            { key: "religion",          label: "Religion",          type: "text",     placeholder: "E.g., Hindu" },
            { key: "nationality",       label: "Nationality",       type: "text",     placeholder: "E.g., Indian" },
            { key: "nid_number",        label: "NID / ID Number",    type: "text",     placeholder: "National ID" },
            { key: "email",             label: "Email Address",     type: "text",     placeholder: "E.g., abc@gmail.com" },
            { key: "blood_group",       label: "Blood Group",       type: "text",     placeholder: "E.g., O+" },
            { key: "course_name",       label: "Course Applied",    type: "text",     placeholder: "Course name" },
            { key: "present_address",   label: "Present Address",   type: "textarea", placeholder: "Full address", fullWidth: true },
            { key: "permanent_address", label: "Permanent Address", type: "textarea", placeholder: "Full address", fullWidth: true },
        ]
    }
};

// =============================================================================
// Extract
// =============================================================================
async function extractText() {
    const fileInput = document.getElementById("imageInput");
    const file = fileInput.files[0];
    if (!file) { showStatus("Please select an image first.", "error"); return; }

    const extractBtn = document.getElementById("extractBtn");
    extractBtn.textContent = "Extracting...";
    extractBtn.disabled = true;

    const formData = new FormData();
    formData.append("image", file);
    // Pass selected form type to server (or "auto")
    formData.append("form_type_hint", selectedFormType);

    try {
        const response = await fetch("/ocr", { method: "POST", body: formData, credentials: "include" });
        const data = await response.json();

        if (data.success) {
            // If user picked a specific type, use that. Otherwise use what server detected.
            const formType = (selectedFormType !== "auto") ? selectedFormType : (data.form_type || "generic");
            renderVerifySection(formType, data.fields, data.confidence);
            document.getElementById("verify-section").hidden = false;
            document.getElementById("verify-section").scrollIntoView({ behavior: "smooth" });
            showStatus("Text extracted successfully. Please verify the fields below.", "success");
        } else {
            showStatus("Error: " + (data.error || "Unknown error"), "error");
        }
    } catch (err) {
        showStatus("Could not connect to server. Make sure Flask is running.", "error");
    } finally {
        extractBtn.textContent = "Extract Text";
        extractBtn.disabled = false;
    }
}

// =============================================================================
// Render verify section dynamically
// =============================================================================
function renderVerifySection(formType, fields, confidence) {
    const config = FORM_CONFIGS[formType] || FORM_CONFIGS["generic"];

    document.getElementById("form-type-label").textContent = config.title;

    const grid = document.getElementById("form-fields-grid");
    grid.innerHTML = "";

    let needsInputCount = 0;

    config.fields.forEach(({ key, label, type, placeholder, fullWidth }) => {
        if (type === "header") {
            const div = document.createElement("div");
            div.className = "verify-form-group full-width";
            div.innerHTML = `<div class="section-divider" style="height: 16px;"></div><label style="display: block; font-size: 13px; font-weight: 600; color: #475569; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">${label}</label>`;
            grid.appendChild(div);
            return;
        }

        const score = confidence ? (confidence[key] || 0) : 0;
        const value = fields ? (fields[key] || "") : "";
        
        let badgeBg, badgeColor, badgeText, inputBorder;
        if (score >= 70) {
            badgeBg = "#EAF3DE"; badgeColor = "#3B6D11"; badgeText = score + "%";
            inputBorder = "#CCCCCC";
        } else if (score > 0) {
            badgeBg = "#FAEEDA"; badgeColor = "#633806"; badgeText = score + "%";
            inputBorder = "#FAC775";
        } else {
            badgeBg = "#FCEBEB"; badgeColor = "#A32D2D"; badgeText = "Needs input";
            inputBorder = "#F09595";
            needsInputCount++;
        }

        // Auto-detect full width if it's a textarea, otherwise default to user setting
        let isFull = fullWidth === true || type === "textarea";

        const div = document.createElement("div");
        div.className = "verify-form-group" + (isFull ? " full-width" : "");

        const badge = `<span class="verify-conf-badge" id="badge-${key}"
            style="background-color:${badgeBg};color:${badgeColor}">${badgeText}</span>`;

        let inputHtml = "";
        if (type === "textarea") {
            inputHtml = `<textarea class="verify-input" id="field-${key}" rows="3" placeholder="${placeholder}"
                style="border-color:${inputBorder}">${escapeHtml(value)}</textarea>`;
        } else {
            inputHtml = `<input class="verify-input" type="text" id="field-${key}" placeholder="${placeholder}"
                value="${escapeHtml(value)}"
                style="border-color:${inputBorder}">`;
        }

        div.innerHTML = `
            <div class="verify-form-label-row">
                <label>${label}</label>
                ${badge}
            </div>
            ${inputHtml}
        `;
        grid.appendChild(div);
    });

    window._currentFormType   = formType;
    window._currentFormConfig = config;

    updateFooterCount(needsInputCount);
}

function escapeHtml(str) {
    return String(str || "")
        .replace(/&/g,'&amp;').replace(/</g,'&lt;')
        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function updateFooterCount(count) {
    const countEl = document.getElementById("manual-input-count");
    if (countEl) {
        if (count > 0) {
            countEl.textContent = `${count} field${count > 1 ? 's' : ''} need manual input`;
            countEl.style.color = "#A32D2D";
        } else {
            countEl.textContent = "All fields verified";
            countEl.style.color = "#3B6D11";
        }
    }
}

// =============================================================================
// Save
// =============================================================================
async function saveForm() {
    const saveBtn  = document.getElementById("saveBtn");
    saveBtn.textContent = "Saving...";
    saveBtn.disabled    = true;

    const config   = window._currentFormConfig || FORM_CONFIGS["generic"];
    const formType = window._currentFormType   || "generic";
    const data     = { form_type: formType, operator: "operator1", fields: {} };

    config.fields.forEach(({ key }) => {
        const el = document.getElementById("field-" + key);
        if (el) data.fields[key] = el.value;
    });

    const hasData = Object.values(data.fields).some(v => v && v.trim());
    if (!hasData) {
        showStatus("Please fill in at least one field before saving.", "error");
        saveBtn.textContent = "Save to Database"; saveBtn.disabled = false;
        return;
    }

    try {
        const response = await fetch("/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
            credentials: "include"
        });
        const result = await response.json();
        if (result.success) {
            showStatus("Form saved successfully to database.", "success");
            resetForm();
        } else {
            showStatus("Error: " + (result.error || "Could not save data"), "error");
        }
    } catch (err) {
        showStatus("Could not connect to server. Make sure Flask is running.", "error");
    } finally {
        saveBtn.textContent = "Save to Database"; saveBtn.disabled = false;
    }
}

// =============================================================================
// Status + Reset
// =============================================================================
function showStatus(message, type) {
    const el = document.getElementById("status-message");
    el.textContent = message; el.className = type; el.hidden = false;
    setTimeout(() => { el.hidden = true; }, 5000);
}

function resetForm() {
    document.getElementById("imageInput").value = "";
    document.getElementById("file-name").textContent = "No file chosen";
    const preview = document.getElementById("preview");
    preview.src = ""; preview.hidden = true;
    document.getElementById("verify-section").hidden = true;
    document.getElementById("form-fields-grid").innerHTML = "";
    document.getElementById("form-type-label").textContent = "";
    
    const countEl = document.getElementById("manual-input-count");
    if (countEl) countEl.textContent = "0 fields need manual input";
    
    document.getElementById("status-message").hidden = true;
    window._currentFormType   = null;
    window._currentFormConfig = null;
    document.getElementById("upload-section").scrollIntoView({ behavior: "smooth" });
}