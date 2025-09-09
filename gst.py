import streamlit as st
import fitz  # PyMuPDF
import pdfplumber
import re
import pandas as pd
from pathlib import Path
 
# Set Streamlit page layout
st.set_page_config(layout="wide")
 
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
# After the logo display code in the sidebar section

# Add User Manual download button below the logo
manual_path = Path(__file__).parent /"GST_Extractor_User_Manual.pdf"
if manual_path.exists():
    with open(manual_path, "rb") as manual_file:
        st.sidebar.download_button(
            label="📄 Download User Manual",
            data=manual_file,
            file_name="GST_Extractor_User_Manual.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
else:
    st.sidebar.warning("User manual not found. Please place 'user_manual.pdf' in the assets directory.")
 
# Add sidebar for GST type selection
st.sidebar.title("GST Return Type")
gst_type = st.sidebar.radio("Select GST Return Type", ["GSTR-1", "GSTR-3B"])

# Add refresh note
st.sidebar.info("🔄 Kindly refresh the page to upload new files or start again.")
 
# GST State Code Mapping
GST_STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka",
    "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
    "97": "Other Territory", "99": "Centre Jurisdiction",
}

# Helper function to get state from GSTIN
def get_state_from_gstin(gstin):
    if not gstin or len(gstin) < 2:
        return "Unknown"
    state_code = gstin[:2]
    return GST_STATE_CODES.get(state_code, "Unknown")
 
# GSTR-1 Functions
def extract_details(pdf_path):
    details = {"GSTIN": "", "State": "", "Legal Name": "", "Month": "", "Financial Year": ""}
   
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                gstin_match = re.search(r'GSTIN\s*[:\-]?\s*(\d{2}[A-Z0-9]{13})', text)
                if gstin_match:
                    details["GSTIN"] = gstin_match.group(1)
                    details["State"] = GST_STATE_CODES.get(details["GSTIN"][:2], "Unknown")
               
                legal_name_match = re.search(r'Legal name of the registered person\s*[:\-]?\s*(.*)', text)
                if legal_name_match:
                    details["Legal Name"] = legal_name_match.group(1).strip()
               
                month_match = re.search(r'Tax period\s*[:\-]?\s*(\w+)', text)
                if month_match:
                    details["Month"] = month_match.group(1).strip()
               
                fy_match = re.search(r'Financial year\s*[:\-]?\s*(\d{4}-\d{2})', text)
                if fy_match:
                    details["Financial Year"] = fy_match.group(1).strip()
               
                break
    return details
 
def extract_total_liability(pdf_bytes):
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        text = "\n".join([page.get_text("text") for page in doc])
   
    pattern = r"Total Liability \(Outward supplies other than Reverse charge\)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)"
    match = re.search(pattern, text)
   
    if match:
        return [match.group(1), match.group(2), match.group(3), match.group(4), match.group(5)]
    return ["Not Found", "", "", "", ""]

# New function to extract Tables 4A and 4B
def extract_tables_4A_4B(pdf_bytes):
    tables = {
        "4A": {
            "description": "Taxable outward supplies made to registered persons (other than reverse charge supplies)",
            "title": "B2B Regular",
            "data": None
        },
        "4B": {
            "description": "Taxable outward supplies made to registered persons attracting tax on reverse charge",
            "title": "B2B Reverse charge",
            "data": None
        }
    }
    
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        text = "\n".join([page.get_text("text") for page in doc])
        
        # Extract Table 4A
        pattern_4A = r"4A - Taxable outward supplies made to registered persons.*?Total\s+(\d+)\s+Invoice\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)"
        match_4A = re.search(pattern_4A, text, re.DOTALL)
        
        if match_4A:
            tables["4A"]["data"] = {
                "No. of records": match_4A.group(1),
                "Value": match_4A.group(2),
                "Integrated Tax": match_4A.group(3),
                "Central Tax": match_4A.group(4),
                "State/UT Tax": match_4A.group(5),
                "Cess": match_4A.group(6)
            }
        
        # Extract Table 4B
        pattern_4B = r"4B - Taxable outward supplies made to registered persons attracting tax on reverse charge.*?Total\s+(\d+)\s+Invoice\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)"
        match_4B = re.search(pattern_4B, text, re.DOTALL)
        
        if match_4B:
            tables["4B"]["data"] = {
                "No. of records": match_4B.group(1),
                "Value": match_4B.group(2),
                "Integrated Tax": match_4B.group(3),
                "Central Tax": match_4B.group(4),
                "State/UT Tax": match_4B.group(5),
                "Cess": match_4B.group(6)
            }
    
    return tables
 
