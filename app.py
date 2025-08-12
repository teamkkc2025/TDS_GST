import streamlit as st
from pathlib import Path
from streamlit.components.v1 import html

# Path to logo
ASSETS_DIR = Path('./assets')
logo_path = ASSETS_DIR / 'kkc logo.png'

def main():
    st.set_page_config(page_title="Tool Links Dashboard", layout="wide")

    # Display logo at the top
    if logo_path.exists():
        st.image(str(logo_path), width=375)
    else:
        st.warning("Logo file not found. Please place 'kkc logo.png' in the assets directory.")

    st.title('Welcome to KKC & Associates LLP Automation Tools')
    st.write('Explore the tools below:')

    # Define links
    tool_1_url = 'https://tdsgst-gst.streamlit.app/'
    tool_2_url = 'https://challan-data-extraction-tool-jr9by5jhfixgwlw8ftexpr.streamlit.app/'

    # Display the links as styled cards
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('''
            <div style="border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h3>📄 GSTR Data Extraction Tool</h3>
                <a href="{0}" target="_blank">Click here to open GSTR Data Extraction Tool</a>
            </div>
        '''.format(tool_1_url), unsafe_allow_html=True)

    with col2:
        st.markdown('''
            <div style="border: 1px solid #e0e0e0; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h3>📑 TDS Data Extraction Tool</h3>
                <a href="{0}" target="_blank">Click here to open TDS Data Extraction Tool</a>
            </div>
        '''.format(tool_2_url), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
