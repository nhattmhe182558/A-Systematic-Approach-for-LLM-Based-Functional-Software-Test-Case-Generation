import os
import json
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.gridspec as gridspec

# Configuration
SOURCE_DIR = "generated_testcase_action_forth_attempt"
OUTPUT_CSV = "comprehensive_report.csv"
OUTPUT_IMG = "dashboard_analysis.png"

# --- 1. DATA PROCESSING ---
def get_failure_category(eval_data):
    """Priority: Web Fail > Invalid Action > Assertion Fail > Success"""
    if not eval_data.get("llm_fail", True):
        return "Success"
    if eval_data.get("web_fail", False):
        return "Web Failure"
    if not eval_data.get("valid_action", True):
        return "Invalid Action"
    if not eval_data.get("result", False):
        return "Assertion Failure"
    return "Unknown Failure"

def collect_data():
    records = []
    print(f"Scanning '{SOURCE_DIR}'...")

    for root, dirs, files in os.walk(SOURCE_DIR):
        folder_name = os.path.basename(root)
        
        for file in files:
            if file.endswith(".json"):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if isinstance(data, list) and len(data) > 0:
                        item = data[0]
                        tc_info = item.get("test_case_info", {})
                        eval_info = item.get("evaluation", {})
                        log = item.get("execute_log", [])

                        records.append({
                            "Business Process": folder_name,
                            "Use Case": tc_info.get("use_case_id", "Unknown"),
                            "Test Case": tc_info.get("test_case_id", file),
                            "Category": get_failure_category(eval_info),
                            "Steps Executed": len(log),
                            "Is Success": 1 if not eval_info.get("llm_fail", True) else 0
                        })
                except Exception as e:
                    pass # Skip errors
    return records

# --- 2. VISUALIZATION ---
def create_dashboard(records):
    if not records:
        print("No data found.")
        return

    df = pd.DataFrame(records)
    
    # Save Raw Data
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Data saved to {OUTPUT_CSV}")

    # Setup Dashboard Layout (2 Rows: Top for Summaries, Bottom for Detail)
    fig = plt.figure(figsize=(18, 12))
    gs = gridspec.GridSpec(2, 2, height_ratios=[1, 1.5]) 
    
    # Define Colors
    colors = {
        "Success": "#4CAF50",           # Green
        "Web Failure": "#F44336",       # Red
        "Assertion Failure": "#FF9800", # Orange
        "Invalid Action": "#9C27B0",    # Purple
        "Unknown Failure": "#607D8B"    # Grey
    }

    # --- PLOT 1: Global Health (Donut Chart) ---
    ax1 = plt.subplot(gs[0, 0])
    status_counts = df['Category'].value_counts()
    
    # Map colors to index
    pie_colors = [colors.get(x, "#333") for x in status_counts.index]
    
    wedges, texts, autotexts = ax1.pie(
        status_counts, 
        labels=status_counts.index, 
        autopct='%1.1f%%', 
        startangle=90, 
        colors=pie_colors, 
        pctdistance=0.85,
        explode=[0.05]*len(status_counts) # Slight separation
    )
    
    # Draw White Circle for Donut Effect
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    ax1.add_artist(centre_circle)
    
    ax1.set_title(f"Global Test Health (Total: {len(df)})", fontweight='bold', fontsize=14)
    plt.setp(autotexts, size=10, weight="bold", color="white")

    # --- PLOT 2: Business Process Performance (Horizontal Bar) ---
    ax2 = plt.subplot(gs[0, 1])
    
    # Calculate Success Rate per Business Process
    bp_stats = df.groupby("Business Process")["Is Success"].mean() * 100
    bp_stats = bp_stats.sort_values()

    # Create Bar H
    bars = ax2.barh(bp_stats.index, bp_stats.values, color='#2196F3')
    
    ax2.set_xlim(0, 100)
    ax2.set_xlabel("Success Rate (%)", fontweight='bold')
    ax2.set_title("Success Rate by Business Process", fontweight='bold', fontsize=14)
    ax2.grid(axis='x', linestyle='--', alpha=0.5)

    # Add labels inside bars
    for bar in bars:
        width = bar.get_width()
        ax2.text(width + 1, bar.get_y() + bar.get_height()/2, 
                 f'{width:.1f}%', va='center', fontweight='bold', color='black')

    # --- PLOT 3: Detailed Use Case Breakdown (Stacked Bar) ---
    ax3 = plt.subplot(gs[1, :]) # Span entire bottom row
    
    # Group data
    uc_data = df.groupby(['Use Case', 'Category']).size().unstack(fill_value=0)
    
    # Ensure color ordering matches
    existing_cols = uc_data.columns.tolist()
    stack_colors = [colors.get(col, "#333") for col in existing_cols]

    uc_data.plot(kind='bar', stacked=True, ax=ax3, color=stack_colors, width=0.7)
    
    ax3.set_title("Detailed Result Breakdown per Use Case", fontweight='bold', fontsize=14)
    ax3.set_ylabel("Count", fontweight='bold')
    ax3.set_xlabel("Use Case ID", fontweight='bold')
    ax3.legend(title="Outcome", loc='upper right', bbox_to_anchor=(1, 1))
    ax3.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Rotate X labels
    plt.setp(ax3.get_xticklabels(), rotation=45, ha="right")

    # Add numeric labels on stacks
    for c in ax3.containers:
        labels = [int(v.get_height()) if v.get_height() > 0 else '' for v in c]
        ax3.bar_label(c, labels=labels, label_type='center', color='white', fontweight='bold', fontsize=8)

    # --- FINAL LAYOUT ADJUSTMENTS ---
    plt.tight_layout()
    plt.savefig(OUTPUT_IMG)
    print(f"Dashboard saved successfully as: {OUTPUT_IMG}")
    plt.show()

if __name__ == "__main__":
    data = collect_data()
    create_dashboard(data)