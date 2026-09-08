import pandas as pd
from io import StringIO
import json

def _parse_markdown_table_to_records(markdown_table: str) -> tuple[list[str], list[dict]]:
    """
    Phân tích một bảng Markdown thành danh sách các dictionary (records) và trả về headers.
    Đây là hàm nội bộ được sử dụng bởi convert_markdown_table_to_df.
    """
    # Tìm dòng chứa dấu gạch ngang phân tách header và body
    lines = markdown_table.strip().split('\n')
    import re
    separator_pattern = re.compile(r'^\|(\s*[:-]+\s*\|)+$')
    separator_index = -1
    for i, line in enumerate(lines):
        if separator_pattern.match(line):
            separator_index = i
            break
            
    if separator_index == -1:
        print("Cảnh báo: Không tìm thấy dòng phân tách header trong bảng Markdown. Trả về danh sách rỗng.")
        return [], []

    try:
        # Lấy dòng header và làm sạch
        header_line = lines[separator_index - 1]
        headers = [h.strip() for h in header_line.split('|')]
        # Remove potential empty string at the beginning/end from split if the table starts/ends with '|'
        if headers and headers[0] == '':
            headers = headers[1:]
        if headers and headers[-1] == '':
            headers = headers[:-1]
        # DO NOT filter out empty strings from headers here, preserve empty column headers

        # Lấy các dòng dữ liệu và làm sạch
        data = []
        for line in lines[separator_index + 1:]:
            line_stripped = line.strip()
            # Bỏ qua các dòng tiêu đề phụ như "**Conditions**" hoặc "**Actions**"
            if line_stripped.startswith('| **Conditions**') or line_stripped.startswith('| **Actions**'):
                continue

            cols = [c.strip() for c in line.split('|')]
            # Remove potential empty string at the beginning/end from split if the table starts/ends with '|'
            if cols and cols[0] == '':
                cols = cols[1:]
            if cols and cols[-1] == '':
                cols = cols[:-1]
            # DO NOT filter out empty strings from cols here, preserve empty cells

            if cols: # Chỉ thêm hàng nếu có dữ liệu sau khi làm sạch
                data.append(cols)
        
        if not data:
            print("Cảnh báo: Không có dữ liệu trong bảng Markdown sau khi phân tích.")
            return headers, []

        num_headers = len(headers)
        
        # Điều chỉnh các hàng dữ liệu để khớp với độ dài header
        adjusted_data = []
        for row_cols in data:
            num_row_cols = len(row_cols)
            if num_row_cols < num_headers:
                # Đệm bằng chuỗi rỗng
                row_cols.extend([''] * (num_headers - num_row_cols))
            elif num_row_cols > num_headers:
                # Cắt bớt
                row_cols = row_cols[:num_headers]
            adjusted_data.append(row_cols)

        # Chuyển đổi adjusted_data thành danh sách các dictionary
        records = []
        for row_cols in adjusted_data:
            record = {}
            for i, header in enumerate(headers):
                record[header] = row_cols[i] if i < len(row_cols) else ''
            records.append(record)
        
        return headers, records
    except Exception as e:
        print(f"Lỗi khi phân tích bảng Markdown: {e}")
        return [], []

def convert_markdown_table_to_df(markdown_table: str) -> pd.DataFrame:
    """
    Chuyển đổi một bảng Markdown thành pandas DataFrame.
    """
    headers, records = _parse_markdown_table_to_records(markdown_table)
    if not records:
        return pd.DataFrame(columns=headers) # Trả về DataFrame rỗng với các headers đã được phân tích
    
    # Tạo DataFrame, sử dụng headers đã được phân tích để đảm bảo thứ tự cột
    df = pd.DataFrame(records, columns=headers)
    return df

def write_test_artifacts_to_file(output_md_file_path: str, output_csv_file_path: str, decision_table_df: pd.DataFrame, test_scenarios: list[dict], test_purposes: list[str], all_refined_specs: list[dict]):
    """
    Ghi Decision Table vào file CSV và các Test Scenarios, Test Purposes, Final Test Spec vào file Markdown.
    """
    # Ghi Decision Table vào CSV
    if not decision_table_df.empty:
        decision_table_df.to_csv(output_csv_file_path, index=False, encoding='utf-8')
        print(f"Đã ghi Decision Table vào file CSV: {output_csv_file_path}")
    else:
        print("Cảnh báo: Decision Table rỗng, không ghi vào file CSV.")

    # Ghi các artifact còn lại vào Markdown
    with open(output_md_file_path, 'w', encoding='utf-8') as f:
        f.write("# Báo Cáo Tạo Test Artifacts\n\n")
        f.write("Đây là báo cáo tổng hợp các artifact được tạo ra từ quy trình sinh test.\n\n")

        f.write("## 1. Decision Table (Bảng Quyết Định)\n\n")
        f.write(f"Bảng quyết định đã được lưu vào file CSV riêng biệt: `{output_csv_file_path}`.\n\n")
        
        f.write("## 2. Test Scenarios (Các Kịch Bản Kiểm Thử)\n\n")
        f.write("Các kịch bản kiểm thử được trích xuất từ bảng quyết định, mỗi kịch bản đại diện cho một trường hợp kiểm thử cụ thể.\n\n")
        for i, scenario in enumerate(test_scenarios):
            f.write(f"### 2.{i+1}. Scenario {i+1}\n")
            f.write("```json\n")
            f.write(json.dumps(scenario, indent=2, ensure_ascii=False))
            f.write("\n```\n\n")
        f.write("\n")

        f.write("## 3. Test Purposes (Mục Đích Kiểm Thử)\n\n")
        f.write("Mục đích kiểm thử cho mỗi kịch bản, mô tả điều gì cần được xác minh.\n\n")
        for i, purpose in enumerate(test_purposes):
            f.write(f"- **Scenario {i+1}:** {purpose}\n")
        f.write("\n\n")

        f.write("## 4. Final Test Specifications (Đặc Tả Kiểm Thử Cuối Cùng cho TẤT CẢ Scenarios)\n\n")
        f.write("Các đặc tả kiểm thử chi tiết cho từng kịch bản, bao gồm mục đích, điều kiện tiên quyết, các bước thực hiện và ghi chú.\n\n")
        for i, spec_data in enumerate(all_refined_specs):
            f.write(f"### 4.{i+1}. Test Specification for Scenario {spec_data['scenario_index']}\n")
            f.write(f"**Scenario:** {spec_data['scenario']}\n")
            f.write(f"**Purpose:** {spec_data['purpose']}\n")
            f.write("```json\n")
            f.write(json.dumps(spec_data['test_specification'], indent=2, ensure_ascii=False))
            f.write("\n```\n\n")

    print(f"Đã ghi các Test Scenarios, Test Purposes và Final Test Specification vào file Markdown: {output_md_file_path}")