# GSTR-3B Functions
def clean_numeric_value(value):
    if value is None:
        return 0.0
   
    if isinstance(value, str):
        value = value.replace("E", "").replace("F", "").strip()
   
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return 0.0
 
def extract_general_details(text):
    def safe_extract(pattern, text):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None
   
    gstin = safe_extract(r"GSTIN(?:\s+of\s+the\s+supplier)?\s+([A-Z0-9]+)", text)
    state = get_state_from_gstin(gstin)
    
    return {
        "GSTIN": gstin,
        "State": state,
        "Legal Name": safe_extract(r"Legal name of the registered person\s+(.+)", text),
        "Date": safe_extract(r"Date of ARN\s+([\d/]+)", text),
        "Financial Year": safe_extract(r"Year\s+(\d{4}-\d{2})", text),
        "Period": safe_extract(r"Period\s+([A-Za-z]+)", text),
    }

def extract_table_3_1(pdf):
    expected_columns = ["Nature of Supplies", "Total Taxable Value", "Integrated Tax", "Central Tax", "State/UT Tax", "Cess"]
   
    for page in pdf.pages:
        text = page.extract_text()
        if "3.1" in text and "Nature of Supplies" in text:
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                df = df.iloc[:, :len(expected_columns)]
                df.columns = expected_columns
               
                for col in expected_columns[1:]:
                    df[col] = df[col].apply(clean_numeric_value)
                return df
   
    return pd.DataFrame(columns=expected_columns)

def extract_numbers_from_line(line):
    """
    Extract numeric values from a line, handling GSTR-3B number formats
    """
    # Remove common non-numeric characters but preserve decimals and commas
    clean_line = re.sub(r'[^\d\s,\.]', ' ', line)
    
    # Find all number patterns
    patterns = [
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # Numbers with commas like 42,390.00
        r'(\d+\.\d{2})',  # Decimal numbers like 42390.00
        r'(\d+)'  # Plain integers
    ]
    
    numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, clean_line)
        if matches:
            for match in matches:
                try:
                    # Clean and convert
                    clean_num = match.replace(',', '')
                    num_val = float(clean_num)
                    numbers.append(num_val)
                except ValueError:
                    continue
            break  # Use the first pattern that gives us results
    
    return numbers

def parse_table_4_data(table_text, full_text):
    """
    Parse Table 4 data based on the actual GSTR-3B structure
    """
    extracted_data = {}
    
    # Define patterns and known values based on the document structure
    patterns = {
        "(5) All other ITC": {
            "patterns": [
                r"\(5\)\s+All other ITC\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)",
                r"All other ITC\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)"
            ]
        },
        "(2) Others": {
            "patterns": [
                r"\(2\)\s+Others\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)",
                r"B\.\s+ITC Reversed.*?\(2\)\s+Others\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)"
            ]
        },
        "C. Net ITC available (A-B)": {
            "patterns": [
                r"C\.\s+Net ITC available \(A-B\)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)",
                r"Net ITC available.*?([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)"
            ]
        },
        "(1) ITC reclaimed which was reversed under Table 4(B)(2) in earlier tax period": {
            "patterns": [
                r"\(1\)\s+ITC reclaimed.*?earlier tax period\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)",
                r"ITC reclaimed.*?([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)"
            ]
        }
    }
    
    # Try to extract using patterns first
    for key, config in patterns.items():
        found = False
        for pattern in config["patterns"]:
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    values = []
                    for i in range(1, 5):
                        val_str = match.group(i).replace(',', '')
                        values.append(float(val_str))
                    extracted_data[key] = values
                    found = True
                    break
                except (ValueError, IndexError):
                    continue
        
        # If not found through patterns, try line-by-line extraction
        if not found:
            lines = full_text.split('\n')
            for line in lines:
                if key == "(5) All other ITC" and "All other ITC" in line:
                    numbers = extract_numbers_from_line(line)
                    if len(numbers) >= 4:
                        extracted_data[key] = numbers[:4]
                        break
                elif key == "(2) Others" and "(2)" in line and "Others" in line:
                    numbers = extract_numbers_from_line(line)
                    if len(numbers) >= 4:
                        extracted_data[key] = numbers[:4]
                        break
                elif key == "C. Net ITC available (A-B)" and "Net ITC available" in line:
                    numbers = extract_numbers_from_line(line)
                    if len(numbers) >= 4:
                        extracted_data[key] = numbers[:4]
                        break
                elif key.startswith("(1) ITC reclaimed") and "ITC reclaimed" in line:
                    numbers = extract_numbers_from_line(line)
                    if len(numbers) >= 4:
                        extracted_data[key] = numbers[:4]
                        break
    
    # For items not found, set to zero
    remaining_items = [
        "(1) Import of goods",
        "(2) Import of services", 
        "(3) Inward supplies liable to reverse charge (other than 1 & 2 above)",
        "(4) Inward supplies from ISD",
        "(1) As per rules 38,42 & 43 of CGST Rules and section 17(5)",
        "(2) Ineligible ITC under section 16(4) & ITC restricted due to PoS rules"
    ]
    
    for item in remaining_items:
        if item not in extracted_data:
            extracted_data[item] = [0.0, 0.0, 0.0, 0.0]
    
    return extracted_data

