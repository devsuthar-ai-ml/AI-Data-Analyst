import streamlit as st
from try1 import load_data, suggest_prompts, prompt_to_code, run_code, ask_llm
import pandas as pd

# Page setup
st.set_page_config(page_title="Personal AI Data Analyst", layout="wide")
st.title("🧠 Personal AI Data Analyst — Interactive Dashboard")

# Sidebar settings
st.sidebar.header("Settings")
use_llm = st.sidebar.checkbox("Use local LLM (ollama) for custom prompts", value=False)
llm_model = st.sidebar.text_input("LLM model name (ollama)", value="llama3.1")
st.sidebar.markdown("If you don't have `ollama` installed, leave this off and use built-in prompts.")

# File upload (now supports DOCX and PDF too)
uploaded = st.file_uploader(
    "Upload CSV, Excel, JSON, DOCX, or PDF",
    type=["csv", "xls", "xlsx", "json", "docx", "pdf"]
)
if uploaded is None:
    st.info("Upload a file to get started. Suggestions will appear automatically.")
    st.stop()

# Load data
try:
    df = load_data(uploaded)
except Exception as e:
    st.error(f"Failed to load file: {e}")
    st.stop()

st.success("File loaded.")
with st.expander("Preview data (first 100 rows or text)"):
    st.dataframe(df.head(100))

# Generate suggestions
suggestions = suggest_prompts(df)
st.markdown("## Suggested analyses (pick one or write your own)")
col1, col2 = st.columns([3,1])
with col1:
    selected = st.selectbox("Choose a suggested prompt", options=suggestions)
    custom = st.text_area("Or write a custom prompt (leave blank to use the selected suggestion)", height=80)
with col2:
    st.markdown("**Quick actions**")
    if st.button("Show suggestions again"):
        st.write(suggestions)

# Determine final prompt
final_prompt = custom.strip() if custom and custom.strip() else selected

st.markdown("### Final prompt")
st.write(final_prompt)

# Run analysis
if st.button("Run analysis"):
    with st.spinner("Running..."):
        # Try deterministic conversion first
        code = prompt_to_code(final_prompt, df)
        if code:
            res = run_code(df, code)
        else:
            # No deterministic code found
            if use_llm:
                system = (
                    "You are a helpful data analyst. Respond ONLY with Python code inside ```python blocks.\n"
                    "The DataFrame is named df. Use pandas for data manipulation and matplotlib for charts.\n"
                    "Do not import heavy libraries. Do not call plt.show(). Just build the figure.\n"
                )
                raw_prompt = system + "\n# User prompt: " + final_prompt
                llm_out = ask_llm(raw_prompt, model=llm_model)

                if llm_out.startswith("[LLM-]"):
                    st.error(llm_out)
                    st.stop()

                # Extract Python code block
                if "```python" in llm_out:
                    try:
                        code = llm_out.split("```python")[1].split("```")[0]
                        res = run_code(df, code)
                    except Exception as e:
                        st.error(f"Failed to execute code from LLM: {e}")
                        st.write(llm_out)
                        st.stop()
                else:
                    st.error("LLM did not return a python code block. Showing raw LLM output:")
                    st.write(llm_out)
                    st.stop()
            else:
                st.error("This is a custom prompt that the app cannot deterministically convert to code. Enable 'Use local LLM' in the sidebar to let a local model generate Python, or edit your prompt to match one of the suggested patterns.")
                st.stop()

    # Display result
    if res["type"] == "text":
        st.markdown("#### Output (text)")
        st.text(res["output"])
    elif res["type"] == "dataframe":
        st.markdown("#### Output (table)")
        st.dataframe(res["df"])
        csv = res["df"].to_csv(index=False).encode("utf-8")
        st.download_button("Download result as CSV", data=csv, file_name="result.csv", mime="text/csv")
    elif res["type"] == "image":
        st.markdown("#### Output (chart)")
        st.image(res["path"], use_column_width=True)
    else:
        st.write("Unknown result type", res)
