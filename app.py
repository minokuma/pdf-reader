import streamlit as st
import pdfplumber
import re
import math
import base64

# --- 로고 이미지를 base64로 변환하는 함수 (이미지 깨짐 방지) ---
def get_image_base64(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""
    

# --- 1. 세션 상태 및 설정 초기화 ---
st.set_page_config(page_title="PDF 품번 정밀 추출기", layout="wide")

if 'selected_brand' not in st.session_state:
    st.session_state.selected_brand = "TOTO"
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

def handle_brand_selection(brand_name):
    st.session_state.selected_brand = brand_name
    st.session_state.current_page = 1

# --- 2. 브랜드별 전용 파싱 로직 ---

def parse_toto(pdf_file):
    """[절대보존] TOTO 전용 정밀 매칭 로직"""
    extracted_data = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=10, y_tolerance=3, layout=False)
                if not text: continue
                lines = text.split('\n')
                current_item = None
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    match = re.match(r'^(\d{3})\s+(.*)', line)
                    if match:
                        if current_item: extracted_data.append(current_item)
                        item_no = match.group(1)
                        remain = match.group(2).strip()
                        parts = remain.split()
                        nums = [p for p in parts if re.sub(r'[,.\s-]', '', p).isdigit() and len(re.sub(r'[^0-9-]', '', p)) > 0]
                        p_code = next((p for p in parts if "◆" in p or not re.sub(r'[,.\s-]', '', p).isdigit()), "-")
                        current_item = {
                            "no": item_no, "code": p_code, "name": "",
                            "qty": nums[0] if len(nums) >= 1 else "-",
                            "unit": nums[1] if len(nums) >= 2 else "-",
                            "total": nums[2] if len(nums) >= 3 else "-",
                            "deliv": parts[-1] if not re.sub(r'[,.-]', '', parts[-1]).isdigit() and parts[-1] != p_code else ""
                        }
                    elif current_item and not current_item["name"]:
                        current_item["name"] = line.replace("◆", "").strip()
                if current_item: extracted_data.append(current_item)
        return [[d['no'], d['code'], d['name'], d['qty'], d['unit'], d['total'], d['deliv']] for d in extracted_data]
    except Exception: return []

def parse_eidai_fixed(pdf_file):
    """[절대보존] EIDAI 전용: 매입률(소수점)과 단가(정수) 구분 배치"""
    extracted_data = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if not text: continue
                lines = text.split('\n')
                for line in lines:
                    parts = line.split()
                    if not parts or not parts[0].isdigit(): continue
                    no_val = parts[0]
                    code_parts = []
                    idx = 1
                    while idx < len(parts) and not re.match(r'^[0-9,.]+$', parts[idx].replace('%','')):
                        code_parts.append(parts[idx])
                        idx += 1
                    code_val = "".join(code_parts)
                    remains = parts[idx:]
                    qty = remains[0] if len(remains) > 0 else ""
                    base_price = remains[1] if len(remains) > 1 else ""
                    financial_data = remains[2:]
                    processed_nums = []
                    f_idx = 0
                    for _ in range(3):
                        if f_idx < len(financial_data) and "." in financial_data[f_idx]:
                            processed_nums.append(financial_data[f_idx])
                            processed_nums.append(financial_data[f_idx+1] if f_idx+1 < len(financial_data) else "")
                            processed_nums.append(financial_data[f_idx+2] if f_idx+2 < len(financial_data) else "")
                            f_idx += 3
                        else:
                            processed_nums.append("") 
                            processed_nums.append(financial_data[f_idx] if f_idx < len(financial_data) else "") 
                            processed_nums.append(financial_data[f_idx+1] if f_idx+1 < len(financial_data) else "")
                            f_idx += 2
                    row = [no_val, code_val, qty, base_price] + processed_nums
                    extracted_data.append(row[:13])
        extracted_data.sort(key=lambda x: int(x[0]))
        return extracted_data
    except Exception: return []