def extract_table_4(pdf):
    """
    Improved Table 4 extraction that correctly maps data from GSTR-3B
    """
    # Initialize the result structure with correct GSTR-3B Table 4 categories
    table_4_structure = [
        "(1) Import of goods",
        "(2) Import of services", 
        "(3) Inward supplies liable to reverse charge (other than 1 & 2 above)",
        "(4) Inward supplies from ISD",
        "(5) All other ITC",
        "(1) As per rules 38,42 & 43 of CGST Rules and section 17(5)",
        "(2) Others",
        "C. Net ITC available (A-B)",
        "(1) ITC reclaimed which was reversed under Table 4(B)(2) in earlier tax period",
        "(2) Ineligible ITC under section 16(4) & ITC restricted due to PoS rules"
    ]
    
    # Extract all text from PDF
    full_text = ""
    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            full_text += page_text + "\n"
    
    # Find Table 4 section
    table_4_start = full_text.find("4. Eligible ITC")
    if table_4_start == -1:
        table_4_start = full_text.find("Eligible ITC")
    
    table_4_end = full_text.find("5.", table_4_start)
    if table_4_end == -1:
        table_4_end = full_text.find("Values of exempt", table_4_start)
    if table_4_end == -1:
        table_4_end = len(full_text)
    
    # Extract Table 4 text section
    table_4_text = full_text[table_4_start:table_4_end] if table_4_start != -1 else ""
    
    # Parse the actual data from document structure
    extracted_data = parse_table_4_data(table_4_text, full_text)
    
    # Build result DataFrame
    table_4_result = []
    for row_desc in table_4_structure:
        if row_desc in extracted_data:
            values = extracted_data[row_desc]
        else:
            values = [0.0, 0.0, 0.0, 0.0]  # Default: IGST, CGST, SGST, Cess
        
        table_4_result.append({
            "Details": row_desc,
            "Integrated tax": values[0] if len(values) > 0 else 0.0,
            "Central tax": values[1] if len(values) > 1 else 0.0,
            "State/UT tax": values[2] if len(values) > 2 else 0.0,
            "Cess": values[3] if len(values) > 3 else 0.0
        })
    
    return pd.DataFrame(table_4_result)

def extract_table_6_1(pdf):
    """
    Improved extraction for Table 6.1 - Payment of tax
    """
    table_6_1_data = []
    
    # Method 1: Try structured table extraction
    for page in pdf.pages:
        text = page.extract_text()
        if not text or "6.1" not in text or "Payment of tax" not in text:
            continue
        
        tables = page.extract_tables()
        for table in tables:
            if not table:
                continue
            
            # Look for payment table structure
            for row_idx, row in enumerate(table):
                if not row:
                    continue
                
                cleaned_row = []
                for cell in row:
                    if cell is None:
                        cleaned_row.append("")
                    else:
                        cleaned_row.append(str(cell).strip())
                
                # Check if this looks like a tax payment row
                first_cell = cleaned_row[0].lower()
                if any(tax_type in first_cell for tax_type in ['integrated', 'central', 'state', 'cess']):
                    if len(cleaned_row) >= 8:  # Should have multiple payment columns
                        
                        # Determine section type based on surrounding text
                        section_type = determine_section_type(text, row_idx)
                        
                        # Extract payment data
                        payment_data = extract_payment_data_from_row(cleaned_row)
                        if payment_data:
                            payment_data["Section"] = section_type
                            table_6_1_data.append(payment_data)
    
    # Method 2: Extract from text patterns
    if not table_6_1_data:
        full_text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
        
        # Find Table 6.1 section
        table_6_1_start = full_text.find("6.1")
        if table_6_1_start == -1:
            table_6_1_start = full_text.find("Payment of tax")
        
        if table_6_1_start != -1:
            # Extract the relevant section
            table_6_1_section = full_text[table_6_1_start:table_6_1_start + 2000]  # Reasonable section size
            table_6_1_data = extract_table_6_1_from_text(table_6_1_section)
    
    # Method 3: Create default structure if nothing found
    if not table_6_1_data:
        # Create default rows for all tax types
        tax_types = ["Integrated tax", "Central tax", "State/UT tax", "Cess"]
        sections = ["(A) Other than reverse charge", "(B) Reverse charge"]
        
        for section in sections:
            for tax_type in tax_types:
                table_6_1_data.append({
                    "Tax Type": tax_type,
                    "Section": section, 
                    "Total tax payable": 0.0,
                    "Tax paid through ITC - Integrated tax": 0.0,
                    "Tax paid through ITC - Central tax": 0.0,
                    "Tax paid through ITC - State/UT tax": 0.0,
                    "Tax paid through ITC - Cess": 0.0,
                    "Tax paid in cash": 0.0,
                    "Interest paid in cash": 0.0,
                    "Late fee paid in cash": 0.0
                })
    
    return pd.DataFrame(table_6_1_data)

