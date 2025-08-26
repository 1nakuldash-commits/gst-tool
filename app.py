import streamlit as st
import pandas as pd
import io

# --- App Title and Description ---
# --- Icon SVG Code ---
# This is your custom icon design converted to a special format
page_icon_svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 130 55" width="130" height="55">
        <defs>
            <linearGradient id="grad1" x1="100%" y1="0%" x2="0%" y2="0%">
                <stop offset="0%" style="stop-color:#9426e9;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#f50035;stop-opacity:1" />
            </linearGradient>
        </defs>
        <style>
            .gst-text { font-family: 'Inter', sans-serif; font-size: 48px; font-weight: 800; fill: white; letter-spacing: -2px; }
            .pro-text { font-family: 'Inter', sans-serif; font-size: 36px; font-weight: 700; fill: white; letter-spacing: -1.5px; }
        </style>
        <text x="0" y="45" class="gst-text">GST</text>
        <rect x="80" y="5" width="50" height="45" rx="4" fill="url(#grad1)" />
        <text x="83" y="40" class="pro-text">PRO</text>
    </svg>
"""

# --- App Title and Icon Configuration ---
st.set_page_config(
    page_title="GST PRO",
    page_icon=page_icon_svg,
    layout="wide"
)
st.title("📄 Simplified Purchase & Sales Processor")
st.write("Upload your Purchase and Sales files below. The app will extract the required data and generate a single Excel file with two sheets.")

# --- Helper function to read either CSV or Excel files ---
def load_data(uploaded_file):
    """Reads either a CSV or an Excel file into a DataFrame, skipping the first 8 rows."""
    if uploaded_file is None:
        return None
    try:
        # Read the file, skipping the header rows to get to the data
        if uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file, skiprows=8)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            return pd.read_excel(uploaded_file, skiprows=8, engine='openpyxl')
    except Exception as e:
        st.error(f"Error reading {uploaded_file.name}: {e}. Please ensure it is a valid file with data starting after row 8.")
        return None
    return None

def process_file(df, file_type):
    """
    This function processes a single DataFrame (either Purchase or Sales)
    and returns a cleaned DataFrame with the required 6 columns.
    """
    if df is None:
        return None

    # --- 1. Smart Column Detection ---
    # Define possible column names for different report types
    # ADDED 'Invoice No' to the map with possible names
    col_map = {
        'Date': ['Invoice Date', 'Invoice date'],
        'Invoice No': ['Invoice No.', 'Invoice Number', 'Voucher No.'], # New entry for Invoice Number
        'Party Name': ['Party Name', 'Receiver Name'],
        'Taxable Amount': ['Taxable value', 'Taxable Value'],
        'GST Rate': ['Rate']
    }
    
    # Find the actual column names present in the uploaded file
    found_cols = {}
    for standard_name, possible_names in col_map.items():
        # Clean column names in the dataframe to remove leading/trailing spaces
        df.columns = df.columns.str.strip()
        found_name = next((col for col in possible_names if col in df.columns), None)
        if not found_name:
            st.error(f"Error in {file_type} file: Could not find the '{standard_name}' column. Please check the file.")
            return None
        found_cols[standard_name] = found_name

    # --- 2. Data Extraction and Cleaning ---
    # Extract only the necessary columns using the found names in the correct order
    # ADDED 'Invoice No' to the extraction list
    extracted_df = df[[
        found_cols['Date'],
        found_cols['Invoice No'], # New field added here
        found_cols['Party Name'],
        found_cols['Taxable Amount'],
        found_cols['GST Rate']
    ]].copy()
    
    # Remove rows where key data like Party Name or Taxable Amount is missing
    extracted_df.dropna(subset=[found_cols['Party Name'], found_cols['Taxable Amount']], inplace=True)
    
    # --- 3. Final Formatting ---
    # Rename columns to the final desired standard names
    # ADDED 'Invoice No' to the rename mapping
    final_df = extracted_df.rename(columns={
        found_cols['Date']: 'Date',
        found_cols['Invoice No']: 'Invoice No', # New field renamed here
        found_cols['Party Name']: 'Party Name',
        found_cols['Taxable Amount']: 'Taxable Amount',
        found_cols['GST Rate']: 'GST Rate'
    })
    
    # Format the GST Rate column by adding a '%'
    final_df['GST Rate'] = final_df['GST Rate'].astype(str) + '%'
    
    # Add the S/N column at the beginning
    final_df.insert(0, 'S/N', range(1, len(final_df) + 1))
    
    return final_df

# --- Streamlit User Interface ---
st.sidebar.header("📂 Upload Your Files")
purchase_file = st.sidebar.file_uploader("1. Upload Purchase Report File", type=["csv", "xlsx"], key="purchase")
sales_file = st.sidebar.file_uploader("2. Upload Sales Report File", type=["csv", "xlsx"], key="sales")

if st.button("🚀 Process Files and Generate Excel", type="primary"):
    if purchase_file and sales_file:
        # Load both files
        df_purchase = load_data(purchase_file)
        df_sales = load_data(sales_file)
        
        # Process each file independently
        purchase_result_df = process_file(df_purchase, 'Purchase')
        sales_result_df = process_file(df_sales, 'Sales')
        
        if purchase_result_df is not None and sales_result_df is not None:
            # Create an in-memory Excel file to hold the results
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                purchase_result_df.to_excel(writer, sheet_name='Purchase Data', index=False)
                sales_result_df.to_excel(writer, sheet_name='Sales Data', index=False)
            
            processed_data = output.getvalue()
            
            st.success("✅ Both files processed successfully! Download your Excel file below.")
            
            # Display previews in the app, hiding the extra index column
            st.subheader("Purchase Data Preview")
            st.dataframe(purchase_result_df, hide_index=True)
            
            st.subheader("Sales Data Preview")
            st.dataframe(sales_result_df, hide_index=True)
            
            # Provide download button for the final multi-sheet Excel file
            st.download_button(
                label="📥 Download Excel File (Purchase & Sales Sheets)",
                data=processed_data,
                file_name="Processed_Data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Processing failed. Please review the errors above.")
    else:
        st.warning("⚠️ Please upload both the Purchase and Sales files before processing.")
