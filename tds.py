import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import fitz
import re
from io import BytesIO
from datetime import datetime
from pathlib import Path

# Function to extract details from TDS Returns PDF (For Form 26)
def extract_details_from_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            extracted_text = ""

            # Combine text from all pages
            for page in pdf.pages:
                extracted_text += page.extract_text() or ""

            # Extract specific details
            period_pattern = re.compile(r"period\s+(Q\d)")
            date_range_pattern = re.compile(r"\(From\s+(\d{2}/\d{2}/\d{2})\s+to\s+(\d{2}/\d{2}/\d{2})")
            form_no_box_pattern = re.compile(r"Form\s+No\.\s*(\d{2}\w)", re.IGNORECASE)
            date_pattern = re.compile(r"Date:\s*(\d{2}/\d{2}/\d{4})")

            # Extract Period
            period = period_pattern.search(extracted_text)

            # Extract Date Range
            date_range = date_range_pattern.search(extracted_text)

            # Extract the second occurrence of Form No.
            form_no_matches = form_no_box_pattern.findall(extracted_text)
            form_no = form_no_matches[1] if len(form_no_matches) > 1 else "Not found"

            # Extract Date
            date = date_pattern.search(extracted_text)

            # Format extracted details as a single row DataFrame
            details = {
                "Period": [period.group(1) if period else "Not found"],
                "Date Range": [f"{date_range.group(1)} to {date_range.group(2)}" if date_range else "Not found"],
                "Form No.": [form_no],
                "Date": [date.group(1) if date else "Not found"],
            }

            return pd.DataFrame(details)

    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})

# Function to extract table from TDS Returns PDF (For Form 26)
def extract_table_from_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            extracted_data = []

            for page in pdf.pages:
                tables = page.extract_tables()

                for table in tables:
                    if table:
                        for row in table:
                            extracted_data.append(row)

            headers = ["Sr. No.", "Return Type", "No. of Deductee / Party Records", "Amount Paid (₹)", "Tax Deducted / Collected (₹)", "Tax Deposited (₹)"]
            table_data = []

            for row in extracted_data:
                if len(row) == len(headers):
                    row_dict = dict(zip(headers, row))
                    table_data.append(row_dict)

            if len(table_data) > 1 and table_data[0]["Sr. No."] == "Sr. No.":
                table_data.pop(0)

            df = pd.DataFrame(table_data)
            df.dropna(subset=headers, how='all', inplace=True)

            return df

    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})

# Function: Process HDFC Bank PDF
def process_hdfc_bank(pdf_file):
    extracted_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            extracted_text += page.extract_text() + "\n"
    return extracted_text

# Function: Parse HDFC Bank Text
def parse_hdfc_bank_text(raw_text):
    lines = raw_text.split("\n")
    return {
        "Date of Receipt": lines[12].split()[-1],
        "Nature of Payment": lines[7].strip().replace("Nature of Payment ", ""),
        "Basic Tax": float(lines[9].replace("Basic Tax", "").strip().replace(",", "")),
        "Interest": float(lines[14].split()[1].replace(",", "")),
        "Penalty": float(lines[12].split()[1].replace(",", "")),
        "Fee (Sec. 234E)": float(lines[15].split()[3].replace(",", "")),
        "TOTAL Amount": float(lines[16].split("Drawn on")[0].replace("TOTAL", "").strip().replace(",", "")),
        "Drawn on": lines[16].split("Drawn on")[-1].strip(),
        "Payment Realisation Date": lines[19].split()[-1],
        "Challan No": int(lines[10].split()[-1].replace(",", "")),
        "Challan Serial No.": int(lines[13].split()[-1].replace(",", ""))
    }