def determine_section_type(text, row_position):
    """
    Determine if a row belongs to 'Other than reverse charge' or 'Reverse charge' section
    """
    # Look for section headers in the text around the row position
    text_lower = text.lower()
    
    # Find positions of section markers
    reverse_charge_pos = text_lower.find("reverse charge")
    other_than_pos = text_lower.find("other than reverse")
    
    # Simple heuristic: if reverse charge appears before other_than, 
    # and we're in the later part of the table, it's likely reverse charge
    if reverse_charge_pos != -1 and (other_than_pos == -1 or reverse_charge_pos > other_than_pos):
        return "(B) Reverse charge"
    else:
        return "(A) Other than reverse charge"

def extract_payment_data_from_row(row):
    """
    Extract payment data from a table row
    """
    if len(row) < 2:
        return None
    
    try:
        return {
            "Tax Type": row[0],
            "Total tax payable": clean_numeric_value(row[1]) if len(row) > 1 else 0.0,
            "Tax paid through ITC - Integrated tax": clean_numeric_value(row[2]) if len(row) > 2 else 0.0,
            "Tax paid through ITC - Central tax": clean_numeric_value(row[3]) if len(row) > 3 else 0.0,
            "Tax paid through ITC - State/UT tax": clean_numeric_value(row[4]) if len(row) > 4 else 0.0, 
            "Tax paid through ITC - Cess": clean_numeric_value(row[5]) if len(row) > 5 else 0.0,
            "Tax paid in cash": clean_numeric_value(row[6]) if len(row) > 6 else 0.0,
            "Interest paid in cash": clean_numeric_value(row[7]) if len(row) > 7 else 0.0,
            "Late fee paid in cash": clean_numeric_value(row[8]) if len(row) > 8 else 0.0
        }
    except (IndexError, ValueError):
        return None

def extract_table_6_1_from_text(text):
    """
    Extract Table 6.1 data from plain text
    """
    table_6_1_data = []
    
    lines = text.split('\n')
    current_section = "(A) Other than reverse charge"  # Default
    
    for line in lines:
        line_lower = line.lower()
        
        # Check for section headers
        if "reverse charge" in line_lower and "other than" not in line_lower:
            current_section = "(B) Reverse charge"
        elif "other than reverse" in line_lower:
            current_section = "(A) Other than reverse charge"
        
        # Look for tax type rows
        if any(tax_type in line_lower for tax_type in ['integrated tax', 'central tax', 'state tax', 'cess']):
            # Extract numbers from the line
            numbers = re.findall(r'(\d+(?:,\d{3})*(?:\.\d{2})?)', line)
            if len(numbers) >= 2:  # At least total payable and one payment method
                
                # Determine tax type
                tax_type = "Unknown"
                if "integrated" in line_lower:
                    tax_type = "Integrated tax"
                elif "central" in line_lower:
                    tax_type = "Central tax"
                elif "state" in line_lower or "ut" in line_lower:
                    tax_type = "State/UT tax"
                elif "cess" in line_lower:
                    tax_type = "Cess"
                
                # Convert numbers and pad to required length
                clean_numbers = []
                for num_str in numbers[:8]:  # Take up to 8 numbers
                    try:
                        clean_numbers.append(float(num_str.replace(',', '')))
                    except ValueError:
                        clean_numbers.append(0.0)
                
                # Pad with zeros if needed
                while len(clean_numbers) < 8:
                    clean_numbers.append(0.0)
                
                table_6_1_data.append({
                    "Tax Type": tax_type,
                    "Section": current_section,
                    "Total tax payable": clean_numbers[0],
                    "Tax paid through ITC - Integrated tax": clean_numbers[1], 
                    "Tax paid through ITC - Central tax": clean_numbers[2],
                    "Tax paid through ITC - State/UT tax": clean_numbers[3],
                    "Tax paid through ITC - Cess": clean_numbers[4],
                    "Tax paid in cash": clean_numbers[5],
                    "Interest paid in cash": clean_numbers[6],
                    "Late fee paid in cash": clean_numbers[7]
                })
    
    return table_6_1_data
 
