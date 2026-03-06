// Show image preview when user selects a file
document.getElementById("imageInput").addEventListener("change", function () {
    const file = this.files[0];
    if (file) {
        document.getElementById("file-name").textContent = file.name;
        const preview = document.getElementById("preview");
        preview.src = URL.createObjectURL(file);
        preview.hidden = false;
    }
});

// Send image to Flask and get extracted fields
async function extractText() {
    const fileInput = document.getElementById("imageInput");
    const file = fileInput.files[0];

    if (!file) {
        showStatus("Please select an image first.", "error");
        return;
    }

    const extractBtn = document.getElementById("extractBtn");
    extractBtn.textContent = "Extracting...";
    extractBtn.disabled = true;

    const formData = new FormData();
    formData.append("image", file);

    try {
        const response = await fetch("http://127.0.0.1:5000/ocr", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            populateFields(data.fields);
            document.getElementById("verify-section").hidden = false;
            document.getElementById("verify-section").scrollIntoView({
                behavior: "smooth"
            });
            showStatus("Text extracted successfully. Please verify the fields below.", "success");
        } else {
            showStatus("Error: " + (data.error || "Unknown error"), "error");
        }
    } catch (error) {
        showStatus("Could not connect to server. Make sure Flask is running.", "error");
    }

    extractBtn.textContent = "Extract Text";
    extractBtn.disabled = false;
}

// Fill in the form fields with extracted data
function populateFields(fields) {
    document.getElementById("field-name").value    = fields.name    || "";
    document.getElementById("field-address").value = fields.address || "";
    document.getElementById("field-phone").value   = fields.phone   || "";
    document.getElementById("field-pincode").value = fields.pincode || "";
    document.getElementById("field-remarks").value = fields.remarks || "";
}

// Save verified form data to Oracle database
async function saveForm() {
    const data = {
        name:     document.getElementById("field-name").value,
        address:  document.getElementById("field-address").value,
        phone:    document.getElementById("field-phone").value,
        pincode:  document.getElementById("field-pincode").value,
        remarks:  document.getElementById("field-remarks").value,
        operator: "operator1"
    };

    if (!data.name && !data.address && !data.phone) {
        showStatus("Please fill in at least name, address or phone before saving.", "error");
        return;
    }

    try {
        const response = await fetch("http://127.0.0.1:5000/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            showStatus("Form saved successfully to database.", "success");
            resetForm();
        } else {
            showStatus("Error saving form: " + (result.error || "Unknown error"), "error");
        }
    } catch (error) {
        showStatus("Could not connect to server. Make sure Flask is running.", "error");
    }
}

// Load all past records from database
async function loadRecords() {
    try {
        const response = await fetch("http://127.0.0.1:5000/records");
        const data = await response.json();

        if (data.success) {
            displayRecords(data.records);
        } else {
            showStatus("Error loading records.", "error");
        }
    } catch (error) {
        showStatus("Could not connect to server. Make sure Flask is running.", "error");
    }
}

// Build and display records table
function displayRecords(records) {
    const container = document.getElementById("records-table-container");

    if (records.length === 0) {
        container.innerHTML = "<p style='color:#64748b;margin-top:10px;'>No records found.</p>";
        return;
    }

    let html = `
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Phone</th>
                    <th>Pincode</th>
                    <th>Address</th>
                    <th>Operator</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
    `;

    records.forEach(function (row) {
        html += `
            <tr>
                <td>${row.id}</td>
                <td>${row.name}</td>
                <td>${row.phone}</td>
                <td>${row.pincode}</td>
                <td>${row.address}</td>
                <td>${row.operator}</td>
                <td>${row.created_at}</td>
            </tr>
        `;
    });

    html += "</tbody></table>";
    container.innerHTML = html;
}

// Show a status message to the operator
function showStatus(message, type) {
    const statusDiv = document.getElementById("status-message");
    statusDiv.textContent = message;
    statusDiv.className = type;
    statusDiv.hidden = false;
    setTimeout(function () {
        statusDiv.hidden = true;
    }, 5000);
}

// Reset the entire form back to initial state
function resetForm() {
    document.getElementById("imageInput").value = "";
    document.getElementById("file-name").textContent = "No file chosen";
    document.getElementById("preview").hidden = true;
    document.getElementById("verify-section").hidden = true;
    document.getElementById("field-name").value    = "";
    document.getElementById("field-address").value = "";
    document.getElementById("field-phone").value   = "";
    document.getElementById("field-pincode").value = "";
    document.getElementById("field-remarks").value = "";
}