def parse_panasonic(pdf_file):
    """[V32.0] 파나소닉 전용: No 컬럼 데이터 분리 추출"""
    extracted_data = []
    try:
        count = 1
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=2, y_tolerance=2)
                if not text: continue
                
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    code_match = re.search(r'([A-Z0-9-]{7,})', line)
                    if not code_match: continue
                    
                    code = code_match.group(1)
                    parts = line.split()
                    
                    amount = "직접 확인 필요"
                    remark = "-"
                    
                    num_parts = len(parts)
                    if num_parts >= 2:
                        found_amount_idx = -1
                        for i in range(1, min(4, num_parts)): 
                            target = parts[-i].replace(',', '').replace('\\', '')
                            if target.isdigit() and len(target) > 2:
                                amount = parts[-i]
                                found_amount_idx = num_parts - i
                                break
                        if found_amount_idx != -1 and found_amount_idx < num_parts - 1:
                            remark = " ".join(parts[found_amount_idx + 1:])

                    # [No, 품번, 품명, 사이즈, 수량, 단가, 금액, 비고] 형태로 반환
                    extracted_data.append([
                        str(count),       # No. 컬럼용 데이터 분리
                        code,             # 품번
                        "직접 확인 필요", 
                        "직접 확인 필요", 
                        "직접 확인 필요", 
                        "직접 확인 필요", 
                        amount,          
                        remark           
                    ])
                    count += 1
        return extracted_data
    except Exception: return []

# --- 3. UI 컴포넌트 ---

def copy_button_html(text, key, height=45):
    if not text or text in ["-", "None", ""]: return ""
    
    # "확인 필요" 문구가 포함된 경우 빨간색 강조 스타일 적용
    is_warning = "확인 필요" in str(text)
    bg_color = "#3d0808" if is_warning else "#262730"
    font_color = "#ff4b4b" if is_warning else "#E0E0E0"
    border_color = "#ff4b4b" if is_warning else "#3E4451"
    
    safe_text = str(text).replace("'", "\\'").replace('"', '\\"')
    return f"""
    <div style="margin-bottom: 5px; display: flex; justify-content: center;">
        <button id="btn_{key}" onclick="navigator.clipboard.writeText('{safe_text}'); this.style.backgroundColor='#4A90E2'; setTimeout(()=>this.style.backgroundColor='{bg_color}', 500);" 
            style="width: 100%; padding: 5px; border-radius: 6px; border: 1px solid {border_color};
            background-color: {bg_color}; color: {font_color}; cursor: pointer; font-size: 13px;
            font-weight: {'bold' if is_warning else 'normal'};
            height: {height}px; text-align: center; overflow: hidden; white-space: nowrap;
            display: flex; align-items: center; justify-content: center;">
            {text}
        </button>
    </div>
    """

# --- 4. 메인 화면 ---
# --- 4. 메인 화면 ---
# --- 4. 메인 화면 ---
st.title("📋 PDF 품번 정밀 추출기 (V17.0)")

# 1. 브랜드 정보 및 로고 설정
brands = [
    {"name": "TOTO", "img": "toto_logo.png"},
    {"name": "PANASONIC", "img": "panasonic_logo.png"},
    {"name": "EIDAI", "img": "eidai_logo.png"},
    {"name": "LIXIL", "img": "lixil_logo.png"},
    {"name": "DAIKEN", "img": "daiken_logo.png"}
]