def create_combined_gstr3b_sheet(general_df, table_3_1_df, table_4_df, table_6_1_df):
    """
    Create a single combined sheet with all GSTR-3B data organized systematically
    """
    # Initialize an empty DataFrame for the combined sheet
    combined_df = pd.DataFrame()
   
    # Process all files
    unique_files = set(table_3_1_df["File Name"].unique()) | set(table_4_df["File Name"].unique()) | set(table_6_1_df["File Name"].unique())
   
    rows = []
   
    for idx, file_name in enumerate(unique_files):
        # Get general details for this file
        file_general_details = general_df[general_df.index == idx].to_dict(orient='records')
        if file_general_details:
            general_info = file_general_details[0]
        else:
            general_info = {"GSTIN": "Unknown", "Legal Name": "Unknown", "Date": "Unknown",
                           "Financial Year": "Unknown", "Period": "Unknown", "State": "Unknown"}
       
        # Create a row with file and general information
        base_row = {
            "File Name": file_name,
            "GSTIN": general_info.get("GSTIN", "Unknown"),
            "State": general_info.get("State", "Unknown"),
            "Legal Name": general_info.get("Legal Name", "Unknown"),
            "Date": general_info.get("Date", "Unknown"),
            "Financial Year": general_info.get("Financial Year", "Unknown"),
            "Period": general_info.get("Period", "Unknown"),
            "Data Type": "",
            "Description": "",
            "Total Taxable Value": 0.0,
            "Integrated Tax": 0.0,
            "Central Tax": 0.0,
            "State/UT Tax": 0.0,
            "Cess": 0.0,
            "Total Tax Payable": 0.0,
            "Tax Paid Through ITC": 0.0,
            "Tax Paid in Cash": 0.0,
            "Interest Paid in Cash": 0.0,
            "Late Fee Paid in Cash": 0.0
        }
       
        # Add a header row for this file
        header_row = base_row.copy()
        header_row["Data Type"] = "FILE INFO"
        header_row["Description"] = "File Information"
        rows.append(header_row)
       
        # Add 3.1 data
        file_table_3_1 = table_3_1_df[table_3_1_df["File Name"] == file_name]
        if not file_table_3_1.empty:
            for _, row in file_table_3_1.iterrows():
                data_row = base_row.copy()
                data_row["Data Type"] = "Table 3.1"
                data_row["Description"] = row.get("Nature of Supplies", "")
                data_row["Total Taxable Value"] = row.get("Total taxable value", 0.0)
                data_row["Integrated Tax"] = row.get("Integrated tax", 0.0)
                data_row["Central Tax"] = row.get("Central tax", 0.0)
                data_row["State/UT Tax"] = row.get("State/UT tax", 0.0)
                data_row["Cess"] = row.get("Cess", 0.0)
                rows.append(data_row)
       
        # Add Table 4 data
        file_table_4 = table_4_df[table_4_df["File Name"] == file_name]
        if not file_table_4.empty:
            for _, row in file_table_4.iterrows():
                data_row = base_row.copy()
                data_row["Data Type"] = "Table 4"
                data_row["Description"] = row.get("Details", "")
                data_row["Integrated Tax"] = row.get("Integrated tax", 0.0)
                data_row["Central Tax"] = row.get("Central tax", 0.0)
                data_row["State/UT Tax"] = row.get("State/UT tax", 0.0)
                data_row["Cess"] = row.get("Cess", 0.0)
                rows.append(data_row)
       
        # Add Table 6.1 data
        file_table_6_1 = table_6_1_df[table_6_1_df["File Name"] == file_name]
        if not file_table_6_1.empty:
            for _, row in file_table_6_1.iterrows():
                data_row = base_row.copy()
                data_row["Data Type"] = "Table 6.1"
                data_row["Description"] = f"{row.get('Section', '')} - {row.get('Tax Type', '')}"
                data_row["Total Tax Payable"] = row.get("Total tax payable", 0.0)
                data_row["Tax Paid Through ITC"] = (
                    row.get("Tax paid through ITC - Integrated tax", 0.0) +
                    row.get("Tax paid through ITC - Central tax", 0.0) +
                    row.get("Tax paid through ITC - State/UT tax", 0.0) +
                    row.get("Tax paid through ITC - Cess", 0.0)
                )
                data_row["Tax Paid in Cash"] = row.get("Tax paid in cash", 0.0)
                data_row["Interest Paid in Cash"] = row.get("Interest paid in cash", 0.0)
                data_row["Late Fee Paid in Cash"] = row.get("Late fee paid in cash", 0.0)
                rows.append(data_row)
       
        # Add a separator row
        separator_row = {k: "" for k in base_row.keys()}
        separator_row["Description"] = "----------------------"
        rows.append(separator_row)
   
    # Create DataFrame from rows
    combined_df = pd.DataFrame(rows)
    return combined_df
 