# Function: Process Income Tax PDF
def process_income_tax(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# Function: Parse Income Tax Text
def parse_income_tax_text(text):
    details = {}
    lines = text.split("\n")
    
    for i, line in enumerate(lines):
        if "TAN" in line:
            details["TAN"] = line.split(":")[-1].strip() 
            if i + 1 < len(lines):
                details["Name"] = re.sub(r'^Name\s*:\s*', '', lines[i + 1].strip())  
        elif "Assessment Year" in line:
            details["Assessment Year"] = line.split(":")[-1].strip()
        elif "Financial Year" in line:
            details["Financial Year"] = line.split(":")[-1].strip()
        elif "Nature of Payment" in line:
            details["Nature of Payment"] = line.split(":")[-1].strip()
        elif "Challan No" in line:
            details["Challan No."] = line.split(":")[-1].strip()
        elif "Tender Date" in line:
            tender_date_raw = line.split(":")[-1]
            tender_date_cleaned = tender_date_raw.split("Tax Breakup Details")[0].strip()
            details["Tender Date"] = tender_date_cleaned
        elif line.startswith("ATax"):
            details["Tax"] = line.split("₹")[-1].strip()    
        elif line.startswith("DInterest"):
            details["Interest"] = line.split("₹")[-1].strip()
        elif line.startswith("EPenalty"):
            details["Penalty"] = line.split("₹")[-1].strip()
        elif line.startswith("FFee under section 234E"):
            details["Fee (Sec. 234E)"] = line.split("₹")[-1].strip()
        elif line.startswith("Total (A+B+C+D+E+F)"):
            details["TOTAL"] = line.split("₹")[-1].strip()
    return details

# Function: Custom Payment Processing
def extract_pdf_details(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""

    for page in reader.pages:
        text += page.extract_text()

    patterns = {
        "TAN": r"TAN\s*:\s*([A-Z0-9]+)",
        "Name": r"TAN\s*:\s*[A-Z0-9]+\s*\n\s*([A-Za-z&.,\s]+)\n",
        "Assessment Year": r"Assessment Year\s*:\s*(\d{4}-\d{2})",
        "Financial Year": r"Financial Year\s*:\s*(\d{4}-\d{2})",
        "Nature of Payment": r"Nature of Payment\s*:\s*(\w+)",
        "Amount (in Rs.)": r"Amount \(in Rs\.\)\s*:\s*₹\s*([\d,]+)",
        "Challan No.": r"Challan No\s*:\s*(\d+)",
        "Tender Date": r"Tender Date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})",
    }

    extracted_data = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        extracted_data[key] = match.group(1) if match else "Not Found"

    return extracted_data

# Function for cleaning and formatting amount
def clean_and_format_amount(amount_str):
    try:
        cleaned = re.sub(r'[^\d.]', '', amount_str)
        amount = float(cleaned)
        return "{:,.2f}".format(amount)
    except (ValueError, TypeError):
        return None

# Function to extract Form24 details
def extract_details_from_form24(pdf_file):
    details = {
        "Form No.": "",
        "Financial Year": "",
        "Quarter": "",
        "Periodicity": "",
        "Date of Filing": "",
        "Total Tax Deducted (₹)": "",
        "Total Challan Amount (₹)": "",
        "Total Tax Deposited as per Deductee Details (₹)": ""
    }

    try:
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        page = pdf_document.load_page(0)
        
        text_blocks = page.get_text("blocks")
        text = " ".join(block[4] for block in text_blocks)
        
        if '24Q' in text:
            details["Form No."] = "24Q"

        year_match = re.search(r'(\d{4}-\d{2}|\d{4}-\d{4})', text)
        if year_match:
            details["Financial Year"] = year_match.group(1)

        quarter_match = re.search(r'Q(\d)', text)
        if quarter_match:
            details["Quarter"] = f"Q{quarter_match.group(1)}"

        periodicity_match = re.search(r'Regular', text, re.IGNORECASE)
        if periodicity_match:
            details["Periodicity"] = "Regular"

        type_match = re.search(r'Type of Statement[^\n]*?(Regular|Original|Correction)', text, re.IGNORECASE)
        if type_match:
            details["Type of Statement"] = type_match.group(1)

        date_match = re.search(r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})', text)
        if date_match:
            details["Date of Filing"] = date_match.group(1)

        table_rows = []
        current_row = []
        prev_y = None
        
        sorted_blocks = sorted(text_blocks, key=lambda b: (b[1], b[0]))
        
        for block in sorted_blocks:
            y_coord = round(block[1], 1)
            if prev_y is None:
                prev_y = y_coord
            
            if abs(y_coord - prev_y) > 5:
                if current_row:
                    table_rows.append(" ".join(current_row))
                current_row = [block[4].strip()]
                prev_y = y_coord
            else:
                current_row.append(block[4].strip())
        
        if current_row:
            table_rows.append(" ".join(current_row))

        for row in table_rows:
            numbers = re.findall(r'\d+\.?\d*', row)
            large_numbers = [n for n in numbers if len(n.replace('.', '')) >= 8]
            
            if len(large_numbers) >= 3:
                amounts = []
                for num in large_numbers:
                    formatted = clean_and_format_amount(num)
                    if formatted:
                        amounts.append(formatted)
                
                if len(amounts) >= 3:
                    amount_values = [float(amt.replace(',', '')) for amt in amounts]
                    max_amount = max(amount_values)
                    max_index = amount_values.index(max_amount)
                    
                    details["Total Challan Amount (₹)"] = amounts[max_index]
                    details["Total Tax Deducted (₹)"] = amounts[1 if max_index != 1 else 0]
                    details["Total Tax Deposited as per Deductee Details (₹)"] = amounts[2]
                    break

        pdf_document.close()
        return pd.DataFrame([details])

    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})