# 2. 로고 버튼 레이아웃 스타일 (이미지 테두리 강조용)
st.markdown("""
    <style>
    .selected-logo {
        border: 4px solid #FF4B4B !important;
        border-radius: 10px;
        padding: 5px;
        background-color: rgba(255, 75, 75, 0.1);
    }
    .unselected-logo {
        border: 1px solid #3E4451;
        border-radius: 10px;
        padding: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 브랜드 선택 영역
b_cols = st.columns(5)

for i, brand in enumerate(brands):
    with b_cols[i]:
        is_selected = st.session_state.selected_brand == brand["name"]
        
        # 선택 상태에 따른 스타일 결정
        border_color = "#FF4B4B" if is_selected else "#3E4451"
        bg_color = "rgba(255, 75, 75, 0.1)" if is_selected else "rgba(255, 255, 255, 0.05)"
        
        # 1. 로고 이미지 영역 (고정 높이 80px 설정으로 정렬)
        # container를 사용해 이미지와 버튼을 하나의 박스로 묶음
        with st.container():
            st.markdown(f"""
                <div style="
                    border: 2px solid {border_color};
                    border-radius: 10px 10px 0 0;
                    padding: 15px;
                    background-color: {bg_color};
                    height: 100px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-bottom: none;
                ">
                    <img src="data:image/png;base64,{get_image_base64(brand['img'])}" 
                         style="max-width: 100%; max-height: 70px; object-fit: contain;">
                </div>
                """, unsafe_allow_html=True)
            
            # 2. 버튼 영역 (이미지 박스 바로 아래에 붙임)
            # 테두리를 연결하기 위해 버튼 스타일을 미세 조정
            if st.button(brand["name"], key=f"btn_sel_{i}", use_container_width=True,
                         type="primary" if is_selected else "secondary"):
                handle_brand_selection(brand["name"])
                st.rerun()

st.divider()

file = st.file_uploader(f"[{st.session_state.selected_brand}] PDF 업로드", type="pdf")

if file:
    # --- 로딩 스피너 적용 부분 ---
    with st.spinner(f"{st.session_state.selected_brand} 데이터를 정밀 분석 중입니다. 잠시만 기다려주세요..."):
        if st.session_state.selected_brand == "TOTO":
            data = parse_toto(file)
            headers = ["No", "品番(품번)", "品名(품명)", "数量(수량)", "単価(단가)", "金額(금액)", "納期(납기)"]
            widths = [0.6, 2.5, 2.5, 0.7, 1.2, 1.2, 0.8]
            b_height = 65
            items_per_page = 100
        elif st.session_state.selected_brand == "EIDAI":
            data = parse_eidai_fixed(file)
            headers = ["No", "品番(품번)", "数量(수량)", "設計単価(설계단가)", "掛率1(매입1)", "提供単価1(제공단가1)", "提供金額1(제공금액1)", "掛率2(매입2)", "提供単価2(제공단가2)", "提供金額2(제공금액2)", "掛率3(매입3)", "提供単価3(제공단가3)", "提供金額3(제공금액3)"]
            widths = [0.4, 1.5, 0.8, 0.8, 0.7, 0.9, 0.9, 0.7, 0.9, 0.9, 0.7, 0.9, 0.9]
            b_height = 45
            items_per_page = 20
        elif st.session_state.selected_brand == "PANASONIC":
            data = parse_panasonic(file)
            # 맨 앞에 "No" 헤더 추가 및 너비(0.5) 배정
            headers = ["No", "品番(품번)", "品名(품명)", "サイズ(사이즈)", "数量(수량)", "単価(단가)", "金額(금액)", "備考(비고)"]
            widths = [0.5, 2.0, 2.5, 1.5, 0.7, 1.2, 1.2, 1.0]
            b_height = 55
            items_per_page = 30
        else:
            st.warning("준비 중인 브랜드입니다.")
            data = []

    if data:
        st.success(f"총 {len(data)}건의 품목을 찾아냈습니다.")
        total_pages = math.ceil(len(data) / items_per_page)
        if total_pages > 1:
            page_cols = st.columns(min(total_pages, 8))
            for p_num in range(1, total_pages + 1):
                if page_cols[(p_num-1)%8].button(f"{p_num}ページ", key=f"pg_{p_num}", 
                                           type="primary" if st.session_state.current_page == p_num else "secondary",
                                           use_container_width=True):
                    st.session_state.current_page = p_num
                    st.rerun()
        
        start_idx = (st.session_state.current_page - 1) * items_per_page
        page_data = data[start_idx : start_idx + items_per_page]

        st.divider()
        h_cols = st.columns(widths)
        for h_col, h in zip(h_cols, headers):
            h_col.markdown(f"<p style='text-align:center; font-weight:bold; color:#4A90E2; font-size:12px; margin-bottom:10px;'>{h}</p>", unsafe_allow_html=True)
        
        for r_idx, row in enumerate(page_data):
            d_cols = st.columns(widths)
            for c_idx, val in enumerate(row):
                if c_idx < len(widths):
                    with d_cols[c_idx]:
                        st.components.v1.html(copy_button_html(val, f"r{r_idx}c{c_idx}", b_height), height=b_height+15)