# Main Application Logic
if gst_type == "GSTR-1":
    st.title("📄 GSTR-1 Data Extraction Tool")
    st.write("Drag and Drop or Upload GSTR-1 PDFs to extract details")
   
    uploaded_files = st.file_uploader("", type=["pdf"], accept_multiple_files=True)
   
    if uploaded_files:
        data = []
        table_4A_data = []
        table_4B_data = []
        
        for uploaded_file in uploaded_files:
            pdf_bytes = uploaded_file.read()
            details = extract_details(uploaded_file)
            total_liability = extract_total_liability(pdf_bytes)
            data.append([uploaded_file.name] + list(details.values()) + total_liability)
            
            # Extract Tables 4A and 4B
            tables_4A_4B = extract_tables_4A_4B(pdf_bytes)
            
            # Process Table 4A
            if tables_4A_4B["4A"]["data"]:
                table_4A_data.append([
                    uploaded_file.name,
                    details["GSTIN"],
                    details["State"],  # Added State column here
                    details["Legal Name"],
                    details["Month"],
                    details["Financial Year"],
                    tables_4A_4B["4A"]["data"]["No. of records"],
                    tables_4A_4B["4A"]["data"]["Value"],
                    tables_4A_4B["4A"]["data"]["Integrated Tax"],
                    tables_4A_4B["4A"]["data"]["Central Tax"],
                    tables_4A_4B["4A"]["data"]["State/UT Tax"],
                    tables_4A_4B["4A"]["data"]["Cess"]
                ])
            
            # Process Table 4B
            if tables_4A_4B["4B"]["data"]:
                table_4B_data.append([
                    uploaded_file.name,
                    details["GSTIN"],
                    details["State"],  # Added State column here
                    details["Legal Name"],
                    details["Month"],
                    details["Financial Year"],
                    tables_4A_4B["4B"]["data"]["No. of records"],
                    tables_4A_4B["4B"]["data"]["Value"],
                    tables_4A_4B["4B"]["data"]["Integrated Tax"],
                    tables_4A_4B["4B"]["data"]["Central Tax"],
                    tables_4A_4B["4B"]["data"]["State/UT Tax"],
                    tables_4A_4B["4B"]["data"]["Cess"]
                ])
       
        columns = ["File Name", "GSTIN", "State", "Legal Name", "Month", "Financial Year", "Taxable Value", "IGST", "CGST", "SGST", "Cess"]
        df = pd.DataFrame(data, columns=columns)
        
        # Create DataFrames for Tables 4A and 4B
        columns_4AB = ["File Name", "GSTIN", "State", "Legal Name", "Month", "Financial Year", "No. of records", "Value", "Integrated Tax", "Central Tax", "State/UT Tax", "Cess"]
        df_4A = pd.DataFrame(table_4A_data, columns=columns_4AB)
        df_4B = pd.DataFrame(table_4B_data, columns=columns_4AB)
       
        st.write("### Total Liability (Outward supplies other than Reverse charge) ")
        st.dataframe(df)

       
        def multiselect_with_select_all(label, options):
            selected = st.multiselect(label, ["Select All"] + options, default=["Select All"])
            return options if "Select All" in selected else selected
       
        selected_month = multiselect_with_select_all("Filter by Month", df["Month"].unique().tolist())
        selected_state = multiselect_with_select_all("Filter by State", df["State"].unique().tolist())
        selected_gstin = multiselect_with_select_all("Filter by GSTIN", df["GSTIN"].unique().tolist())
        selected_legal_name = multiselect_with_select_all("Filter by Legal Name", df["Legal Name"].unique().tolist())
        selected_year = multiselect_with_select_all("Filter by Financial Year", df["Financial Year"].unique().tolist())
       
        filtered_df = df
        filtered_df_4A = df_4A
        filtered_df_4B = df_4B
        
        if selected_month:
            filtered_df = filtered_df[filtered_df["Month"].isin(selected_month)]
            filtered_df_4A = filtered_df_4A[filtered_df_4A["Month"].isin(selected_month)]
            filtered_df_4B = filtered_df_4B[filtered_df_4B["Month"].isin(selected_month)]
            
        if selected_state:
            filtered_df = filtered_df[filtered_df["State"].isin(selected_state)]
            filtered_df_4A = filtered_df_4A[filtered_df_4A["State"].isin(selected_state)]
            filtered_df_4B = filtered_df_4B[filtered_df_4B["State"].isin(selected_state)]
            
        if selected_gstin:
            filtered_df = filtered_df[filtered_df["GSTIN"].isin(selected_gstin)]
            filtered_df_4A = filtered_df_4A[filtered_df_4A["GSTIN"].isin(selected_gstin)]
            filtered_df_4B = filtered_df_4B[filtered_df_4B["GSTIN"].isin(selected_gstin)]
            
        if selected_legal_name:
            filtered_df = filtered_df[filtered_df["Legal Name"].isin(selected_legal_name)]
            filtered_df_4A = filtered_df_4A[filtered_df_4A["Legal Name"].isin(selected_legal_name)]
            filtered_df_4B = filtered_df_4B[filtered_df_4B["Legal Name"].isin(selected_legal_name)]
            
        if selected_year:
            filtered_df = filtered_df[filtered_df["Financial Year"].isin(selected_year)]
            filtered_df_4A = filtered_df_4A[filtered_df_4A["Financial Year"].isin(selected_year)]
            filtered_df_4B = filtered_df_4B[filtered_df_4B["Financial Year"].isin(selected_year)]
       
        st.write("### Filtered Results - Total Liability")
        st.dataframe(filtered_df)
        
        st.write("### Filtered Results - Table 4A")
        st.dataframe(filtered_df_4A)
        
        st.write("### Filtered Results - Table 4B")
        st.dataframe(filtered_df_4B)
       
        # Add Excel download functionality for GSTR-1
        output_excel = "GSTR1_Filtered.xlsx"
        with pd.ExcelWriter(output_excel) as writer:
            # Only include filtered data in the Excel file
            filtered_df.to_excel(writer, sheet_name="Filtered Total Liability", index=False)
            filtered_df_4A.to_excel(writer, sheet_name="Filtered Table 4A", index=False)
            filtered_df_4B.to_excel(writer, sheet_name="Filtered Table 4B", index=False)
       
        with open(output_excel, "rb") as f:
            st.download_button("Download Filtered Data as Excel", f, file_name="GSTR1_Filtered.xlsx")
 