# Function: Save Data to Excel
def save_to_excel(data_frames):
    output = BytesIO()
    combined_df = pd.concat(data_frames, ignore_index=True)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        combined_df.to_excel(writer, index=False, sheet_name="Extracted Data", float_format="%.2f")
    output.seek(0)
    return output

# Streamlit App
st.set_page_config(page_title="Challan Data Extraction Tool", layout="wide")

# Define the path to assets directory
ASSETS_DIR = Path("assets")

# Create assets directory if it doesn't exist
ASSETS_DIR.mkdir(exist_ok=True)

# Add logo to the sidebar
logo_path = Path(__file__).parent / "kkc logo.png"
if logo_path.exists():
    st.sidebar.image(str(logo_path), width=275)
else:
    st.sidebar.warning("Logo file not found. Please place 'kkc logo.png' in the assets directory.")

# Add user manual link in the sidebar
manual_path = Path(__file__).parent /"TDS_Extractor_User_Manual.pdf"
if manual_path.exists():
    with open(manual_path, "rb") as pdf_file:
        pdf_bytes = pdf_file.read()
    st.sidebar.download_button(
        label="📄 Download User Manual",
        data=pdf_bytes,
        file_name="TDS_Extractor_User_Manual.pdf",
        mime="application/pdf"
    )
else:
    st.sidebar.warning("User manual not found. Please place 'KKC.pdf' in the assets directory.")

# Add title and process configuration header in the sidebar
st.sidebar.header("🛠️ Process Configuration")

# Add title in the main content area
col1, col2 = st.columns([1, 4])
with col2:
    st.title("📄 TDS Data Extraction Tool")

# Sidebar Options
option = st.sidebar.radio(
    "Select Document Type",
    ["TDS Returns", "TDS Payments"],
    help="Choose the type of document for data extraction."
)

# Additional options based on selection
if option == "TDS Returns":
    form_type = st.sidebar.radio(
        "Select Form Type",
        ["Form24Q", "Form26Q & Form27Q"],
        help="Choose the type of TDS Return form."
    )
elif option == "TDS Payments":
    payment_option = st.sidebar.radio(
        "Select Payment Source",
        ["HDFC Bank", "Income Tax Department with Tax Breakup", "Income Tax Department without Tax Breakup"],
        help="Choose the type of payment document for processing."
    )

# File uploader
uploaded_files = st.sidebar.file_uploader(
    "Upload PDF Files",
    type="pdf",
    accept_multiple_files=True,
    key="file_uploader",
    help="Drag and drop or upload PDF files for processing."
)

submit = st.sidebar.button("🚀 Start Extraction")

# Add refresh note
st.sidebar.info("🔄 Kindly refresh the page to upload new files or start again.")

# Main Processing Section
if submit and uploaded_files:
    st.subheader("🔍 Extracting Data from Uploaded Files")
    progress = st.progress(0)
    extracted_data = []

    for idx, pdf_file in enumerate(uploaded_files):
        try:
            if option == "TDS Returns":
                if form_type == "Form24Q":
                    combined_df = extract_details_from_form24(pdf_file)
                else:  # Form26
                    details_df = extract_details_from_pdf(pdf_file)
                    table_df = extract_table_from_pdf(pdf_file)
                    combined_df = pd.concat([details_df, table_df], ignore_index=True)
            elif option == "TDS Payments":
                if payment_option == "HDFC Bank":
                    raw_text = process_hdfc_bank(pdf_file)
                    parsed_data = parse_hdfc_bank_text(raw_text)
                    combined_df = pd.DataFrame([parsed_data])
                elif payment_option == "Income Tax Department with Tax Breakup":
                    raw_text = process_income_tax(pdf_file)
                    parsed_data = parse_income_tax_text(raw_text)
                    combined_df = pd.DataFrame([parsed_data])
                else:  # Income Tax Department without Tax Breakup
                    extracted_details = extract_pdf_details(pdf_file)
                    combined_df = pd.DataFrame([extracted_details])

            extracted_data.append(combined_df)
            progress.progress((idx + 1) / len(uploaded_files))
        except Exception as e:
            st.error(f"Error processing '{pdf_file.name}': {e}")

    if extracted_data:
        final_combined_df = pd.concat(extracted_data, ignore_index=True)
        
        # Create two columns for data display and download button
        data_col, download_col = st.columns([3, 1])
        
        with data_col:
            st.subheader("📊 Extracted Data")
            st.dataframe(final_combined_df)
        
        # Create Excel file
        excel_data = save_to_excel([final_combined_df])
        
        # Add download button in the download column
        with download_col:
            # Generate timestamp for unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extracted_data_{timestamp}.xlsx"
            
            # Add download button with timestamp in filename
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=filename,
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                key="download_button"
            )
