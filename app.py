import streamlit as st
import pdfplumber
import re

def copy_button_html(text, key):
    if not text or text in ["-", "None", ""]: return ""
    safe_text = str(text).replace("'", "\\'").replace('"', '\\"')
    # font-size를 14px로 키우고, line-height를 조절하여 텍스트가 잘 보직게 수정
    return f"""
    <div style="margin-bottom: 8px;">
        <button id="btn_{key}" onclick="copyToClipboard_{key}()" style="
            width: 100%; padding: 12px 5px; border-radius: 8px; border: 1px solid #4A90E2;
            background-color: #262730; color: white; cursor: pointer;
            font-size: 14px; font-weight: 600; transition: all 0.2s;
            white-space: normal; word-break: break-all; height: 60px;
            line-height: 1.2;
        ">
            {text}
        </button>
    </div>
    <script>
    function copyToClipboard_{key}() {{
        const text = '{safe_text}';
        const btn = document.getElementById('btn_{key}');
        navigator.clipboard.writeText(text).then(() => {{
            const originalText = btn.innerText;
            btn.innerText = '✅ Copied!';
            btn.style.backgroundColor = '#28a745';
            setTimeout(() => {{
                btn.innerText = originalText;
                btn.style.backgroundColor = '#262730';
            }}, 700);
        }});
    }}
    </script>
    """

def parse_pdf_ultimate_fix(pdf_file):
    extracted_data = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=10, y_tolerance=3, layout=False)
            lines = text.split('\n')
            
            current_item = None
            for line in lines:
                line = line.strip()
                if not line: continue

                match = re.match(r'^(\d{3})\s+(.*)', line)
                if match:
                    if current_item:
                        extracted_data.append(current_item)
                    
                    item_no = match.group(1)
                    remain = match.group(2).strip()
                    parts = remain.split()
                    nums = [p for p in parts if re.sub(r'[,.\s-]', '', p).isdigit() and len(re.sub(r'[^0-9-]', '', p)) > 0]
                    
                    p_code = "-"
                    for part in parts:
                        if "◆" in part or (not re.sub(r'[,.\s-]', '', part).isdigit()):
                            p_code = part
                            break

                    current_item = {
                        "no": item_no,
                        "code": p_code,
                        "name": "",
                        "qty": nums[0] if len(nums) >= 1 else "-",
                        "unit": nums[1] if len(nums) >= 2 else "-",
                        "total": nums[2] if len(nums) >= 3 else "-",
                        "deliv": parts[-1] if not re.sub(r'[,.-]', '', parts[-1]).isdigit() and parts[-1] != p_code else ""
                    }
                
                elif current_item:
                    if current_item["code"] == "◆" or len(current_item["code"]) < 2:
                        current_item["code"] = line
                    elif not current_item["name"]:
                        current_item["name"] = line.replace("◆", "").strip()

            if current_item:
                extracted_data.append(current_item)
                
    return [[d['no'], d['code'], d['name'], d['qty'], d['unit'], d['total'], d['deliv']] for d in extracted_data]

# --- UI Layout ---
st.set_page_config(page_title="PDF 품번 완전 추출", layout="wide")
st.title("📋 PDF 품번-품명 정밀 매칭 추출기 (V7)")
st.info("버튼의 글자 크기를 키우고 가독성을 높였습니다.")

uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type="pdf")

if uploaded_file:
    data = parse_pdf_ultimate_fix(uploaded_file)
    if data:
        # 컬럼 너비 조정
        col_widths = [0.6, 2.5, 2.5, 0.7, 1.2, 1.2, 0.8]
        headers = ["번호", "품번(Code)", "품명/내용", "수량", "단가", "금액", "납기"]
        
        h_cols = st.columns(col_widths)
        for col, h in zip(h_cols, headers):
            # 헤더 폰트 크기 확대 (18px)
            col.markdown(f"<p style='text-align:center; font-weight:bold; color:#4A90E2; font-size:18px;'>{h}</p>", unsafe_allow_html=True)
        
        for r_idx, row in enumerate(data):
            d_cols = st.columns(col_widths)
            for c_idx, item in enumerate(row):
                with d_cols[c_idx]:
                    # 버튼 높이를 75로 상향 조정하여 큰 폰트 수용
                    st.components.v1.html(copy_button_html(item, f"{r_idx}_{c_idx}"), height=75)