else:  # GSTR-3B
    st.title("📄 GSTR-3B Data Extraction Tool")
    st.write("Drag and Drop or Upload GSTR-3B PDFs to extract details")
   
    uploaded_files = st.file_uploader("", type="pdf", accept_multiple_files=True)
   
    if uploaded_files:
        all_general_details = []
        all_table_3_1 = []
        all_table_4 = []
        all_table_6_1 = []
       
        for pdf_file in uploaded_files:
            with pdfplumber.open(pdf_file) as pdf:
                full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
               
                general_details = extract_general_details(full_text)
                all_general_details.append(general_details)
               
                table_3_1 = extract_table_3_1(pdf)
                table_3_1["File Name"] = pdf_file.name
                all_table_3_1.append(table_3_1)
               
                table_4 = extract_table_4(pdf)
                table_4["File Name"] = pdf_file.name
                all_table_4.append(table_4)
               
                table_6_1 = extract_table_6_1(pdf)
                table_6_1["File Name"] = pdf_file.name
                all_table_6_1.append(table_6_1)
       
        # 1) General Details
        st.subheader("General Details")
        general_df = pd.DataFrame(all_general_details)
        st.dataframe(general_df)
       
        # Process the extracted tables
        final_table_3_1 = pd.concat(all_table_3_1, ignore_index=True)
        final_table_4 = pd.concat(all_table_4, ignore_index=True)
        final_table_6_1 = pd.concat(all_table_6_1, ignore_index=True)
        
        # Create combined data sheet
        combined_df = create_combined_gstr3b_sheet(general_df, final_table_3_1, final_table_4, final_table_6_1)
        
        # 2) Filters
        st.write("### Filter Data")
        
        def multiselect_with_select_all(label, options):
            selected = st.multiselect(label, ["Select All"] + options, default=["Select All"])
            return options if "Select All" in selected else selected
        
        # Extract unique values for filters
        months = general_df["Period"].dropna().unique().tolist()
        states = [GST_STATE_CODES.get(gstin[:2], "Unknown") if gstin else "Unknown" 
                 for gstin in general_df["GSTIN"].dropna().unique()]
        gstins = general_df["GSTIN"].dropna().unique().tolist()
        legal_names = general_df["Legal Name"].dropna().unique().tolist()
        financial_years = general_df["Financial Year"].dropna().unique().tolist()
        
        # Create filters
        selected_month = multiselect_with_select_all("Filter by Month", months)
        selected_state = multiselect_with_select_all("Filter by State", states)
        selected_gstin = multiselect_with_select_all("Filter by GSTIN", gstins)
        selected_legal_name = multiselect_with_select_all("Filter by Legal Name", legal_names)
        selected_year = multiselect_with_select_all("Filter by Financial Year", financial_years)
        
        # Apply filters to dataframes
        filtered_general_df = general_df.copy()
        filtered_table_3_1 = final_table_3_1.copy()
        filtered_table_4 = final_table_4.copy()
        filtered_table_6_1 = final_table_6_1.copy()
        filtered_combined_df = combined_df.copy()
        
        # Filter by Month (Period)
        if selected_month:
            filtered_general_df = filtered_general_df[filtered_general_df["Period"].isin(selected_month)]
            file_names = filtered_general_df.index.tolist()
            
            filtered_table_3_1 = filtered_table_3_1[filtered_table_3_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_4 = filtered_table_4[filtered_table_4["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_6_1 = filtered_table_6_1[filtered_table_6_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_combined_df = filtered_combined_df[filtered_combined_df["Period"].isin(selected_month)]
        
        # Filter by State (derived from GSTIN)
        if selected_state:
            state_gstins = []
            for gstin in gstins:
                if gstin and GST_STATE_CODES.get(gstin[:2], "Unknown") in selected_state:
                    state_gstins.append(gstin)
            
            filtered_general_df = filtered_general_df[filtered_general_df["GSTIN"].isin(state_gstins)]
            file_names = filtered_general_df.index.tolist()
            
            filtered_table_3_1 = filtered_table_3_1[filtered_table_3_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_4 = filtered_table_4[filtered_table_4["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_6_1 = filtered_table_6_1[filtered_table_6_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_combined_df = filtered_combined_df[filtered_combined_df["GSTIN"].isin(state_gstins)]
        
        # Filter by GSTIN
        if selected_gstin:
            filtered_general_df = filtered_general_df[filtered_general_df["GSTIN"].isin(selected_gstin)]
            file_names = filtered_general_df.index.tolist()
            
            filtered_table_3_1 = filtered_table_3_1[filtered_table_3_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_4 = filtered_table_4[filtered_table_4["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_6_1 = filtered_table_6_1[filtered_table_6_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_combined_df = filtered_combined_df[filtered_combined_df["GSTIN"].isin(selected_gstin)]
        
        # Filter by Legal Name
        if selected_legal_name:
            filtered_general_df = filtered_general_df[filtered_general_df["Legal Name"].isin(selected_legal_name)]
            file_names = filtered_general_df.index.tolist()
            
            filtered_table_3_1 = filtered_table_3_1[filtered_table_3_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_4 = filtered_table_4[filtered_table_4["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_6_1 = filtered_table_6_1[filtered_table_6_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_combined_df = filtered_combined_df[filtered_combined_df["Legal Name"].isin(selected_legal_name)]
        
        # Filter by Financial Year
        if selected_year:
            filtered_general_df = filtered_general_df[filtered_general_df["Financial Year"].isin(selected_year)]
            file_names = filtered_general_df.index.tolist()
            
            filtered_table_3_1 = filtered_table_3_1[filtered_table_3_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_4 = filtered_table_4[filtered_table_4["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_6_1 = filtered_table_6_1[filtered_table_6_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_combined_df = filtered_combined_df[filtered_combined_df["Financial Year"].isin(selected_year)]
        
        # Display filtered results in order specified
        # 3) Filtered General Details
        st.write("### Filtered General Details")
        st.dataframe(filtered_general_df)
        
        # 4) Filtered Table 3.1
        st.write("### Filtered Table 3.1 - Outward and Reverse Charge Supplies")
        st.dataframe(filtered_table_3_1)
        
        # 5) Filtered Table 4
        st.write("### Filtered Table 4 - Eligible ITC")
        st.dataframe(filtered_table_4)
        
        # 6) Filtered Table 6.1
        st.write("### Filtered Table 6.1 - Payment of Tax")
        st.dataframe(filtered_table_6_1)
        
        # 7) Filtered Combined GSTR-3B Data
        st.write("### Filtered Combined GSTR-3B Data")
        st.dataframe(filtered_combined_df)
       
        output_excel = "GSTR3B_Filtered.xlsx"
        with pd.ExcelWriter(output_excel) as writer:
            # Only write filtered data to the Excel file
            filtered_combined_df.to_excel(writer, sheet_name="Filtered Combined Data", index=False)
            filtered_general_df.to_excel(writer, sheet_name="Filtered General Details", index=False)
            filtered_table_3_1.to_excel(writer, sheet_name="Filtered Table 3.1", index=False)
            filtered_table_4.to_excel(writer, sheet_name="Filtered Table 4", index=False)
            filtered_table_6_1.to_excel(writer, sheet_name="Filtered Table 6.1", index=False)
       
        with open(output_excel, "rb") as f:
            st.download_button("Download Filtered Data", f, file_name="GSTR3B_Filtered.xlsx")
